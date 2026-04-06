# Project Alias System (feat-014)

**Status:** Complete
**Version:** 3.2.0-alpha.2

## Overview

The Project Alias System allows you to register BuildRunner projects with short aliases and launch them instantly from any terminal with a single command.

**Key Features:**
- ✅ Register projects with memorable aliases (e.g., "sales", "myapp")
- ✅ Shell integration (automatic `.zshrc`/`.bashrc` aliases)
- ✅ Launch Claude Code/Cursor/Windsurf with one command
- ✅ Initialize new projects with interactive planning mode
- ✅ Attach existing projects quickly
- ✅ Project registry at `~/.buildrunner/projects.json`
- ✅ Automatic backup of shell config before modification

---

## Quick Start

### Initialize a New Project

```bash
cd ~/Projects/my-new-project
br project init myapp
```

**What happens:**
1. Creates `.buildrunner/` directory
2. Enters planning mode (asks questions about your project)
3. Generates `PROJECT_SPEC.md`
4. Registers project with alias "myapp"
5. Adds shell alias to `~/.zshrc`

**Result:** Type `myapp` anywhere to launch Claude Code in that project!

---

### Attach an Existing Project

```bash
cd ~/Projects/sales-assistant
br project attach sales
```

**What happens:**
1. Registers project with alias "sales"
2. Creates minimal `PROJECT_SPEC.md` if missing
3. Adds shell alias to `~/.zshrc`

**Result:** Type `sales` anywhere to launch Claude Code in that project!

---

### List All Projects

```bash
br project list
```

Shows all registered projects with validation status.

---

### Remove a Project

```bash
br project remove myapp
```

Removes from registry and removes shell alias.

---

## Commands

### `br project init [alias]`

Initialize a new BuildRunner project with interactive planning mode.

**Options:**
- `--dir, -d` - Project directory (default: current directory)
- `--template, -t` - Planning template: quick, standard, complete (default: standard)
- `--editor, -e` - Editor preference: claude, cursor, windsurf (default: claude)
- `--skip-planning` - Skip planning mode, just create structure

**Example:**
```bash
cd ~/Projects/my-app
br project init myapp --template complete --editor cursor
```

---

### `br project attach <alias>`

Register an existing project with an alias.

**Options:**
- `--dir, -d` - Project directory (default: current directory)
- `--editor, -e` - Editor preference: claude, cursor, windsurf (default: claude)
- `--scan` - Scan codebase and generate PROJECT_SPEC.md

**Example:**
```bash
cd ~/Projects/existing-app
br project attach app --scan
```

---

### `br project list`

List all registered projects with validation status.

**Output:**
```
Registered Projects (3)

┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┓
┃ Alias    ┃ Path                           ┃ Editor ┃ Status     ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━┩
│ br3      │ /Users/you/Projects/BR3        │ claude │ ✅ Valid   │
│ myapp    │ /Users/you/Projects/myapp      │ cursor │ ✅ Valid   │
│ sales    │ /Users/you/Projects/sales      │ claude │ ✅ Valid   │
└──────────┴────────────────────────────────┴────────┴────────────┘
```

---

### `br project remove <alias>`

Remove a project from registry.

**Options:**
- `--keep-shell-alias` - Keep the shell alias in config file

**Example:**
```bash
br project remove old-app
```

---

### `br project jump <alias>`

Jump to a project (alternative to direct alias).

**Example:**
```bash
br project jump sales
# Same as: sales
```

**Use this when:**
- Shell aliases haven't been loaded yet
- Testing project launch without shell reload

---

## Shell Integration

### How It Works

When you register a project, BuildRunner adds an alias to your shell config:

**In `~/.zshrc` or `~/.bashrc`:**
```bash
# BuildRunner Project Aliases - DO NOT EDIT MANUALLY
alias br3='cd /Users/you/Projects/BuildRunner3 && claude --dangerously-skip-permissions'
alias myapp='cd /Users/you/Projects/myapp && cursor --disable-extensions'
alias sales='cd /Users/you/Projects/sales-assistant && claude --dangerously-skip-permissions'
# End BuildRunner Project Aliases
```

### Activation

After registering a project, reload your shell:

```bash
source ~/.zshrc
# or
source ~/.bashrc
```

**From then on:** Just type the alias anywhere to launch!

```bash
sales    # Opens Claude Code in sales-assistant project
```

---

## Project Registry

Projects are stored in: `~/.buildrunner/projects.json`

**Format:**
```json
{
  "sales": {
    "alias": "sales",
    "path": "/Users/you/Projects/sales-assistant",
    "created": "2025-11-24T20:00:00",
    "editor": "claude",
    "spec_path": ".buildrunner/PROJECT_SPEC.md",
    "last_accessed": "2025-11-24T21:00:00"
  },
  "myapp": {
    "alias": "myapp",
    "path": "/Users/you/Projects/myapp",
    "created": "2025-11-24T19:00:00",
    "editor": "cursor",
    "spec_path": ".buildrunner/PROJECT_SPEC.md",
    "last_accessed": null
  }
}
```

---

## Editor Support

### Claude Code (default)

```bash
br project attach myapp --editor claude
```

**Launch command:**
```bash
claude --dangerously-skip-permissions
```

### Cursor

```bash
br project attach myapp --editor cursor
```

**Launch command:**
```bash
cursor --disable-extensions
```

### Windsurf

```bash
br project attach myapp --editor windsurf
```

