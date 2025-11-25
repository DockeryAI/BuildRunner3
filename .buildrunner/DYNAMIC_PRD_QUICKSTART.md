# Dynamic PRD System - Quick Start Guide

Get started with the Dynamic PRD-Driven Build System in 5 minutes.

## Prerequisites

```bash
# Install required packages
pip install watchdog filelock fastapi uvicorn websockets

# Or add to requirements.txt and install
cat >> requirements.txt << EOF
watchdog>=3.0.0
filelock>=3.12.0
fastapi>=0.104.0
uvicorn>=0.24.0
websockets>=12.0
EOF

pip install -r requirements.txt
```

## Quick Test (3 Steps)

### Step 1: Start the API Server

```bash
cd /Users/byronhudson/Projects/BuildRunner3
source .venv/bin/activate  # or your virtual environment
python -m uvicorn api.server:app --reload --port 8080
```

You should see:
```
Loaded .env from: /Users/byronhudson/Projects/BuildRunner3/.env
Starting BuildRunner API server...
INFO:     Uvicorn running on http://127.0.0.1:8080
```

### Step 2: Test REST API

Open a new terminal:

```bash
# Get current PRD
curl http://localhost:8080/api/prd/current | jq

# Add a test feature
curl -X POST http://localhost:8080/api/prd/update \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "add_feature": {
        "id": "feature-quickstart",
        "name": "Quick Start Test Feature",
        "description": "Testing the Dynamic PRD System",
        "priority": "low",
        "requirements": ["Test requirement 1", "Test requirement 2"],
        "acceptance_criteria": ["Should load successfully", "Should regenerate tasks"]
      }
    },
    "author": "quickstart-tester"
  }' | jq

# Verify it was added
curl http://localhost:8080/api/prd/current | jq '.features[] | select(.id=="feature-quickstart")'
```

### Step 3: Test File Watcher

Edit the PROJECT_SPEC.md file directly:

```bash
# Open in editor
vim .buildrunner/PROJECT_SPEC.md

# Or append programmatically
cat >> .buildrunner/PROJECT_SPEC.md << 'EOF'

## Feature X: Manual Test Feature

**Priority:** Medium

### Description

This feature was added by directly editing the file.

### Requirements

- Requirement 1
- Requirement 2

### Acceptance Criteria

- [ ] File watcher detects change
- [ ] PRD reloads automatically
- [ ] Tasks regenerate
EOF
```

Check the server logs - you should see:
```
INFO: Detected external change to .buildrunner/PROJECT_SPEC.md
INFO: PRD reloaded from file
INFO: PRD change detected: feature_added
INFO: Regeneration complete in 1.23s: 5 generated, 0 preserved
```

## Usage Examples

### Example 1: Natural Language Preview

```bash
curl -X POST http://localhost:8080/api/prd/parse-nl \
  -H "Content-Type: application/json" \
  -d '{"text": "add authentication with JWT tokens"}' | jq
```

Response:
```json
{
  "success": true,
  "message": "Successfully parsed natural language",
  "updates": {
    "add_feature": {
      "id": "feature-4",
      "name": "Authentication With Jwt Tokens",
      "description": "Feature: authentication with jwt tokens",
      "priority": "medium"
    }
  },
  "preview": "➕ Will add feature: Authentication With Jwt Tokens"
}
```

### Example 2: Update Existing Feature

```bash
curl -X POST http://localhost:8080/api/prd/update \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "update_feature": {
        "id": "feature-1",
        "updates": {
          "priority": "high",
          "description": "Updated description for feature 1"
        }
      }
    },
    "author": "developer"
  }' | jq
```

### Example 3: Version History

```bash
# Get all versions
curl http://localhost:8080/api/prd/versions | jq

# Rollback to version 2
curl -X POST http://localhost:8080/api/prd/rollback \
  -H "Content-Type: application/json" \
  -d '{"version_index": 2}' | jq
```

### Example 4: WebSocket Connection

```bash
# Install websocat if needed: brew install websocat
websocat ws://localhost:8080/api/prd/stream

# You'll receive:
# 1. Initial PRD state immediately
# 2. Updates whenever PRD changes

# Keep connection alive by sending ping every 30s
# (Open another terminal and make PRD changes to see real-time updates)
```

## Python SDK Examples

### Basic Usage

```python
from pathlib import Path
from core.prd.prd_controller import get_prd_controller

# Get controller (singleton)
controller = get_prd_controller()

# Get current PRD
prd = controller.prd
print(f"Project: {prd.project_name}")
print(f"Features: {len(prd.features)}")

# Add a feature
updates = {
    "add_feature": {
        "id": "feature-sdk-test",
        "name": "SDK Test Feature",
        "description": "Added via Python SDK",
        "priority": "medium"
    }
}
event = controller.update_prd(updates, author="sdk-user")
print(f"Event: {event.event_type.value}")
print(f"Affected features: {event.affected_features}")
```

