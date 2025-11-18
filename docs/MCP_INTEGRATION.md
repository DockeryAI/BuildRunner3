# MCP Integration - BuildRunner 3.0

BuildRunner 3.0 exposes its functionality through MCP (Model Context Protocol), allowing AI assistants like Claude Code to directly manage features, check status, and enforce governance rules.

## What is MCP?

Model Context Protocol (MCP) is a standardized way for AI assistants to interact with external tools and services. It enables Claude Code to:
- Read and modify project data
- Execute commands
- Query system state
- Coordinate actions

## MCP Server

BuildRunner provides an MCP server (`cli/mcp_server.py`) that exposes BuildRunner tools to AI assistants.

### Starting the Server

```bash
python cli/mcp_server.py
```

The server listens on stdin/stdout, receiving JSON requests and sending JSON responses.

### Request Format

```json
{
  "tool": "tool_name",
  "arguments": {
    "arg1": "value1",
    "arg2": "value2"
  }
}
```

### Response Format

```json
{
  "success": true,
  "result": {...},
  "message": "Optional message"
}
```

Or on error:

```json
{
  "success": false,
  "error": "Error message"
}
```

## Available Tools

### Feature Management

#### feature_add

Add a new feature to the project.

**Parameters:**
- `name` (required): Feature name
- `id` (optional): Feature ID (auto-generated if not provided)
- `status` (optional): Status (default: "planned")
- `priority` (optional): Priority (default: "medium")

**Example:**
```json
{
  "tool": "feature_add",
  "arguments": {
    "name": "User Authentication",
    "id": "auth",
    "priority": "high"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "id": "auth",
    "name": "User Authentication",
    "status": "planned",
    "priority": "high"
  },
  "message": "Added feature: User Authentication (auth)"
}
```

#### feature_complete

Mark a feature as complete.

**Parameters:**
- `feature_id` (required): Feature ID to complete

**Example:**
```json
{
  "tool": "feature_complete",
  "arguments": {
    "feature_id": "auth"
  }
}
```

#### feature_list

List all features, optionally filtered by status.

**Parameters:**
- `status` (optional): Filter by status ("planned", "in_progress", "complete", etc.)

**Example:**
```json
{
  "tool": "feature_list",
  "arguments": {
    "status": "in_progress"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": [
    {
      "id": "auth",
      "name": "User Authentication",
      "status": "in_progress",
      "priority": "high"
    }
  ],
  "count": 1
}
```

#### feature_get

Get details of a specific feature.

**Parameters:**
- `feature_id` (required): Feature ID

**Example:**
```json
{
  "tool": "feature_get",
  "arguments": {
    "feature_id": "auth"
  }
}
```

#### feature_update

Update a feature's properties.

**Parameters:**
- `feature_id` (required): Feature ID
- `updates` (required): Dictionary of updates

**Example:**
```json
{
  "tool": "feature_update",
  "arguments": {
    "feature_id": "auth",
    "updates": {
      "status": "in_progress",
      "assignee": "alice@example.com"
    }
  }
}
```

### Status & Reporting

#### status_get

Get current project status and metrics.

**Parameters:** None

**Example:**
```json
{
  "tool": "status_get",
  "arguments": {}
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "project": "MyProject",
    "version": "1.0.0",
    "status": "in_development",
    "metrics": {
      "features_complete": 5,
      "features_in_progress": 3,
      "features_planned": 7,
      "completion_percentage": 33
    },
    "features": [...]
  }
}
```

#### status_generate

Generate STATUS.md from features.json.

**Parameters:** None

**Example:**
```json
{
  "tool": "status_generate",
  "arguments": {}
}
```

### Governance

#### governance_check

Run governance checks (pre-commit or pre-push).

**Parameters:**
- `check_type` (required): "pre_commit" or "pre_push"

**Example:**
```json
{
  "tool": "governance_check",
  "arguments": {
    "check_type": "pre_commit"
  }
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "passed": true,
    "failed_checks": []
  },
  "message": "All checks passed"
}
```

#### governance_validate

Validate governance configuration.

**Parameters:** None

**Example:**
```json
{
  "tool": "governance_validate",
  "arguments": {}
}
```

### Tool Discovery

#### list_tools

List all available tools with their parameters.

**Parameters:** None

**Example:**
```json
{
  "tool": "list_tools",
  "arguments": {}
}
```

**Response:**
```json
{
  "success": true,
  "result": [
    {
      "name": "feature_add",
      "description": "Add a new feature to the project",
      "parameters": {...}
    },
    ...
  ]
}
```

## Using MCP with Claude Code

Claude Code can interact with BuildRunner via MCP when properly configured.

### Configuration

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "buildrunner": {
      "command": "python",
      "args": ["/path/to/project/cli/mcp_server.py"],
      "cwd": "/path/to/project"
    }
  }
}
```

### Example Interactions

**Claude Code can now:**

```
User: "Add a new feature called Database Migration"

Claude: I'll add that feature for you.
[Uses MCP tool: feature_add]
✅ Added feature: Database Migration (database-migration)

User: "What's the current project status?"

Claude: Let me check.
[Uses MCP tool: status_get]
Your project MyProject is at 33% completion:
- 5 features complete
- 3 in progress
- 7 planned

User: "Mark the auth feature as complete"

Claude: I'll mark it complete and regenerate STATUS.md.
[Uses MCP tool: feature_complete]
✅ Completed feature: auth
✅ Generated: .buildrunner/STATUS.md
```

## Git Hooks Integration

BuildRunner's git hooks can also trigger MCP operations:

### pre-commit

Automatically validates before commits:
- Features.json schema
- Governance rules
- Checksums

### post-commit

Automatically updates after commits:
- Regenerates STATUS.md
- Updates metrics
- Updates AI context

### pre-push

Validates before push:
- Sync status
- Project completeness
- Governance compliance

## Programmatic Usage

You can also use the MCP server programmatically:

```python
from cli.mcp_server import MCPServer

# Create server
server = MCPServer()

# Make a request
request = {
    "tool": "feature_add",
    "arguments": {
        "name": "New Feature",
        "priority": "high"
    }
}

response = server.handle_request(request)
print(response)
```

## Error Handling

All tools return consistent error responses:

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

Common error scenarios:
- Missing required parameters
- Feature not found
- Governance validation failures
- File I/O errors

## Best Practices

1. **Always check success field** in responses before processing results
2. **Use feature IDs consistently** - they're unique across the project
3. **Run governance checks** before major operations
4. **Generate STATUS.md** after feature changes
5. **Handle errors gracefully** - MCP should never crash the workflow

## Troubleshooting

### Server not responding

Check that:
- Python path is correct
- Project root is correct
- Dependencies are installed
- features.json exists

### Tools failing

Check:
- Tool name spelling
- Required parameters provided
- Project is properly initialized (`br init`)
- No file permission issues

### Governance errors

Check:
- governance.yaml is valid
- Checksums match
- Enforcement policy allows operation

## Future Enhancements

- WebSocket support for real-time updates
- Batch operations for multiple features
- Undo/redo support
- Conflict resolution for concurrent edits
- Webhook notifications
- GraphQL query support

---

For CLI documentation, see [CLI.md](CLI.md).

For git hooks details, see [GIT_HOOKS.md](GIT_HOOKS.md) (if exists).
