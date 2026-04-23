# Week 2 Resume Prompts - Restart After Interruption

These prompts handle cleanup and fresh restart for interrupted builds.

---

## PROMPT 1: Build 2A - CLI (Fresh Start)

**Copy/paste this entire prompt into Claude Code:**

```
BUILDRUNNER 3.0 - BUILD 2A: CLI (RESUME/RESTART)

═══════════════════════════════════════════════════════════════════

CONTEXT:
- This build was started but interrupted
- Worktree may already exist at: /Users/byronhudson/Projects/br3-cli
- Branch: build/week2-cli
- We will clean and restart fresh

═══════════════════════════════════════════════════════════════════

STEP 1: CLEANUP AND FRESH START

Check if worktree exists and clean it:

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Check worktree status
git worktree list

# If br3-cli exists, check what's there
if [ -d "../br3-cli" ]; then
  cd ../br3-cli
  echo "=== Checking br3-cli worktree ==="
  git status
  ls -la cli/ 2>/dev/null || echo "cli/ doesn't exist yet"

  # If there's uncommitted work, show it
  git diff --stat
  git status --short

  # Go back to main
  cd /Users/byronhudson/Projects/BuildRunner3
fi

# Decision point: Clean restart or continue?
# For CLEAN RESTART (recommended after interruption):
if [ -d "../br3-cli" ]; then
  echo "Removing existing worktree..."
  git worktree remove ../br3-cli --force
  git branch -D build/week2-cli 2>/dev/null || true
fi

# Create fresh worktree
git worktree add ../br3-cli -b build/week2-cli
cd ../br3-cli

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install typer rich watchdog pytest pyyaml pytest-cov
```

═══════════════════════════════════════════════════════════════════

STEP 2: CREATE PROJECT STRUCTURE

Create directories:

```bash
mkdir -p cli
mkdir -p tests
mkdir -p docs/examples
```

═══════════════════════════════════════════════════════════════════

STEP 3: IMPLEMENT CLI CORE

**cli/__init__.py**
```python
"""BuildRunner 3.0 CLI Module"""

__version__ = "3.0.0-alpha.2"
```

**cli/main.py**
```python
#!/usr/bin/env python3
"""BuildRunner 3.0 CLI - Main Entry Point"""

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
from typing import Optional
import sys

from core.feature_registry import FeatureRegistry
from core.status_generator import StatusGenerator
from core.ai_context import AIContextManager

app = typer.Typer(
    name="buildrunner",
    help="BuildRunner 3.0 - AI-native project management",
    add_completion=False
)
console = Console()

@app.command()
def init(project_name: str):
    """Initialize a new BuildRunner project"""
    try:
        buildrunner_dir = Path(".buildrunner")
        buildrunner_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (buildrunner_dir / "context").mkdir(exist_ok=True)
        (buildrunner_dir / "governance").mkdir(exist_ok=True)

        # Initialize features.json
        registry = FeatureRegistry()
        registry.data["project"] = project_name
        registry.data["version"] = "0.1.0"
        registry.data["status"] = "in_development"
        registry.save()

        # Initialize AI context
        ai_context = AIContextManager()
        ai_context.update_memory(f"Initialized project: {project_name}")

        console.print(f"[green]✓[/green] Initialized BuildRunner project: {project_name}")
        console.print(f"[dim]Created .buildrunner/ structure[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

@app.command()
def status():
    """Show project status"""
    try:
        registry = FeatureRegistry()
        data = registry.data

        # Create status table
        table = Table(title=f"Project: {data.get('project', 'Unknown')}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        metrics = data.get("metrics", {})
        table.add_row("Complete", str(metrics.get("features_complete", 0)))
        table.add_row("In Progress", str(metrics.get("features_in_progress", 0)))
        table.add_row("Planned", str(metrics.get("features_planned", 0)))
        table.add_row("Completion", f"{metrics.get('completion_percentage', 0)}%")

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

@app.command()
def generate():
    """Generate STATUS.md from features.json"""
    try:
        generator = StatusGenerator()
        generator.save()
        console.print("[green]✓[/green] Generated .buildrunner/STATUS.md")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

# Feature management subcommand
feature_app = typer.Typer(help="Manage features")

@feature_app.command("add")
def feature_add(
    name: str,
    description: str = "",
    priority: str = "medium",
    week: Optional[int] = None,
    build: Optional[str] = None
):
    """Add a new feature"""
    try:
        registry = FeatureRegistry()

        # Generate ID from name
        feature_id = name.lower().replace(" ", "-")

        feature = registry.add_feature(
            feature_id=feature_id,
            name=name,
            description=description,
            priority=priority,
            week=week,
            build=build
        )

        console.print(f"[green]✓[/green] Added feature: {name} (ID: {feature_id})")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

@feature_app.command("complete")
def feature_complete(feature_id: str):
    """Mark a feature as complete"""
    try:
        registry = FeatureRegistry()
        registry.complete_feature(feature_id)
        console.print(f"[green]✓[/green] Marked feature complete: {feature_id}")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

@feature_app.command("list")
def feature_list(status: Optional[str] = None):
    """List all features"""
    try:
        registry = FeatureRegistry()
        features = registry.data.get("features", [])

        if status:
            features = [f for f in features if f.get("status") == status]

        if not features:
            console.print("[yellow]No features found[/yellow]")
            return

        table = Table(title="Features")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Status", style="green")
        table.add_column("Priority", style="yellow")
        table.add_column("Week", style="blue")

        for feature in features:
            table.add_row(
                feature.get("id", ""),
                feature.get("name", ""),
                feature.get("status", ""),
                feature.get("priority", ""),
                str(feature.get("week", "")) if feature.get("week") else "-"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)

app.add_typer(feature_app, name="feature")

@app.command()
def sync():
    """Trigger Supabase sync (stub)"""
    console.print("[yellow]⚠[/yellow] Supabase sync not yet implemented")

if __name__ == "__main__":
    app()
```

