# Your First BuildRunner Project

A complete step-by-step guide to creating your first project with BuildRunner 3.0, from installation to your first complete feature.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Initialization](#project-initialization)
- [Understanding the Structure](#understanding-the-structure)
- [Creating Your First Feature](#creating-your-first-feature)
- [Running Quality Checks](#running-quality-checks)
- [Testing Your Feature](#testing-your-feature)
- [Gap Analysis](#gap-analysis)
- [Common Mistakes](#common-mistakes)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** installed
- **Git** installed and configured
- Basic understanding of Python
- A terminal/command line
- A code editor (VS Code, PyCharm, etc.)

### Verify Prerequisites

```bash
# Check Python version
python3 --version
# Should show 3.11 or higher

# Check Git
git --version
# Should show git version 2.0 or higher

# Check pip
python3 -m pip --version
```

## Installation

### Step 1: Install BuildRunner

```bash
# Create a directory for your projects
mkdir ~/buildrunner-projects
cd ~/buildrunner-projects

# Install BuildRunner via pip
pip install buildrunner
# OR if you have the source:
# pip install -e /path/to/buildrunner3
```

### Step 2: Verify Installation

```bash
# Check BuildRunner is installed
br --version

# Should output: BuildRunner v3.0.0 (or similar)
```

### Step 3: View Available Commands

```bash
# See all available commands
br --help
```

You should see command groups like:
- `init` - Initialize a new project
- `design` - Design system commands
- `quality` - Code quality analysis
- `gaps` - Gap analysis
- `guard` - Architecture guard

## Project Initialization

### Step 1: Create Your Project

Let's create a simple todo list API project:

```bash
# Create new project directory
mkdir my-todo-api
cd my-todo-api

# Initialize Git
git init
```

### Step 2: Initialize BuildRunner

```bash
# Initialize BuildRunner in your project
br init

# Follow the interactive prompts:
# - Project name: my-todo-api
# - Description: A simple REST API for managing todos
# - Author: Your Name
# - License: MIT
```

**What this creates:**

```
my-todo-api/
├── .buildrunner/
│   ├── features.json       # Feature tracking
│   ├── governance.yaml     # Project rules
│   └── CLAUDE.md           # AI context
├── PROJECT_SPEC.md         # Project specification
├── README.md               # Project overview
├── pyproject.toml          # Python project config
└── requirements.txt        # Dependencies
```

### Step 3: Review Generated Files

**PROJECT_SPEC.md** - Your project's specification:
```markdown
# my-todo-api Specification

## Overview
A simple REST API for managing todos

## Features
(Will be populated as you add features)

## API Endpoints
(To be defined)

## Database Schema
(To be defined)
```

**.buildrunner/features.json** - Feature tracking:
```json
{
  "project": "my-todo-api",
  "features": []
}
```

## Understanding the Structure

### The .buildrunner Directory

This is BuildRunner's control center:

**features.json**
- Tracks all features and their status
- Updated as you build
- Used for gap analysis

**governance.yaml**
- Project rules and constraints
- Architecture decisions
- Quality standards

**CLAUDE.md**
- Context for AI assistants
- Lessons learned
- Current work state

### The PROJECT_SPEC.md

Your single source of truth:
- What you're building
- Why you're building it
- How it should work
- API contracts
- Database schemas

## Creating Your First Feature

Let's build our first feature: **Create Todo Item**

### Step 1: Define the Feature Spec

Update `PROJECT_SPEC.md`:

```markdown
## Features

### 1. Create Todo Item
Allow users to create a new todo item with title and optional description.

**API Endpoint:**
- `POST /api/todos`
- Body: `{"title": "string", "description": "string (optional)"}`
- Response: `201 Created` with todo object

**Database:**
- Table: `todos`
  - id (integer, primary key)
  - title (text, required)
  - description (text, nullable)
  - completed (boolean, default false)
  - created_at (timestamp)
```

### Step 2: Register the Feature

```bash
# Add feature to tracking
br features add \
  --id "feat-create-todo" \
  --name "Create Todo Item" \
  --description "API endpoint to create new todos" \
  --status "planned"
```

This updates `.buildrunner/features.json`:

```json
{
  "project": "my-todo-api",
  "features": [
    {
      "id": "feat-create-todo",
      "name": "Create Todo Item",
      "description": "API endpoint to create new todos",
      "status": "planned",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Step 3: Create Project Structure

```bash
# Create source directories
mkdir -p api models tests
touch api/__init__.py models/__init__.py tests/__init__.py

# Create main files
touch api/todos.py
touch models/todo.py
touch tests/test_todos.py
```

Your structure now looks like:

```
my-todo-api/
├── api/
│   ├── __init__.py
│   └── todos.py          # API routes
├── models/
│   ├── __init__.py
│   └── todo.py           # Data models
├── tests/
│   ├── __init__.py
│   └── test_todos.py     # Tests
├── .buildrunner/
├── PROJECT_SPEC.md
└── requirements.txt
```

### Step 4: Implement the Model

Edit `models/todo.py`:

```python
"""Todo data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Todo:
    """A todo item."""

    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
    created_at: datetime = None

    def __post_init__(self):
        """Set created_at if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'created_at': self.created_at.isoformat()
        }
```

### Step 5: Implement the API

Edit `api/todos.py`:

```python
"""Todo API endpoints."""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from models.todo import Todo


app = FastAPI(title="My Todo API")

# In-memory storage for demo (use database in production)
todos: List[Todo] = []
next_id = 1


class TodoCreate(BaseModel):
    """Request model for creating a todo."""
    title: str
    description: Optional[str] = None


class TodoResponse(BaseModel):
    """Response model for a todo."""
    id: int
    title: str
    description: Optional[str]
    completed: bool
    created_at: str


@app.post("/api/todos", status_code=201, response_model=TodoResponse)
def create_todo(todo_data: TodoCreate) -> dict:
    """
    Create a new todo item.

    Args:
        todo_data: Todo creation data

    Returns:
        Created todo object
    """
    global next_id

    # Create todo
    todo = Todo(
        id=next_id,
        title=todo_data.title,
        description=todo_data.description
    )

    todos.append(todo)
    next_id += 1

    return todo.to_dict()


@app.get("/api/todos", response_model=List[TodoResponse])
def list_todos() -> List[dict]:
    """
    List all todos.

    Returns:
        List of all todos
    """
    return [todo.to_dict() for todo in todos]
```

### Step 6: Add Dependencies

Update `requirements.txt`:

```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
pytest>=7.4.0
pytest-cov>=4.1.0
httpx>=0.25.0  # For testing FastAPI
```

Install dependencies:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 7: Update Feature Status

```bash
# Mark feature as in progress
br features update feat-create-todo --status in_progress
```

## Testing Your Feature

### Step 1: Write Tests

Edit `tests/test_todos.py`:

```python
"""Tests for todo API."""

import pytest
from fastapi.testclient import TestClient

from api.todos import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_create_todo(client):
    """Test creating a todo."""
    response = client.post(
        "/api/todos",
        json={"title": "Buy milk", "description": "2% milk"}
    )

    assert response.status_code == 201

    data = response.json()
    assert data['title'] == "Buy milk"
    assert data['description'] == "2% milk"
    assert data['completed'] is False
    assert 'id' in data
    assert 'created_at' in data


def test_create_todo_without_description(client):
    """Test creating a todo without description."""
    response = client.post(
        "/api/todos",
        json={"title": "Call dentist"}
    )

    assert response.status_code == 201

    data = response.json()
    assert data['title'] == "Call dentist"
    assert data['description'] is None


def test_list_todos(client):
    """Test listing todos."""
    # Create some todos
    client.post("/api/todos", json={"title": "Todo 1"})
    client.post("/api/todos", json={"title": "Todo 2"})

    # List todos
    response = client.get("/api/todos")

    assert response.status_code == 200

    data = response.json()
    assert len(data) >= 2
    assert any(todo['title'] == "Todo 1" for todo in data)
```

### Step 2: Run Tests

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=api --cov=models --cov-report=term-missing
```

Expected output:
```
tests/test_todos.py::test_create_todo PASSED
tests/test_todos.py::test_create_todo_without_description PASSED
tests/test_todos.py::test_list_todos PASSED

----------- coverage: platform darwin, python 3.11.0 -----------
Name              Stmts   Miss  Cover   Missing
-----------------------------------------------
api/todos.py         25      2    92%   15-16
models/todo.py       15      0   100%
-----------------------------------------------
TOTAL                40      2    95%
```

### Step 3: Run the Server

```bash
# Start the API server
uvicorn api.todos:app --reload

# Server starts at http://localhost:8000
```

### Step 4: Test Manually

```bash
# In another terminal, test the API:

# Create a todo
curl -X POST http://localhost:8000/api/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Test todo", "description": "Testing the API"}'

# List todos
curl http://localhost:8000/api/todos
```

## Running Quality Checks

BuildRunner includes quality analysis tools:

### Step 1: Run Quality Check

```bash
# Analyze code quality
br quality check
```

Output shows:
```
📊 Code Quality Report

Quality Scores:
Component       Score  Status
Structure       85.0   ✓ Good
Security        90.0   ✓ Excellent
Testing         95.0   ✓ Excellent
Documentation   75.0   ✓ Good
OVERALL         86.3   ✓ Good

📈 Metrics:
  Avg Complexity: 2.5
  Type Hint Coverage: 80.0%
  Test Coverage: 95.0%
  Docstring Coverage: 75.0%
```

### Step 2: Fix Quality Issues

If you see suggestions:

```
💡 Suggestions:
  • Add type hints to function parameters
  • Add docstrings to public classes
```

Update your code accordingly.

### Step 3: Set Quality Threshold

```bash
# Enforce minimum quality score
br quality check --threshold 85 --strict

# Exit code 0 if passing, 1 if failing
```

## Gap Analysis

Check for incomplete work:

### Step 1: Run Gap Analysis

```bash
# Analyze gaps in implementation
br gaps analyze
```

Output:
```
=== Gap Analysis Summary ===

Total Gaps: 3

By Severity:
  🔴 High:   0 gaps
  🟡 Medium: 2 gaps
  🟢 Low:    1 gap

By Category:
  Features:       1 gap
  Implementation: 1 gap
  Dependencies:   1 gap
```

### Step 2: Review Gap Report

```bash
# Generate detailed report
br gaps analyze --output gap_report.md
```

The report shows:
- Incomplete features
- TODO comments
- Missing tests
- Missing documentation

### Step 3: Address Gaps

Fix any issues found, then mark feature complete:

```bash
# Mark feature as complete
br features update feat-create-todo --status complete
```

## Common Mistakes

### 1. Forgetting to Activate Virtual Environment

**Mistake:**
```bash
pip install fastapi
# ModuleNotFoundError: No module named 'fastapi'
```

**Fix:**
```bash
# Always activate venv first
source .venv/bin/activate
pip install fastapi
```

### 2. Not Updating Features Status

**Mistake:**
Features remain in "planned" status even after implementation.

**Fix:**
```bash
# Update status as you progress
br features update FEATURE_ID --status in_progress
# ... work on feature ...
br features update FEATURE_ID --status complete
```

### 3. Missing Type Hints

**Mistake:**
```python
def create_todo(data):  # No type hints
    return Todo(data.title)
```

**Fix:**
```python
def create_todo(data: TodoCreate) -> Todo:
    return Todo(data.title)
```

### 4. No Tests Written

**Mistake:**
Implementing features without tests.

**Fix:**
Write tests first (TDD) or immediately after implementation.

### 5. Ignoring Quality Checks

**Mistake:**
Not running `br quality check` before committing.

**Fix:**
```bash
# Add pre-commit hook
echo "br quality check --threshold 80" > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### 6. Not Updating PROJECT_SPEC.md

**Mistake:**
Code diverges from spec.

**Fix:**
Keep PROJECT_SPEC.md updated as single source of truth.

## Troubleshooting

### Issue: "Command not found: br"

**Cause:** BuildRunner not installed or not in PATH

**Solution:**
```bash
# Check installation
pip show buildrunner

# If not installed:
pip install buildrunner

# If installed but not in PATH, use full path:
python -m buildrunner.cli
```

### Issue: "No module named 'fastapi'"

**Cause:** Dependencies not installed or venv not activated

**Solution:**
```bash
# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Issue: Quality check fails with "black not found"

**Cause:** Code formatter not installed

**Solution:**
```bash
pip install black bandit
```

### Issue: Tests fail with import errors

**Cause:** Python path not set correctly

**Solution:**
```bash
# Run tests from project root
cd /path/to/my-todo-api
pytest tests/

# Or set PYTHONPATH
export PYTHONPATH=$(pwd)
pytest tests/
```

### Issue: Gap analysis shows "features.json not found"

**Cause:** BuildRunner not initialized

**Solution:**
```bash
# Initialize BuildRunner
br init

# Or create manually:
mkdir -p .buildrunner
echo '{"project": "my-project", "features": []}' > .buildrunner/features.json
```

### Issue: "Port 8000 already in use"

**Cause:** Another process using the port

**Solution:**
```bash
# Use different port
uvicorn api.todos:app --port 8001

# Or kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

## Next Steps

Congratulations! You've completed your first BuildRunner project. Here's what to learn next:

### 1. Design System Integration

Learn to use industry profiles and design systems:
- See [DESIGN_SYSTEM_GUIDE.md](DESIGN_SYSTEM_GUIDE.md)
- Create consistent UIs with Tailwind configs
- Use healthcare, fintech, or e-commerce profiles

### 2. Quality Gates in CI/CD

Automate quality enforcement:
- See [QUALITY_GATES.md](QUALITY_GATES.md)
- Set up pre-commit hooks
- Integrate with GitHub Actions

### 3. Parallel Development

Work on multiple features simultaneously:
- See [PARALLEL_BUILDS.md](PARALLEL_BUILDS.md)
- Use git worktrees
- Orchestrate parallel builds

### 4. Completion Assurance

Ensure nothing is missed:
- See [COMPLETION_ASSURANCE.md](COMPLETION_ASSURANCE.md)
- Use gap analyzer effectively
- Pre-release checklists

### 5. Advanced Features

Explore advanced BuildRunner features:
- Architecture guard (`br guard check`)
- Migration tools (`br migrate`)
- Plugin system
- Dashboard (`br dashboard`)

## Additional Resources

### Documentation

- [Getting Started](../GETTING_STARTED.md)
- [CLI Reference](../CLI_REFERENCE.md)
- [Core Concepts](../CORE_CONCEPTS.md)
- [API Documentation](../API.md)

### Examples

- `examples/healthcare-dashboard/` - Real-world dashboard
- `examples/fintech-api/` - Financial services API
- `examples/ecommerce-marketplace/` - E-commerce platform

### Community

- GitHub: https://github.com/yourusername/buildrunner3
- Issues: Report bugs and request features
- Discussions: Ask questions, share projects

## Summary

You've learned:

✅ How to install and set up BuildRunner
✅ How to initialize a new project
✅ How to create and track features
✅ How to implement features with quality
✅ How to write and run tests
✅ How to use quality checks
✅ How to run gap analysis
✅ Common mistakes and how to avoid them
✅ Troubleshooting common issues

Keep building, and remember: BuildRunner is here to help you maintain quality and completeness throughout your development journey!