**Launch command:**
```bash
windsurf
```

---

## Planning Mode Integration

When you run `br project init`, you enter planning mode which asks:

**Standard Template (default):**
1. Project name?
2. What does it do?
3. Key features?
4. Tech stack?
5. User stories?
6. Success criteria?

**Quick Template:**
- Just feature list
- Minimal details
- Fast setup (~5 min)

**Complete Template:**
- Everything in Standard
- API specifications
- Architecture diagrams
- Risk assessment
- Test scenarios
- Effort estimates

Planning mode generates a complete `PROJECT_SPEC.md` that becomes your single source of truth.

---

## Architecture

### Components

**1. ProjectRegistry** (`core/project_registry.py`)
- Stores project metadata
- Validates project structure
- Manages `~/.buildrunner/projects.json`

**2. ShellIntegration** (`core/shell_integration.py`)
- Manages shell config files
- Adds/removes aliases
- Auto-detects shell (zsh/bash)
- Creates backups before modification

**3. ProjectCommands** (`cli/project_commands.py`)
- CLI commands (init, attach, list, remove, jump)
- User interaction and prompts
- Integrates with planning mode

### Data Flow

```
User runs: br project attach sales
         ↓
1. Validate directory exists
2. Create .buildrunner/ if needed
3. Register in ProjectRegistry
         ↓
4. ShellIntegration adds alias to ~/.zshrc
         ↓
5. User reloads shell: source ~/.zshrc
         ↓
6. User types: sales
         ↓
7. Shell executes: cd ~/Projects/sales && claude --dangerously-skip-permissions
         ↓
8. Claude Code launches in project!
```

---

## Security & Safety

### Backups

Before modifying shell config, a backup is created:

```bash
~/.zshrc.backup.20251124_200000
```

### Validation

Before launching, validates:
- ✅ Project path still exists
- ✅ `.buildrunner/` directory present
- ✅ `PROJECT_SPEC.md` exists

### Markers

Shell aliases are wrapped in markers to prevent accidental editing:

```bash
# BuildRunner Project Aliases - DO NOT EDIT MANUALLY
# ... aliases here ...
# End BuildRunner Project Aliases
```

---

## Troubleshooting

### Alias doesn't work after registration

**Problem:** Typed `myapp` but command not found

**Solution:** Reload your shell
```bash
source ~/.zshrc
# or restart terminal
```

---

### Alias points to wrong directory

**Problem:** Project was moved

**Solution:** Re-register with same alias
```bash
cd /new/location
br project attach myapp  # Updates existing registration
```

---

### Editor command not found

**Problem:** `claude: command not found`

**Solution:** Install editor CLI
- Claude Code: https://code.claude.ai
- Cursor: https://cursor.sh
- Windsurf: https://windsurf.ai

---

### Project validation fails

**Problem:** `br project list` shows "❌ Missing" or "⚠️ Incomplete"

**Solution:**
```bash
br project jump myapp  # Check error message
# Fix missing files, then:
br project attach myapp  # Re-register
```

---

### Want to use different shell config

**Problem:** Using `.bash_profile` not `.zshrc`

**Solution:** ShellIntegration auto-detects. If multiple configs exist, it uses the first found:
1. `.zshrc` (preferred)
2. `.bashrc`
3. `.bash_profile`

Manually specify by editing the first time, then aliases work.

---

## Future Enhancements

Potential improvements beyond current scope:

1. **Multi-editor support per project** - Different aliases for same project with different editors
2. **Project templates** - Pre-configured project structures
3. **Team sharing** - Share project registry with team via git
4. **Remote projects** - SSH-based project aliases
5. **Project groups** - Organize projects into folders/groups
6. **Auto-detection** - Detect BuildRunner projects in parent directories
7. **VS Code integration** - Launch with `code` command
8. **Custom launch scripts** - Run scripts before/after launch

---

## API Reference

### ProjectRegistry

```python
from core.project_registry import get_project_registry

registry = get_project_registry()

# Register project
project = registry.register_project(
    alias="myapp",
    project_path=Path("/path/to/project"),
    editor="claude",
    spec_path=".buildrunner/PROJECT_SPEC.md"
)

# Get project
project = registry.get_project("myapp")

# List all
projects = registry.list_projects()

# Remove
registry.remove_project("myapp")

# Validate
validation = registry.validate_project("myapp")
```

### ShellIntegration

```python
from core.shell_integration import get_shell_integration

shell = get_shell_integration()

# Add alias
shell.add_alias(
    alias="myapp",
    project_path="/path/to/project",
    editor="claude"
)

# Remove alias
shell.remove_alias("myapp")

# List aliases
aliases = shell.list_aliases()

# Get config path
config_path = shell.get_primary_config()
```

---

## Summary

The Project Alias System makes BuildRunner projects instantly accessible:

**Before:**
```bash
cd ~/Projects/long/path/to/sales-assistant
claude --dangerously-skip-permissions
```

**After:**
```bash
sales  # Done!
```

**Benefits:**
- ⚡ Instant project switching
- 🎯 Memorable aliases
- 🔧 Editor preferences per project
- 📋 Centralized project registry
- 🔒 Safe shell config modification

**Perfect for:**
- Managing multiple BuildRunner projects
- Quick context switching
- Team onboarding (share aliases)
- Daily development workflow

---

**Documentation Generated:** 2025-11-24
**BuildRunner Version:** 3.2.0-alpha.2
**Feature:** feat-014