═══════════════════════════════════════════════════════════════════

STEP 4: IMPLEMENT AUTOMATED DEBUGGING

**cli/auto_pipe.py**
```python
"""Command auto-piping with context capture"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Tuple

class CommandPiper:
    """Execute commands and auto-pipe outputs to context"""

    def __init__(self, context_dir: str = ".buildrunner/context"):
        self.context_dir = Path(context_dir)
        self.output_file = self.context_dir / "command-outputs.md"
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def run_and_pipe(self, command: str) -> Tuple[int, str, str]:
        """
        Execute command and pipe output to context
        Returns: (exit_code, stdout, stderr)
        """
        timestamp = datetime.now().isoformat()

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )

        # Write to context
        with open(self.output_file, "a") as f:
            f.write(f"\n## [{timestamp}] `{command}`\n\n")

            if result.stdout:
                f.write(f"### stdout\n```\n{result.stdout}\n```\n\n")

            if result.stderr:
                f.write(f"### stderr\n```\n{result.stderr}\n```\n\n")

            f.write(f"**Exit Code:** {result.returncode}\n\n")
            f.write("---\n\n")

        return result.returncode, result.stdout, result.stderr
```

**cli/error_watcher.py**
```python
"""Error watcher daemon for auto-detection"""

import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import time
import threading

class ErrorWatcher:
    """Watch for errors and auto-update blockers"""

    ERROR_PATTERNS = {
        "syntax": [
            r"SyntaxError",
            r"IndentationError",
            r"unexpected indent"
        ],
        "runtime": [
            r"Traceback \(most recent call last\)",
            r"RuntimeError",
            r"ValueError",
            r"TypeError"
        ],
        "test": [
            r"FAILED",
            r"ERROR",
            r"AssertionError"
        ],
        "git": [
            r"fatal:",
            r"error: ",
            r"merge conflict"
        ],
        "file": [
            r"No such file or directory",
            r"FileNotFoundError",
            r"Permission denied"
        ]
    }

    def __init__(self, context_dir: str = ".buildrunner/context"):
        self.context_dir = Path(context_dir)
        self.blockers_file = self.context_dir / "blockers.md"
        self.command_outputs = self.context_dir / "command-outputs.md"
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start error watcher daemon"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop error watcher daemon"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _watch_loop(self):
        """Main watch loop"""
        while self.running:
            self.check_for_errors()
            time.sleep(10)  # Check every 10 seconds

    def check_for_errors(self) -> List[Dict]:
        """Scan recent outputs for errors"""
        if not self.command_outputs.exists():
            return []

        content = self.command_outputs.read_text()
        errors = []

        # Check each error pattern
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE):
                    errors.append({
                        "category": category,
                        "pattern": pattern,
                        "timestamp": datetime.now().isoformat()
                    })

        # Update blockers if errors found
        if errors:
            self._update_blockers(errors)

        return errors

    def _update_blockers(self, errors: List[Dict]):
        """Update blockers.md with new errors"""
        self.context_dir.mkdir(parents=True, exist_ok=True)

        with open(self.blockers_file, "a") as f:
            f.write(f"\n## Errors Detected: {datetime.now().isoformat()}\n\n")

            for error in errors:
                f.write(f"- **{error['category']}**: {error['pattern']}\n")

            f.write("\n---\n\n")

    def categorize_error(self, error_text: str) -> str:
        """Categorize an error message"""
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_text, re.MULTILINE):
                    return category
        return "unknown"
```

