# WebSocket System - Quick Start Guide

## Quick Setup

```bash
# Install dependencies
pip install watchdog

# Run example server
python examples/websocket_example.py

# Open test client
open examples/websocket_client.html
```

## Connect to WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/api/build/stream/session_id');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## Send Messages

```javascript
// Ping
ws.send(JSON.stringify({ type: 'ping' }));

// Subscribe to topics
ws.send(JSON.stringify({
    type: 'subscribe',
    topics: ['component_update', 'terminal_output']
}));
```

## Server-Side Broadcasting

```python
from api.websocket_handler import (
    broadcast_component_update,
    broadcast_terminal_output,
    broadcast_build_progress
)

# Broadcast component update
await broadcast_component_update(
    session_id="build_123",
    component_id="auth_service",
    status="in_progress",
    progress=45.5
)

# Stream terminal output
await broadcast_terminal_output(
    session_id="build_123",
    output="Compiling...\n",
    output_type="stdout"
)

# Send progress update
await broadcast_build_progress(
    session_id="build_123",
    total_components=10,
    completed_components=7,
    percent=70.0
)
```

## File Watching

```python
from core.build.file_watcher import create_file_watcher_with_websocket
from api.websocket_handler import broadcast_checkpoint_update

# Create watcher
watcher = await create_file_watcher_with_websocket(
    project_root="/path/to/project",
    session_id="build_123",
    websocket_broadcaster=broadcast_checkpoint_update
)

# Stop watching
await watcher.stop()
```

## Parse Checkpoints

```python
from core.build.checkpoint_parser import (
    parse_checkpoint,
    get_checkpoint_summary,
    get_component_updates
)

# Parse checkpoint file
data = parse_checkpoint("checkpoint_123.json")
print(f"Progress: {data['overall_progress']['completion_percentage']}%")

# Get summary
summary = get_checkpoint_summary("checkpoint_123.json")
print(f"Phase: {summary['phase']}")
print(f"Status: {summary['status']}")

# Extract component updates
components = get_component_updates("checkpoint_123.json")
for comp in components:
    print(f"{comp['component_id']}: {comp['status']} ({comp['progress']}%)")
```

## Message Types

### Component Update
```json
{
  "type": "component_update",
  "session_id": "build_123",
  "component_id": "auth_service",
  "status": "in_progress",
  "progress": 45.5,
  "metadata": {}
}
```

### Terminal Output
```json
{
  "type": "terminal_output",
  "session_id": "build_123",
  "output": "Building...\n",
  "output_type": "stdout",
  "source": "builder"
}
```

### Build Progress
```json
{
  "type": "build_progress",
  "session_id": "build_123",
  "total": 10,
  "completed": 7,
  "percent": 70.0
}
```

### Checkpoint Update
```json
{
  "type": "checkpoint_update",
  "session_id": "build_123",
  "checkpoint_id": "checkpoint_123",
  "phase": "build_phase_1",
  "tasks_completed": ["task1", "task2"],
  "files_created": ["file1.py"]
}
```

## Integration with FastAPI

```python
from fastapi import FastAPI
from api.websocket_handler import router as websocket_router

app = FastAPI()
app.include_router(websocket_router)

@app.on_event("startup")
async def startup():
    # Start file watcher
    global watcher
    watcher = await create_file_watcher_with_websocket(
        project_root=".",
        session_id="main",
        websocket_broadcaster=broadcast_checkpoint_update
    )

@app.on_event("shutdown")
async def shutdown():
    # Stop file watcher
    await watcher.stop()
```

## Testing Commands

```bash
# Send demo update
curl -X POST http://localhost:8000/demo/send-update

# Check API docs
open http://localhost:8000/docs

# Monitor WebSocket in terminal
wscat -c ws://localhost:8000/api/build/stream/session_123
```

## File Locations

```
api/websocket_handler.py          - WebSocket endpoint
core/build/file_watcher.py         - File system monitoring
core/build/checkpoint_parser.py    - Checkpoint parsing
examples/websocket_example.py      - Example server
examples/websocket_client.html     - Test client
```

## Key Functions

| Function | Purpose |
|----------|---------|
| `broadcast_component_update()` | Send component status |
| `broadcast_terminal_output()` | Stream terminal output |
| `broadcast_build_progress()` | Send progress update |
| `broadcast_checkpoint_update()` | Send checkpoint data |
| `parse_checkpoint()` | Parse checkpoint JSON |
| `get_checkpoint_summary()` | Get checkpoint summary |
| `create_file_watcher_with_websocket()` | Setup file watcher |

## Troubleshooting

### WebSocket won't connect
- Check server is running
- Verify URL format: `ws://host:port/api/build/stream/{session_id}`
- Check CORS settings

### File watcher not working
- Install watchdog: `pip install watchdog`
- Check directory permissions
- Verify .buildrunner/ exists

### No messages received
- Check session_id matches
- Verify files are being created in .buildrunner/
- Check server logs for errors

---

For detailed documentation, see: `WEBSOCKET_IMPLEMENTATION.md`
