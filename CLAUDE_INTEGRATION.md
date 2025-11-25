# BuildRunner Claude Integration Guide

## Overview
BuildRunner 3.2 integrates with Claude AI to help you plan, design, and build projects. Due to browser security restrictions, web UIs cannot directly launch desktop applications. This guide explains all available methods for using Claude with BuildRunner.

## Integration Methods

### Method 1: Copy-to-Clipboard (Simplest)
**How it works:** The UI copies planning prompts to your clipboard
**Pros:** Works immediately, no setup required
**Cons:** Manual paste required

1. Initialize project in UI
2. Click "Start Planning Mode"
3. Prompt is copied to clipboard automatically
4. Open Claude manually and paste the prompt

### Method 2: Desktop Bridge Server (Recommended)
**How it works:** A local server bridges the web UI to desktop apps
**Pros:** Can launch Claude automatically
**Cons:** Requires running an extra server

#### Setup:
```bash
# In a terminal, run the desktop bridge:
cd /Users/byronhudson/Projects/BuildRunner3
source .venv/bin/activate
python api/desktop_bridge.py
```

The bridge runs on `http://localhost:8081` and provides:
- Automatic Claude launching
- Desktop command execution
- Bidirectional communication

#### Features:
- Detects Claude installation automatically
- Falls back to clipboard if Claude not found
- Works on macOS, Windows, and Linux

### Method 3: CLI Direct (Traditional)
**How it works:** Use the BR CLI directly
**Pros:** Full control, all features available
**Cons:** No web UI benefits

```bash
# Initialize project
br init MyProject

# Start planning
br plan

# Create PRD
br prd

# The CLI will try to launch Claude automatically
```

### Method 4: Electron App (Future)
**Status:** Not implemented yet
**How it works:** Desktop app with web UI that can control other apps
**Pros:** Best of both worlds
**Cons:** Requires separate installation

## Claude Workflow

### 1. Project Initialization
```
Web UI → br init → Creates project structure → Shows planning prompt
```

### 2. Planning Phase
```
Click "Start Planning" → Generates prompt → Copies to clipboard/Opens Claude
```

### 3. Claude Interaction
Claude helps you:
- Define project requirements
- Break down into features
- Create technical specifications
- Generate task lists
- Design architecture

### 4. Build Execution
```
br run → Executes AI agents → Builds your project
```

## API Endpoints

### Main API (Port 8080)
- `/api/execute` - Execute BR commands
- `/api/orchestrator/*` - Task orchestration
- `/api/agents/*` - AI agent management

### Desktop Bridge (Port 8081)
- `/ws/desktop` - WebSocket for desktop control
- Actions:
  - `launch_claude` - Opens Claude with prompt
  - `execute` - Run desktop commands
  - `ping` - Connection test

## Troubleshooting

### Claude Won't Launch
1. Check if Desktop Bridge is running on port 8081
2. Verify Claude is installed at:
   - macOS: `/Applications/Claude.app` or `/Applications/Claude Code.app`
   - Windows: Check if `claude` command works
3. Fallback: Use copy-to-clipboard method

### CORS Errors
- Ensure API server includes your port in allowed origins
- Current allowed ports: 3000, 3001, 5173

### Bridge Connection Failed
```bash
# Check if bridge is running
curl http://localhost:8081

# Restart bridge
pkill -f desktop_bridge.py
python api/desktop_bridge.py
```

## Security Considerations

1. **Desktop Bridge Security**
   - Only runs locally (127.0.0.1)
   - Cannot be accessed from external networks
   - Commands are validated before execution

2. **Web UI Limitations**
   - Cannot access file system directly
   - Cannot launch apps without bridge
   - Sandboxed for security

## Quick Start Checklist

- [ ] Web UI running on http://localhost:3001
- [ ] API server running on http://localhost:8080
- [ ] Desktop Bridge running on http://localhost:8081 (optional)
- [ ] Claude installed on your system (for auto-launch)

## Commands Reference

| Command | Description | UI Support |
|---------|-------------|------------|
| `br init [name]` | Initialize project | ✅ Full |
| `br plan` | Start planning mode | ✅ With clipboard |
| `br prd` | Create PRD | ✅ With clipboard |
| `br run` | Execute build | ✅ Full |
| `br status` | Check status | ✅ Full |
| `br agent list` | List AI agents | ✅ Full |

## Future Enhancements

1. **Claude API Integration** (When available)
   - Direct API calls from UI
   - Streaming responses
   - Session management

2. **Browser Extension**
   - Override security restrictions
   - Direct desktop control
   - Auto-sync with Claude

3. **Electron Desktop App**
   - Native desktop features
   - Full Claude integration
   - File system access

## Support

For issues or questions:
1. Check the API logs: http://localhost:8080/docs
2. Check Desktop Bridge: http://localhost:8081
3. File issues at: https://github.com/anthropics/claude-code/issues