**cli/retry_logic.py**
```python
"""Auto-retry logic with exponential backoff"""

import time
from typing import Callable, Any, Optional
from pathlib import Path
from datetime import datetime

class RetryHandler:
    """Handle command retries with backoff"""

    TRANSIENT_ERRORS = [
        "Connection refused",
        "timeout",
        "Resource temporarily unavailable",
        "Try again",
        "Temporary failure"
    ]

    def __init__(self, max_retries: int = 3, context_dir: str = ".buildrunner/context"):
        self.max_retries = max_retries
        self.context_dir = Path(context_dir)
        self.retry_log = self.context_dir / "retry-log.md"

    def should_retry(self, error_msg: str) -> bool:
        """Check if error is transient and should be retried"""
        return any(pattern in error_msg for pattern in self.TRANSIENT_ERRORS)

    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry function with exponential backoff
        Wait times: 1s, 2s, 4s, 8s
        """
        wait_times = [1, 2, 4, 8]

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)

                if attempt > 0:
                    self._log_retry(func.__name__, attempt, "success")

                return result

            except Exception as e:
                error_msg = str(e)

                # Check if should retry
                if attempt < self.max_retries and self.should_retry(error_msg):
                    wait_time = wait_times[attempt]
                    self._log_retry(func.__name__, attempt + 1, f"retrying after {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    self._log_retry(func.__name__, attempt + 1, f"failed: {error_msg}")
                    raise

    def _log_retry(self, func_name: str, attempt: int, status: str):
        """Log retry attempt to context"""
        self.context_dir.mkdir(parents=True, exist_ok=True)

        with open(self.retry_log, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {func_name} - Attempt {attempt}: {status}\n")
```

**cli/debug_commands.py**
```python
"""Debug commands for CLI"""

import typer
from rich.console import Console
from rich.panel import Panel
import sys
import subprocess
from pathlib import Path

from cli.auto_pipe import CommandPiper
from cli.error_watcher import ErrorWatcher

debug_app = typer.Typer(help="Debugging commands")
console = Console()

@debug_app.command()
def check():
    """Run full diagnostics"""
    console.print(Panel("[bold]BuildRunner Diagnostics[/bold]", style="blue"))

    # Check Python version
    python_version = subprocess.run(["python3", "--version"], capture_output=True, text=True)
    console.print(f"[cyan]Python:[/cyan] {python_version.stdout.strip()}")

    # Check git status
    git_status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    console.print(f"[cyan]Git Status:[/cyan] {'Clean' if not git_status.stdout else 'Modified files'}")

    # Check .buildrunner/ structure
    buildrunner_exists = Path(".buildrunner").exists()
    console.print(f"[cyan].buildrunner/:[/cyan] {'✓ Exists' if buildrunner_exists else '✗ Missing'}")

    # Check for recent errors
    blockers_file = Path(".buildrunner/context/blockers.md")
    if blockers_file.exists():
        console.print(f"[yellow]⚠ Blockers detected[/yellow] - check {blockers_file}")
    else:
        console.print("[green]✓ No blockers[/green]")

@debug_app.command()
def pipe(command: str):
    """Run command with auto-piping"""
    piper = CommandPiper()
    console.print(f"[dim]Running: {command}[/dim]")

    exit_code, stdout, stderr = piper.run_and_pipe(command)

    if stdout:
        console.print(stdout)
    if stderr:
        console.print(f"[red]{stderr}[/red]")

    console.print(f"\n[dim]✓ Output saved to .buildrunner/context/command-outputs.md[/dim]")
    sys.exit(exit_code)

@debug_app.command()
def watch(action: str = "status"):
    """Control error watcher (start/stop/status)"""
    watcher = ErrorWatcher()

    if action == "start":
        watcher.start()
        console.print("[green]✓[/green] Error watcher started")
    elif action == "stop":
        watcher.stop()
        console.print("[yellow]⚠[/yellow] Error watcher stopped")
    elif action == "status":
        console.print(f"[cyan]Watcher:[/cyan] {'Running' if watcher.running else 'Stopped'}")
```

Add to cli/main.py:
```python
from cli.debug_commands import debug_app
app.add_typer(debug_app, name="debug")
```

═══════════════════════════════════════════════════════════════════

STEP 5: IMPLEMENT CONFIG SYSTEM

