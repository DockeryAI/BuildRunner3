"""
WebSocket Log Streaming Server
Streams BuildRunner logs and command outputs to UI in real-time
"""
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import aiofiles
import logging

logger = logging.getLogger(__name__)

class LogFileHandler(FileSystemEventHandler):
    """Watches log files for changes and notifies connected clients"""

    def __init__(self, manager: 'ConnectionManager'):
        self.manager = manager
        self.file_positions: Dict[str, int] = {}

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.log'):
            asyncio.create_task(self.stream_new_content(event.src_path))

    async def stream_new_content(self, filepath: str):
        """Stream new content from modified log file"""
        try:
            # Get last read position
            last_position = self.file_positions.get(filepath, 0)

            async with aiofiles.open(filepath, 'r') as f:
                await f.seek(last_position)
                new_content = await f.read()

                if new_content:
                    # Update position
                    self.file_positions[filepath] = await f.tell()

                    # Stream to all connected clients
                    await self.manager.broadcast({
                        'type': 'log_update',
                        'file': os.path.basename(filepath),
                        'content': new_content,
                        'timestamp': datetime.now().isoformat()
                    })
        except Exception as e:
            logger.error(f"Error streaming log content: {e}")


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.log_handler: Optional[LogFileHandler] = None
        self.observer: Optional[Observer] = None

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)

        # Send initial state
        await self.send_initial_state(websocket)

        # Start file watching if not already started
        if not self.observer:
            self.start_file_watching()

    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket"""
        self.active_connections.discard(websocket)

        # Stop watching if no connections
        if not self.active_connections and self.observer:
            self.observer.stop()
            self.observer = None

    async def send_initial_state(self, websocket: WebSocket):
        """Send current log state to newly connected client"""
        log_dir = Path("/Users/byronhudson/Projects/BuildRunner3/workspace/logs")

        if log_dir.exists():
            for log_file in log_dir.glob("*.log"):
                try:
                    async with aiofiles.open(log_file, 'r') as f:
                        content = await f.read()
                        await websocket.send_json({
                            'type': 'initial_log',
                            'file': log_file.name,
                            'content': content,
                            'timestamp': datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Error sending initial log {log_file}: {e}")

    def start_file_watching(self):
        """Start watching log directory for changes"""
        log_dir = "/Users/byronhudson/Projects/BuildRunner3/workspace/logs"

        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        self.log_handler = LogFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.log_handler, log_dir, recursive=False)
        self.observer.start()

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)

        # Clean up disconnected
        self.active_connections -= disconnected

    async def send_command_output(self, command: str, output: str, error: str = None):
        """Send command execution output to all clients"""
        await self.broadcast({
            'type': 'command_output',
            'command': command,
            'output': output,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })

    async def send_status_update(self, status: str, details: dict = None):
        """Send BuildRunner status update"""
        await self.broadcast({
            'type': 'status_update',
            'status': status,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for log streaming"""
    await manager.connect(websocket)

    try:
        while True:
            # Keep connection alive and handle commands
            data = await websocket.receive_json()

            if data.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})
            elif data.get('type') == 'subscribe':
                # Handle log subscription requests
                log_file = data.get('file')
                if log_file:
                    # Start tailing specific log file
                    await tail_log_file(websocket, log_file)
            elif data.get('type') == 'command':
                # Handle command execution requests
                command = data.get('command')
                if command:
                    await execute_and_stream(command)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def tail_log_file(websocket: WebSocket, filename: str):
    """Tail a specific log file and stream to client"""
    filepath = Path(f"/Users/byronhudson/Projects/BuildRunner3/workspace/logs/{filename}")

    if not filepath.exists():
        await websocket.send_json({
            'type': 'error',
            'message': f'Log file {filename} not found'
        })
        return

    # Stream existing content
    async with aiofiles.open(filepath, 'r') as f:
        content = await f.read()
        await websocket.send_json({
            'type': 'log_content',
            'file': filename,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })


async def execute_and_stream(command: str):
    """Execute command and stream output to all clients"""
    try:
        # Log command to file
        log_file = f"/Users/byronhudson/Projects/BuildRunner3/workspace/logs/commands.log"
        async with aiofiles.open(log_file, 'a') as f:
            await f.write(f"\n[{datetime.now().isoformat()}] $ {command}\n")

        # Execute command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/Users/byronhudson/Projects/BuildRunner3"
        )

        # Stream output as it comes
        async def stream_output(stream, is_error=False):
            while True:
                line = await stream.readline()
                if not line:
                    break

                text = line.decode('utf-8')

                # Log to file
                async with aiofiles.open(log_file, 'a') as f:
                    await f.write(text)

                # Stream to clients
                await manager.send_command_output(
                    command=command,
                    output=text if not is_error else None,
                    error=text if is_error else None
                )

        # Stream both stdout and stderr
        await asyncio.gather(
            stream_output(process.stdout, False),
            stream_output(process.stderr, True)
        )

        await process.wait()

        # Send completion status
        await manager.send_status_update(
            'command_complete',
            {'command': command, 'return_code': process.returncode}
        )

    except Exception as e:
        logger.error(f"Command execution error: {e}")
        await manager.send_command_output(
            command=command,
            output=None,
            error=str(e)
        )