# Worktree D: MCP Validation (2-3 hours)

## Goal
Comprehensive E2E tests for MCP server integration.

## Tasks

### 1. Test Infrastructure (0.5 hours)
**File**: `tests/e2e/test_mcp_integration.py`

```python
import pytest
import json
from pathlib import Path
from cli.mcp_server import MCPServer

@pytest.fixture
def mcp_server(tmp_path):
    """Create MCP server with test project"""
    # Initialize features.json
    features_file = tmp_path / ".buildrunner" / "features.json"
    features_file.parent.mkdir(parents=True)
    features_file.write_text(json.dumps({
        "project": "TestProject",
        "version": "1.0.0",
        "features": []
    }))

    server = MCPServer(project_root=tmp_path)
    return server
```

### 2. Test All 9 Tools (1.5 hours)

```python
def test_list_tools(mcp_server):
    """Test list_tools returns all 9 tools"""
    response = mcp_server.handle_request({
        "tool": "list_tools",
        "arguments": {}
    })

    assert response["success"] == True
    assert len(response["result"]) == 9

def test_feature_add(mcp_server):
    """Test adding feature"""
    response = mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {
            "name": "Test Feature",
            "id": "test",
            "priority": "high"
        }
    })

    assert response["success"] == True
    assert response["result"]["id"] == "test"

def test_feature_complete(mcp_server):
    """Test completing feature"""
    # Add first
    mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "F1", "id": "f1"}
    })

    # Complete
    response = mcp_server.handle_request({
        "tool": "feature_complete",
        "arguments": {"feature_id": "f1"}
    })

    assert response["success"] == True

def test_feature_list(mcp_server):
    """Test listing with filter"""
    # Add multiple
    mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "F1", "id": "f1"}
    })
    mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "F2", "id": "f2"}
    })

    # Complete one
    mcp_server.handle_request({
        "tool": "feature_complete",
        "arguments": {"feature_id": "f1"}
    })

    # List completed only
    response = mcp_server.handle_request({
        "tool": "feature_list",
        "arguments": {"status": "completed"}
    })

    assert response["count"] == 1
    assert response["result"][0]["id"] == "f1"

def test_feature_get(mcp_server):
    """Test getting specific feature"""
    mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "Test", "id": "test"}
    })

    response = mcp_server.handle_request({
        "tool": "feature_get",
        "arguments": {"feature_id": "test"}
    })

    assert response["success"] == True
    assert response["result"]["name"] == "Test"

def test_feature_update(mcp_server):
    """Test updating feature"""
    mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "F1", "id": "f1"}
    })

    response = mcp_server.handle_request({
        "tool": "feature_update",
        "arguments": {
            "feature_id": "f1",
            "updates": {"status": "in_progress", "priority": "critical"}
        }
    })

    assert response["success"] == True

def test_status_get(mcp_server):
    """Test project status"""
    # Add and complete features
    mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "F1", "id": "f1"}
    })
    mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "F2", "id": "f2"}
    })
    mcp_server.handle_request({
        "tool": "feature_complete",
        "arguments": {"feature_id": "f1"}
    })

    response = mcp_server.handle_request({
        "tool": "status_get",
        "arguments": {}
    })

    assert response["success"] == True
    metrics = response["result"]["metrics"]
    assert metrics["features_complete"] == 1
    assert metrics["features_in_progress"] == 0
    assert metrics["features_planned"] == 1

def test_status_generate(mcp_server):
    """Test STATUS.md generation"""
    response = mcp_server.handle_request({
        "tool": "status_generate",
        "arguments": {}
    })

    assert response["success"] == True
    status_file = mcp_server.project_root / "STATUS.md"
    assert status_file.exists()

def test_governance_check(mcp_server):
    """Test governance validation"""
    response = mcp_server.handle_request({
        "tool": "governance_check",
        "arguments": {"check_type": "pre_commit"}
    })

    assert response["success"] == True
    assert "passed" in response["result"]
```

### 3. E2E Flow Test (0.5 hours)

```python
def test_complete_workflow(mcp_server):
    """Test full workflow: add → update → complete → status"""

    # Add feature
    add = mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {"name": "Auth System", "id": "auth", "priority": "critical"}
    })
    assert add["success"]

    # Update to in_progress
    update = mcp_server.handle_request({
        "tool": "feature_update",
        "arguments": {"feature_id": "auth", "updates": {"status": "in_progress"}}
    })
    assert update["success"]

    # Complete
    complete = mcp_server.handle_request({
        "tool": "feature_complete",
        "arguments": {"feature_id": "auth"}
    })
    assert complete["success"]

    # Generate status
    generate = mcp_server.handle_request({
        "tool": "status_generate",
        "arguments": {}
    })
    assert generate["success"]

    # Verify STATUS.md
    status_file = mcp_server.project_root / "STATUS.md"
    assert "Auth System" in status_file.read_text()
```

### 4. Error Handling (0.5 hours)

```python
def test_missing_required_params(mcp_server):
    """Test error on missing params"""
    response = mcp_server.handle_request({
        "tool": "feature_add",
        "arguments": {}  # Missing 'name'
    })

    assert response["success"] == False
    assert "error" in response

def test_feature_not_found(mcp_server):
    """Test error when feature missing"""
    response = mcp_server.handle_request({
        "tool": "feature_get",
        "arguments": {"feature_id": "nonexistent"}
    })

    assert response["success"] == False
    assert "not found" in response["error"].lower()

def test_invalid_tool_name(mcp_server):
    """Test error on invalid tool"""
    response = mcp_server.handle_request({
        "tool": "nonexistent_tool",
        "arguments": {}
    })

    assert response["success"] == False
```

## Acceptance Criteria
- [ ] All 9 MCP tools tested
- [ ] E2E workflow test passing
- [ ] Error handling validated
- [ ] 90%+ test coverage on mcp_server.py
- [ ] Documentation matches implementation
- [ ] Quality check passes

## Notes
- Test with isolated features.json (tmp_path)
- Verify JSON request/response format
- Test all error cases
- Validate against docs/MCP_INTEGRATION.md