**cli/config_manager.py**
```python
"""Behavior configuration with hierarchy"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from copy import deepcopy

class ConfigManager:
    """Manage global and project configs"""

    DEFAULT_CONFIG = {
        "behavior": {
            "response_style": "concise",
            "code_display": "snippets",
            "personality": "professional"
        },
        "context": {
            "auto_load": True,
            "max_context_size": 50000
        },
        "automation": {
            "auto_pipe": True,
            "auto_retry": True,
            "error_watch": True,
            "background_tests": False
        }
    }

    def __init__(self):
        self.global_config_path = Path.home() / ".buildrunner" / "global-behavior.yaml"
        self.project_config_path = Path(".buildrunner") / "behavior.yaml"

    def load_config(self) -> Dict[str, Any]:
        """Load and merge configs: Project > Global > Defaults"""
        config = deepcopy(self.DEFAULT_CONFIG)

        # Merge global config
        if self.global_config_path.exists():
            with open(self.global_config_path) as f:
                global_config = yaml.safe_load(f) or {}
                self._deep_merge(config, global_config)

        # Merge project config
        if self.project_config_path.exists():
            with open(self.project_config_path) as f:
                project_config = yaml.safe_load(f) or {}
                self._deep_merge(config, project_config)

        return config

    def get_config(self, key: str) -> Any:
        """Get config value by dot-notation key"""
        config = self.load_config()
        keys = key.split(".")

        value = config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None

        return value

    def set_config(self, key: str, value: Any, scope: str = "project"):
        """Set config value"""
        keys = key.split(".")

        # Choose config file
        if scope == "global":
            config_path = self.global_config_path
        else:
            config_path = self.project_config_path

        # Load existing config
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Set value
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

        # Save
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    def validate_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """Validate config against schema"""
        errors = []

        # Check valid keys
        valid_sections = ["behavior", "context", "automation"]
        for section in config.keys():
            if section not in valid_sections:
                errors.append(f"Unknown section: {section}")

        # Validate behavior section
        if "behavior" in config:
            valid_styles = ["concise", "detailed", "technical"]
            style = config["behavior"].get("response_style")
            if style and style not in valid_styles:
                errors.append(f"Invalid response_style: {style}")

        return (len(errors) == 0, errors)

    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge override into base"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
```

**cli/config_commands.py**
```python
"""Config management commands"""

import typer
from rich.console import Console
from rich.table import Table
import yaml

from cli.config_manager import ConfigManager

config_app = typer.Typer(help="Manage configuration")
console = Console()

@config_app.command()
def init(global_scope: bool = False):
    """Create config file from template"""
    manager = ConfigManager()

    if global_scope:
        config_path = manager.global_config_path
        scope_name = "global"
    else:
        config_path = manager.project_config_path
        scope_name = "project"

    # Create config with defaults
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(manager.DEFAULT_CONFIG, f, default_flow_style=False)

    console.print(f"[green]✓[/green] Created {scope_name} config: {config_path}")

@config_app.command()
def get(key: str):
    """Get config value"""
    manager = ConfigManager()
    value = manager.get_config(key)

    if value is None:
        console.print(f"[red]✗[/red] Key not found: {key}")
    else:
        console.print(f"[cyan]{key}:[/cyan] {value}")

@config_app.command()
def set(key: str, value: str, global_scope: bool = False):
    """Set config value"""
    manager = ConfigManager()
    scope = "global" if global_scope else "project"

    # Convert value to appropriate type
    if value.lower() in ["true", "false"]:
        value = value.lower() == "true"
    elif value.isdigit():
        value = int(value)

    manager.set_config(key, value, scope)
    console.print(f"[green]✓[/green] Set {key} = {value} ({scope})")

@config_app.command("list")
def list_config():
    """Show all config"""
    manager = ConfigManager()
    config = manager.load_config()

    table = Table(title="Configuration (Merged)")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    def flatten(d, prefix=""):
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flatten(value, full_key)
            else:
                table.add_row(full_key, str(value))

    flatten(config)
    console.print(table)
```

Add to cli/main.py:
```python
from cli.config_commands import config_app
app.add_typer(config_app, name="config")
```

═══════════════════════════════════════════════════════════════════

STEP 6: WRITE TESTS

Create comprehensive test files:

**tests/test_cli.py** - Test core commands
**tests/test_config_manager.py** - Test config hierarchy
**tests/test_auto_pipe.py** - Test command piping
**tests/test_error_watcher.py** - Test error detection
**tests/test_retry_logic.py** - Test auto-retry

Run tests:
```bash
source .venv/bin/activate
pytest tests/test_cli.py tests/test_config_manager.py tests/test_auto_pipe.py tests/test_error_watcher.py tests/test_retry_logic.py -v --cov=cli --cov-report=term-missing
```

═══════════════════════════════════════════════════════════════════

STEP 7: CREATE DOCUMENTATION