### Subscribe to Events

```python
from core.prd.prd_controller import get_prd_controller, PRDChangeEvent

def on_prd_change(event: PRDChangeEvent):
    print(f"PRD changed: {event.event_type.value}")
    print(f"Affected features: {event.affected_features}")
    print(f"Timestamp: {event.timestamp}")

controller = get_prd_controller()
controller.subscribe(on_prd_change)

# Now any PRD changes will trigger the callback
```

### Adaptive Planner Integration

```python
from pathlib import Path
from core.adaptive_planner import get_adaptive_planner
from core.task_queue import TaskQueue

# Initialize
task_queue = TaskQueue()
planner = get_adaptive_planner(Path.cwd(), task_queue)

# Generate initial plan from PRD
result = planner.initial_plan_from_prd()
print(f"Generated {result.tasks_generated} tasks in {result.duration_seconds:.2f}s")

# Get execution plan
plan = planner.get_execution_plan()
print(f"Total tasks: {plan['total_tasks']}")
print(f"Execution levels: {plan['execution_levels']}")
print(f"Ready tasks: {plan['ready_tasks']}")

# PRD changes will now automatically trigger regeneration
```

## Testing Scenarios

### Scenario 1: Zero Work Loss

1. Add a feature and generate tasks
2. Mark some tasks as COMPLETED
3. Update the feature (e.g., change priority)
4. Verify completed tasks are preserved

```python
from core.task_queue import TaskQueue, TaskStatus

task_queue = TaskQueue()

# Simulate task completion
task_queue.add_task("task-1", "Build login form", 90, [])
task_queue.update_status("task-1", TaskStatus.COMPLETED)

# Now update the feature - task-1 should remain COMPLETED
```

### Scenario 2: Multi-Channel Sync

1. Open 2 browser tabs to the UI (once implemented)
2. Edit PRD in tab 1
3. Verify tab 2 updates instantly via WebSocket
4. Edit PROJECT_SPEC.md directly
5. Verify both tabs update

### Scenario 3: Performance Test

```python
import time
from core.prd.prd_controller import get_prd_controller

controller = get_prd_controller()

# Add 2 features and measure regeneration time
start = time.time()
for i in range(2):
    updates = {
        "add_feature": {
            "id": f"feature-perf-{i}",
            "name": f"Performance Test Feature {i}",
            "priority": "medium"
        }
    }
    controller.update_prd(updates, author="perf-test")
duration = time.time() - start

print(f"Regeneration time for 2 features: {duration:.2f}s")
assert duration < 3.0, "Should be <3s for 2 features"
```

## Troubleshooting

### Issue: "Could not acquire lock"

**Solution:**
```bash
rm .buildrunner/.PROJECT_SPEC.md.lock
```

### Issue: "PRD not initialized"

**Solution:** Ensure PROJECT_SPEC.md exists:
```bash
ls -la .buildrunner/PROJECT_SPEC.md
```

If missing, create it:
```bash
cat > .buildrunner/PROJECT_SPEC.md << 'EOF'
# My Project

**Version:** 1.0.0
**Last Updated:** 2025-11-19

## Project Overview

This is a test project.

## Feature 1: Initial Feature

**Priority:** Medium

### Description

This is the initial feature.

### Requirements

- Requirement 1

### Acceptance Criteria

- [ ] Criterion 1
EOF
```

### Issue: WebSocket disconnects immediately

**Solution:** Implement ping/pong keep-alive:
```javascript
const ws = new WebSocket('ws://localhost:8080/api/prd/stream');
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send('ping');
  }
}, 30000);
```

### Issue: Tasks not regenerating

**Solution:** Check that Adaptive Planner is subscribed:
```python
from core.prd.prd_controller import get_prd_controller

controller = get_prd_controller()
print(f"Listeners: {len(controller._listeners)}")
# Should be at least 1 (Adaptive Planner)
```

## Next Steps

1. **Frontend UI**: Implement PRDEditor.tsx for rich editing experience
2. **Testing**: Write comprehensive test suite
3. **Documentation**: Add inline code comments and API docs
4. **Deployment**: Deploy to production environment
5. **Monitoring**: Add telemetry and performance monitoring

## Resources

- **Full Documentation**: `.buildrunner/DYNAMIC_PRD_SYSTEM.md`
- **API Docs**: http://localhost:8080/docs (when server is running)
- **WebSocket Tester**: https://www.websocket.org/echo.html

## Support

For issues or questions:
- Check logs in the API server console
- Review `.buildrunner/.PROJECT_SPEC.md.lock` for lock issues
- Ensure all dependencies are installed
- Verify PROJECT_SPEC.md format is valid

---

**Last Updated:** 2025-11-19
**Time to Complete:** ~5 minutes
