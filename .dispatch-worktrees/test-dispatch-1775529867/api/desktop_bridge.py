"""
Desktop Bridge Server for BuildRunner Web UI

This server runs locally and provides a WebSocket interface that can:
1. Launch desktop applications (like Claude)
2. Execute system commands that browsers can't
3. Provide real bidirectional communication

Run this alongside your web UI to enable desktop integration.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import subprocess
import os
import json
import platform
from typing import Dict, Any
from pathlib import Path

app = FastAPI(title="BuildRunner Desktop Bridge", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DesktopBridge:
    """Handles desktop operations that browsers can't perform"""

    @staticmethod
    async def launch_claude(project_name: str, prompt: str) -> Dict[str, Any]:
        """Launch Claude with a specific prompt"""
        try:
            # Try different methods to open Claude
            system = platform.system()

            # First, try the Claude CLI if available
            try:
                # Save prompt to temp file
                temp_file = Path("/tmp/br_claude_prompt.txt")
                temp_file.write_text(f"Project: {project_name}\n\n{prompt}")

                # Try Claude CLI
                result = subprocess.run(
                    ["claude", "--dangerously-skip-permissions", str(temp_file)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    return {
                        "status": "success",
                        "message": "Claude CLI launched successfully",
                        "method": "cli",
                    }
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

            # Try opening Claude desktop app
            if system == "Darwin":  # macOS
                apps = [
                    "/Applications/Claude.app",
                    "/Applications/Claude Code.app",
                    "~/Applications/Claude.app",
                    "~/Applications/Claude Code.app",
                ]

                for app_path in apps:
                    expanded = os.path.expanduser(app_path)
                    if os.path.exists(expanded):
                        subprocess.run(["open", expanded])
                        return {
                            "status": "success",
                            "message": f"Opened {os.path.basename(expanded)}",
                            "method": "desktop_app",
                            "note": "Please paste the prompt manually",
                        }

            elif system == "Windows":
                # Try Windows methods
                try:
                    subprocess.run(["start", "claude"], shell=True)
                    return {
                        "status": "success",
                        "message": "Claude launched on Windows",
                        "method": "windows_start",
                    }
                except:
                    pass

            # Fallback: copy to clipboard
            if system == "Darwin":
                process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
                process.communicate(prompt)
                return {
                    "status": "partial",
                    "message": "Prompt copied to clipboard. Please open Claude manually.",
                    "method": "clipboard",
                }

            return {
                "status": "error",
                "message": "Could not find Claude on your system",
                "method": "none",
            }

        except Exception as e:
            return {"status": "error", "message": str(e), "method": "error"}

    @staticmethod
    async def execute_command(command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a system command"""
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60
            )

            return {
                "status": "success",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command timeout"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


bridge = DesktopBridge()


@app.websocket("/ws/desktop")
async def desktop_bridge_socket(websocket: WebSocket):
    """WebSocket endpoint for desktop operations"""
    await websocket.accept()

    try:
        while True:
            # Receive message from web UI
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "launch_claude":
                result = await bridge.launch_claude(
                    data.get("project_name", "Unknown"), data.get("prompt", "")
                )
                await websocket.send_json(result)

            elif action == "execute":
                result = await bridge.execute_command(data.get("command"), data.get("cwd"))
                await websocket.send_json(result)

            elif action == "ping":
                await websocket.send_json({"status": "pong"})

            else:
                await websocket.send_json(
                    {"status": "error", "message": f"Unknown action: {action}"}
                )

    except WebSocketDisconnect:
        print("Client disconnected from desktop bridge")
    except Exception as e:
        print(f"Desktop bridge error: {e}")
        await websocket.close()


@app.get("/")
async def root():
    return {
        "service": "BuildRunner Desktop Bridge",
        "status": "running",
        "capabilities": ["launch_claude", "execute_command", "clipboard_operations"],
    }


if __name__ == "__main__":
    import uvicorn

    print("🌉 Starting BuildRunner Desktop Bridge on port 8081...")
    print("This bridge enables web UI to control desktop applications")
    uvicorn.run(app, host="127.0.0.1", port=8081)