**docs/CLI.md** - Complete command reference
**docs/AUTOMATED_DEBUGGING.md** - Debug features guide
**docs/BEHAVIOR_CONFIG.md** - Config system guide

**docs/examples/global-behavior.yaml** - Example global config
**docs/examples/project-behavior.yaml** - Example project config

═══════════════════════════════════════════════════════════════════

STEP 8: COMMIT

```bash
git add .
git commit -m "feat: Implement CLI with automated debugging and behavior config (Build 2A)

Features:
- Core CLI commands: init, feature (add/complete/list), status, generate, sync
- Automated debugging: debug check/pipe/watch
- Behavior config system with global/project hierarchy
- Auto-piping command outputs to context
- Error watcher daemon with auto-blocker updates
- Auto-retry logic with exponential backoff
- Rich formatting for professional output

Tests:
- Comprehensive test suite for all CLI modules
- 85%+ coverage target

Documentation:
- CLI command reference
- Automated debugging guide
- Behavior config guide
- Example configs"
```

═══════════════════════════════════════════════════════════════════

DO NOT MERGE - Wait for Build 2C integration.
```

---

## PROMPT 2: Build 2B - API (Fresh Start)

**Copy/paste this entire prompt into Claude Code:**

```
BUILDRUNNER 3.0 - BUILD 2B: API (RESUME/RESTART)

═══════════════════════════════════════════════════════════════════

CONTEXT:
- This build was started but interrupted
- Worktree may already exist at: /Users/byronhudson/Projects/br3-api
- Branch: build/week2-api
- We will clean and restart fresh

═══════════════════════════════════════════════════════════════════

STEP 1: CLEANUP AND FRESH START

Check if worktree exists and clean it:

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Check worktree status
git worktree list

# If br3-api exists, check what's there
if [ -d "../br3-api" ]; then
  cd ../br3-api
  echo "=== Checking br3-api worktree ==="
  git status
  ls -la api/ 2>/dev/null || echo "api/ doesn't exist yet"

  # If there's uncommitted work, show it
  git diff --stat
  git status --short

  # Go back to main
  cd /Users/byronhudson/Projects/BuildRunner3
fi

# Decision point: Clean restart or continue?
# For CLEAN RESTART (recommended after interruption):
if [ -d "../br3-api" ]; then
  echo "Removing existing worktree..."
  git worktree remove ../br3-api --force
  git branch -D build/week2-api 2>/dev/null || true
fi

# Create fresh worktree
git worktree add ../br3-api -b build/week2-api
cd ../br3-api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn pytest httpx python-dotenv pytest-asyncio aiofiles pyyaml websockets pytest-cov
```

═══════════════════════════════════════════════════════════════════

STEP 2: CREATE PROJECT STRUCTURE

Create directories:

```bash
mkdir -p api/routes
mkdir -p tests
mkdir -p docs
```

═══════════════════════════════════════════════════════════════════

STEP 3: IMPLEMENT FASTAPI CORE

**api/__init__.py**
```python
"""BuildRunner 3.0 API Module"""

__version__ = "3.0.0-alpha.2"
```

**api/models.py**
```python
"""Pydantic models for API"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class FeatureModel(BaseModel):
    id: str
    name: str
    status: str
    version: str
    priority: str
    week: Optional[int] = None
    build: Optional[str] = None
    description: str

class ConfigModel(BaseModel):
    source: str  # default, global, project
    config: Dict[str, Any]

class ErrorModel(BaseModel):
    id: str
    timestamp: datetime
    category: str
    message: str
    source: str
    suggested_fix: Optional[str] = None

class TestResultModel(BaseModel):
    timestamp: datetime
    total: int
    passed: int
    failed: int
    errors: int
    duration: float
    failures: List[Dict[str, str]] = []

class MetricsModel(BaseModel):
    features_complete: int
    features_in_progress: int
    features_planned: int
    completion_percentage: int
    total_tests: int = 0
    test_pass_rate: float = 0.0
    active_blockers: int = 0
```

**api/main.py**
```python
"""FastAPI Application"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import time
from pathlib import Path

from api.models import FeatureModel, MetricsModel
from core.feature_registry import FeatureRegistry
from core.status_generator import StatusGenerator

