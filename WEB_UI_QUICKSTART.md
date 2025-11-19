# BuildRunner 3.2 Web UI - Quick Start Guide

## Installation

### 1. Install Backend Dependencies
```bash
# From project root
pip install -r requirements-api.txt
```

### 2. Install Frontend Dependencies
```bash
cd ui
npm install
```

## Running the Application

### Option 1: Run Both Servers (Recommended)

**Terminal 1 - Backend:**
```bash
# From project root
python -m uvicorn api.server:app --host 0.0.0.0 --port 8080 --reload
```

**Terminal 2 - Frontend:**
```bash
cd ui
npm run dev
```

### Option 2: Using Python Script

**Backend:**
```bash
python api/server.py
```

**Frontend:**
```bash
cd ui
npm run dev
```

## Access the Dashboard

Open your browser and navigate to:
```
http://localhost:5173
```

The dashboard will automatically connect to the backend API at `http://localhost:8080`

## Verify Installation

### Test Backend
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "BuildRunner API",
  "version": "3.2.0"
}
```

### Test WebSocket
The frontend will show a green "Live" indicator when WebSocket is connected.

## Features

### Dashboard Views

1. **Tasks Tab**
   - View all tasks with status
   - Filter by status (pending, running, completed, failed)
   - See task details, complexity, and time estimates

2. **Agent Pool Tab**
   - Monitor agent pool utilization
   - View active sessions
   - Track worker metrics

3. **Telemetry Tab**
   - Real-time event timeline
   - Event filtering
   - Metadata inspection

### Controls

- **Pause** - Pause orchestration
- **Resume** - Resume paused orchestration
- **Stop** - Stop orchestration

## API Documentation

Interactive API documentation available at:
```
http://localhost:8080/docs
```

## Development

### Backend Development

Enable auto-reload:
```bash
uvicorn api.server:app --reload --port 8080
```

### Frontend Development

Vite provides hot module replacement:
```bash
cd ui
npm run dev
```

## Testing

### Backend Tests
```bash
# All backend tests
pytest tests/test_api_server.py -v
pytest tests/test_websockets.py -v

# With coverage
pytest tests/test_api_server.py --cov=api --cov-report=html
```

### Frontend Tests
```bash
cd ui

# Run tests
npm test

# With coverage
npm run test:coverage

# Watch mode
npm test -- --watch
```

## Building for Production

### Frontend Build
```bash
cd ui
npm run build
```

Production files will be in `ui/dist/`

### Serve Production Build
```bash
cd ui
npm run preview
```

## Troubleshooting

### Port Already in Use

If port 8080 is in use:
```bash
# Find process
lsof -i :8080

# Kill process
kill -9 <PID>
```

### WebSocket Connection Issues

1. Check backend is running on port 8080
2. Check CORS settings in `api/server.py`
3. Verify WebSocket URL in frontend

### Module Not Found Errors

Backend:
```bash
# Ensure you're in the venv
source .venv/bin/activate
pip install -r requirements-api.txt
```

Frontend:
```bash
cd ui
npm install
```

## Environment Variables

Create `ui/.env` for custom configuration:
```env
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080
```

## Next Steps

1. Start both servers
2. Open http://localhost:5173
3. Explore the dashboard
4. Try pausing/resuming orchestration
5. View real-time task updates
6. Check telemetry timeline

## Support

For issues or questions, see:
- API Documentation: http://localhost:8080/docs
- Implementation Guide: WEB_UI_IMPLEMENTATION.md
- Main README: README.md