# Create app
app = FastAPI(
    title="BuildRunner 3.0 API",
    version="3.0.0-alpha.2",
    description="AI-native project management API"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all requests to context"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Log to context
    log_file = Path(".buildrunner/context/api-requests.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "a") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] {request.method} {request.url.path} - {response.status_code} ({duration*1000:.2f}ms)\n")

    return response

# Routes
@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "3.0.0-alpha.2",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/features", response_model=List[FeatureModel])
async def get_features(status: Optional[str] = None):
    """Get all features"""
    try:
        registry = FeatureRegistry()
        features = registry.data.get("features", [])

        if status:
            features = [f for f in features if f.get("status") == status]

        return features
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/features/{feature_id}", response_model=FeatureModel)
async def get_feature(feature_id: str):
    """Get single feature"""
    try:
        registry = FeatureRegistry()
        feature = registry.get_feature(feature_id)

        if not feature:
            raise HTTPException(status_code=404, detail=f"Feature not found: {feature_id}")

        return feature
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/features", response_model=FeatureModel)
async def create_feature(feature: FeatureModel):
    """Create new feature"""
    try:
        registry = FeatureRegistry()
        created = registry.add_feature(
            feature_id=feature.id,
            name=feature.name,
            description=feature.description,
            priority=feature.priority,
            week=feature.week,
            build=feature.build
        )
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/features/{feature_id}", response_model=FeatureModel)
async def update_feature(feature_id: str, updates: Dict[str, Any]):
    """Update feature"""
    try:
        registry = FeatureRegistry()
        updated = registry.update_feature(feature_id, updates)

        if not updated:
            raise HTTPException(status_code=404, detail=f"Feature not found: {feature_id}")

        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/features/{feature_id}")
async def delete_feature(feature_id: str):
    """Delete feature"""
    try:
        registry = FeatureRegistry()
        registry.delete_feature(feature_id)
        return {"status": "deleted", "feature_id": feature_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics", response_model=MetricsModel)
async def get_metrics():
    """Get project metrics"""
    try:
        registry = FeatureRegistry()
        metrics = registry.data.get("metrics", {})
        return MetricsModel(**metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate_status():
    """Generate STATUS.md"""
    try:
        generator = StatusGenerator()
        generator.save()
        return {"status": "generated", "file": ".buildrunner/STATUS.md"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync")
async def sync_supabase():
    """Trigger Supabase sync (stub)"""
    return {"status": "not_implemented", "message": "Supabase sync coming in Week 3"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

═══════════════════════════════════════════════════════════════════

STEP 4: IMPLEMENT CONFIG ENDPOINTS

**api/config_service.py**
```python
"""Config service for API"""

import yaml
from pathlib import Path
from typing import Dict, Any
from copy import deepcopy

class ConfigService:
    """Load and manage configs"""

    DEFAULT_CONFIG = {
        "behavior": {
            "response_style": "concise",
            "code_display": "snippets",
            "personality": "professional"
        },
        "context": {
            "auto_load": True,
            "max_context_size": 50000
        },
        "automation": {
            "auto_pipe": True,
            "auto_retry": True,
            "error_watch": True,
            "background_tests": False
        }
    }

    def __init__(self):
        self.global_config_path = Path.home() / ".buildrunner" / "global-behavior.yaml"
        self.project_config_path = Path(".buildrunner") / "behavior.yaml"

    def load_global_config(self) -> Dict[str, Any]:
        """Load global config"""
        if self.global_config_path.exists():
            with open(self.global_config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def load_project_config(self) -> Dict[str, Any]:
        """Load project config"""
        if self.project_config_path.exists():
            with open(self.project_config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def merge_configs(self) -> Dict[str, Any]:
        """Merge configs with hierarchy"""
        config = deepcopy(self.DEFAULT_CONFIG)

        # Merge global
        global_config = self.load_global_config()
        self._deep_merge(config, global_config)

        # Merge project
        project_config = self.load_project_config()
        self._deep_merge(config, project_config)

        return config

    def save_project_config(self, config: Dict[str, Any]):
        """Save project config"""
        self.project_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.project_config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
```

**api/routes/config.py**
```python
"""Config management endpoints"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from api.config_service import ConfigService
from api.models import ConfigModel

router = APIRouter(prefix="/config", tags=["config"])
config_service = ConfigService()

@router.get("", response_model=ConfigModel)
async def get_config():
    """Get merged config"""
    config = config_service.merge_configs()
    return ConfigModel(source="merged", config=config)

@router.get("/global", response_model=ConfigModel)
async def get_global_config():
    """Get global config only"""
    config = config_service.load_global_config()
    return ConfigModel(source="global", config=config)

@router.get("/project", response_model=ConfigModel)
async def get_project_config():
    """Get project config only"""
    config = config_service.load_project_config()
    return ConfigModel(source="project", config=config)

@router.patch("/project", response_model=ConfigModel)
async def update_project_config(updates: Dict[str, Any]):
    """Update project config"""
    try:
        # Load existing
        config = config_service.load_project_config()

        # Apply updates
        config.update(updates)

        # Save
        config_service.save_project_config(config)

        # Return merged
        merged = config_service.merge_configs()
        return ConfigModel(source="merged", config=merged)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema")
async def get_schema():
    """Get config schema"""
    return config_service.DEFAULT_CONFIG
```

Add to api/main.py:
```python
from api.routes.config import router as config_router
app.include_router(config_router)
```

═══════════════════════════════════════════════════════════════════

STEP 5: IMPLEMENT DEBUG ENDPOINTS

**api/error_watcher.py**
```python
"""Error watcher for API"""

import re
from pathlib import Path
from datetime import datetime
from typing import List
from api.models import ErrorModel
import uuid

class ErrorWatcherAPI:
    """Scan context for errors"""

    ERROR_PATTERNS = {
        "syntax": [r"SyntaxError", r"IndentationError"],
        "runtime": [r"Traceback", r"RuntimeError", r"ValueError"],
        "test": [r"FAILED", r"AssertionError"],
        "git": [r"fatal:", r"merge conflict"],
        "file": [r"No such file", r"FileNotFoundError"]
    }

    FIX_SUGGESTIONS = {
        "ModuleNotFoundError": "Run: pip install <module_name>",
        "FAILED": "Check test file and fix assertions",
        "merge conflict": "Run: git status and resolve conflicts",
        "Permission denied": "Run: chmod +x <file>"
    }

    def __init__(self, context_dir: str = ".buildrunner/context"):
        self.context_dir = Path(context_dir)

    def scan_context(self) -> List[ErrorModel]:
        """Scan for errors"""
        errors = []

        # Scan command outputs
        outputs_file = self.context_dir / "command-outputs.md"
        if outputs_file.exists():
            content = outputs_file.read_text()
            errors.extend(self._scan_content(content, "command-outputs.md"))

        # Scan blockers
        blockers_file = self.context_dir / "blockers.md"
        if blockers_file.exists():
            content = blockers_file.read_text()
            errors.extend(self._scan_content(content, "blockers.md"))

        return errors

    def _scan_content(self, content: str, source: str) -> List[ErrorModel]:
        """Scan content for error patterns"""
        errors = []

        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    error_text = match.group()
                    errors.append(ErrorModel(
                        id=str(uuid.uuid4())[:8],
                        timestamp=datetime.utcnow(),
                        category=category,
                        message=error_text,
                        source=source,
                        suggested_fix=self.suggest_fix(error_text)
                    ))

        return errors

    def suggest_fix(self, error_text: str) -> str:
        """Suggest fix based on error"""
        for pattern, suggestion in self.FIX_SUGGESTIONS.items():
            if pattern in error_text:
                return suggestion
        return None
```

**api/routes/debug.py**
```python
"""Debug endpoints"""

from fastapi import APIRouter, HTTPException
from typing import List
import subprocess
from pathlib import Path

from api.models import ErrorModel
from api.error_watcher import ErrorWatcherAPI

router = APIRouter(prefix="/debug", tags=["debug"])
error_watcher = ErrorWatcherAPI()

@router.get("/status")
async def debug_status():
    """System diagnostics"""
    return {
        "python_version": subprocess.run(["python3", "--version"], capture_output=True, text=True).stdout.strip(),
        "git_branch": subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip(),
        "buildrunner_exists": Path(".buildrunner").exists(),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/blockers")
async def get_blockers():
    """Get current blockers"""
    blockers_file = Path(".buildrunner/context/blockers.md")
    if not blockers_file.exists():
        return {"blockers": []}

    content = blockers_file.read_text()
    return {"blockers": content.split("\n---\n")}

@router.get("/errors", response_model=List[ErrorModel])
async def get_errors():
    """Get recent errors"""
    try:
        errors = error_watcher.scan_context()
        return errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def run_tests():
    """Run test suite"""
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True
        )

        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

Add to api/main.py:
```python
from api.routes.debug import router as debug_router
app.include_router(debug_router)
```

═══════════════════════════════════════════════════════════════════

STEP 6: WRITE TESTS

**tests/test_api.py** - Test core endpoints
**tests/test_api_config.py** - Test config endpoints
**tests/test_api_debug.py** - Test debug endpoints
**tests/test_config_service.py** - Test config service
**tests/test_error_watcher.py** - Test error detection

Run tests:
```bash
source .venv/bin/activate
pytest tests/test_api*.py tests/test_config_service.py tests/test_error_watcher.py -v --cov=api --cov-report=term-missing
```

═══════════════════════════════════════════════════════════════════

STEP 7: CREATE DOCUMENTATION

**docs/API.md** - Complete API reference with examples
**docs/API_DEBUGGING.md** - Debug endpoints guide

═══════════════════════════════════════════════════════════════════

STEP 8: TEST MANUALLY

Start server:
```bash
source .venv/bin/activate
uvicorn api.main:app --reload
```

Test endpoints:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/features
curl http://localhost:8000/config
curl http://localhost:8000/debug/status
```

Visit http://localhost:8000/docs for interactive API docs

═══════════════════════════════════════════════════════════════════

STEP 9: COMMIT

```bash
git add .
git commit -m "feat: Implement FastAPI backend with config and debug endpoints (Build 2B)

Features:
- Core endpoints: features, metrics, generate
- Config endpoints with global/project hierarchy
- Debug endpoints: status, blockers, errors, test
- Error watcher API with categorization and fix suggestions
- Request logging middleware
- OpenAPI docs auto-generated

Tests:
- Comprehensive test suite for all API modules
- 85%+ coverage target

Documentation:
- Complete API reference
- API debugging guide"
```

═══════════════════════════════════════════════════════════════════

DO NOT MERGE - Wait for Build 2C integration.
```

---

## PROMPT 3: Build 2C - Integration (After 2A & 2B Complete)

**⚠️ ONLY RUN THIS AFTER BUILDS 2A AND 2B ARE COMMITTED**

**Copy/paste this entire prompt into Claude Code:**

```
BUILDRUNNER 3.0 - BUILD 2C: INTEGRATION + PRD

═══════════════════════════════════════════════════════════════════

CONTEXT:
- Builds 2A (CLI) and 2B (API) are complete and committed
- Working in main branch: /Users/byronhudson/Projects/BuildRunner3
- Will merge both branches and implement PRD system

═══════════════════════════════════════════════════════════════════

STEP 1: VERIFY BUILDS ARE READY

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Check both branches have commits
echo "=== Build 2A (CLI) ==="
git log build/week2-cli --oneline -3

echo "=== Build 2B (API) ==="
git log build/week2-api --oneline -3

# If either shows no new commits, STOP and complete that build first
```

═══════════════════════════════════════════════════════════════════

STEP 2: MERGE BUILD 2A (CLI)

```bash
git merge --no-ff build/week2-cli -m "Merge Build 2A: CLI with automated debugging and behavior config"
```

If conflicts:
- Review with: `git status`
- Resolve conflicts
- `git add <resolved files>`
- `git commit`

═══════════════════════════════════════════════════════════════════

STEP 3: MERGE BUILD 2B (API)

```bash
git merge --no-ff build/week2-api -m "Merge Build 2B: FastAPI backend with config and debug endpoints"
```

If conflicts:
- Review and resolve
- Likely in: core/__init__.py, tests/__init__.py
- Combine imports from both builds

═══════════════════════════════════════════════════════════════════

STEP 4: RUN INTEGRATION TESTS

```bash
# Activate venv (create if needed)
python3 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install typer rich watchdog fastapi uvicorn pytest httpx python-dotenv pytest-asyncio aiofiles pyyaml websockets pytest-cov GitPython

# Run all tests
pytest tests/ -v --cov --cov-report=term-missing

# If tests fail, fix integration issues and re-run
```

═══════════════════════════════════════════════════════════════════

STEP 5: IMPLEMENT PRD SYSTEM

Create .buildrunner/PRD.md template, core/prd_parser.py, core/prd_mapper.py, cli/prd_commands.py

Add PRD commands to CLI and write tests.

(See full implementation details in original WEEK2_EXECUTABLE_PROMPTS.md STEP 6)

═══════════════════════════════════════════════════════════════════

STEP 6: FINAL TESTING

```bash
# Run full test suite
pytest tests/ -v --cov --cov-report=term-missing --cov-report=html

# Manual CLI tests
python -m cli.main --help
python -m cli.main status
python -m cli.main config list

# Manual API tests (in separate terminal)
uvicorn api.main:app --reload
# Then: curl http://localhost:8000/health
```

═══════════════════════════════════════════════════════════════════

STEP 7: COMMIT AND TAG

```bash
git add .
git commit -m "feat: Complete Week 2 Integration with PRD System (Build 2C)"

git tag -a v3.0.0-alpha.2 -m "BuildRunner 3.0 Alpha 2 Release

Week 2 Complete: CLI + API + PRD System"
```

═══════════════════════════════════════════════════════════════════

STEP 8: CLEANUP WORKTREES

```bash
git worktree remove ../br3-cli
git worktree remove ../br3-api
git branch -d build/week2-cli
git branch -d build/week2-api
```

═══════════════════════════════════════════════════════════════════

Week 2 COMPLETE!
```

---

These prompts handle the interrupted state and provide clean restart instructions with all setup included.