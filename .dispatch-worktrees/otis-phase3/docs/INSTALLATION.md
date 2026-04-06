# Installation Guide

**Complete installation instructions for BuildRunner 3.0 across all platforms.**

---

## Table of Contents

- [Quick Install](#quick-install)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [pip (Recommended)](#pip-recommended)
  - [Homebrew (macOS)](#homebrew-macos)
  - [Docker](#docker)
  - [From Source](#from-source)
- [Verification](#verification)
- [Post-Installation](#post-installation)
- [Troubleshooting](#troubleshooting)
- [Platform-Specific Notes](#platform-specific-notes)
- [Upgrading](#upgrading)
- [Uninstallation](#uninstallation)

---

## Quick Install

### macOS / Linux

```bash
# Using pip
pip install buildrunner

# OR using Homebrew (macOS)
brew install buildrunner

# Verify installation
br --version
```

### Windows

```powershell
# Using pip
pip install buildrunner

# Verify installation
br --version
```

---

## Prerequisites

### Python Version

- **Required:** Python 3.11 or higher
- **Recommended:** Python 3.12+

**Check your Python version:**
```bash
python3 --version
# Output: Python 3.11.x or higher
```

**Install Python if needed:**
- **macOS:** `brew install python@3.12`
- **Linux:** `sudo apt install python3.12` (Ubuntu/Debian)
- **Windows:** Download from [python.org](https://www.python.org/downloads/)

### System Requirements

| Platform | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 512 MB | 1 GB+ |
| **Disk** | 100 MB | 500 MB+ |
| **OS** | macOS 10.15+, Linux, Windows 10+ | Latest stable |

### Optional Dependencies

For full functionality, you may need:
- **Git:** Version control (required)
- **Node.js:** For MCP integration with Claude Code
- **Docker:** For containerized workflows (optional)

---

## Installation Methods

### pip (Recommended)

**Advantages:**
- ✅ Cross-platform (macOS, Linux, Windows)
- ✅ Easy updates
- ✅ Works in virtual environments
- ✅ No admin/sudo required (with `--user`)

**Installation:**

```bash
# Install globally
pip install buildrunner

# OR install for current user only (no sudo)
pip install --user buildrunner

# OR install in virtual environment (recommended for dev)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install buildrunner
```

**With optional dependencies:**
```bash
# Install with development tools
pip install "buildrunner[dev]"

# Install with all optional features
pip install "buildrunner[all]"
```

---

### Homebrew (macOS)

**Advantages:**
- ✅ Native macOS integration
- ✅ Automatic dependency management
- ✅ Easy updates via `brew upgrade`

**Installation:**

```bash
# Add BuildRunner tap (if not already added)
brew tap buildrunner/buildrunner

# Install BuildRunner
brew install buildrunner

# Verify installation
br --version
```

**Update:**
```bash
brew upgrade buildrunner
```

**Uninstall:**
```bash
brew uninstall buildrunner
```

---

### Docker

**Advantages:**
- ✅ No local Python installation needed
- ✅ Isolated environment
- ✅ Consistent across platforms
- ✅ Perfect for CI/CD

**Installation:**

```bash
# Pull latest image
docker pull buildrunner/buildrunner:latest

# Create alias for convenience
alias br="docker run -it --rm -v $(pwd):/project -w /project buildrunner/buildrunner"

# Add alias to shell profile for persistence
echo 'alias br="docker run -it --rm -v $(pwd):/project -w /project buildrunner/buildrunner"' >> ~/.zshrc
source ~/.zshrc
```

**Usage:**
```bash
# All br commands work the same
br init my-project
br status
br feature add "User authentication"
```

**Specific Version:**
```bash
# Pull specific version
docker pull buildrunner/buildrunner:3.0.0

# Use specific version
alias br="docker run -it --rm -v $(pwd):/project -w /project buildrunner/buildrunner:3.0.0"
```

---

### From Source

**When to use:**
- 🔧 Contributing to BuildRunner development
- 🔧 Testing unreleased features
- 🔧 Custom modifications

**Prerequisites:**
- Git
- Python 3.11+
- pip

**Installation:**

```bash
# Clone repository
git clone https://github.com/buildrunner/buildrunner.git
cd buildrunner

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
br --version
# Output: BuildRunner 3.0.0 (development)
```

**Run tests:**
```bash
pytest tests/
```

**Build package:**
```bash
python -m build
```

---

## Verification

### Test Installation

```bash
# Check version
br --version
# Output: BuildRunner 3.0.0

# Check help
br --help
# Output: List of all commands

# Run diagnostic
br config list
# Output: Current configuration
```

### Create Test Project

```bash
# Initialize test project
br init test-project
cd test-project

# Check project status
br status
# Output: Project status display

# Success! BuildRunner is working.
```

---

## Post-Installation

### 1. Configure Git (if not already configured)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 2. Set Up MCP Integration (Optional - for Claude Code)

Add to `~/.config/claude/config.json`:
```json
{
  "mcpServers": {
    "buildrunner": {
      "command": "python",
      "args": ["-m", "cli.mcp_server"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

### 3. Configure Optional Integrations

```bash
# GitHub integration
br config set github.token ghp_your_token_here
br config set github.repo your-org/your-repo

# Notion integration
br config set notion.token secret_your_token_here
br config set notion.database_id your_database_id

# Slack notifications
br config set slack.webhook_url https://hooks.slack.com/services/XXX
```

### 4. Set Global Defaults (Optional)

```bash
# Set default industry for new projects
br config set defaults.industry healthcare

# Set default quality threshold
br config set quality.min_score 75

# Enable auto-generation of STATUS.md
br config set features.auto_generate true
```

---

## Troubleshooting

### Common Issues

#### `br: command not found`

**Cause:** BuildRunner not in PATH

**Solutions:**

**Option 1 - pip install --user:**
```bash
# Add user bin to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$PATH:$HOME/.local/bin"
source ~/.zshrc
```

**Option 2 - Use python -m:**
```bash
python3 -m cli.main --help
# Or create alias:
alias br="python3 -m cli.main"
```

**Option 3 - Reinstall globally:**
```bash
sudo pip install buildrunner
```

---

#### `ModuleNotFoundError: No module named 'typer'`

**Cause:** Dependencies not installed

**Solution:**
```bash
# Reinstall with dependencies
pip install --force-reinstall buildrunner

# OR install dependencies manually
pip install typer click rich pyyaml GitPython
```

---

#### `Permission denied` errors

**Cause:** Insufficient permissions

**Solution:**
```bash
# Install for user only (no sudo)
pip install --user buildrunner

# OR use virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install buildrunner
```

---

#### `SSL: CERTIFICATE_VERIFY_FAILED`

**Cause:** SSL certificate issues (common on corporate networks)

**Solution:**
```bash
# Install with --trusted-host (temporary fix)
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org buildrunner

# OR install root certificates (permanent fix)
# macOS:
/Applications/Python\ 3.11/Install\ Certificates.command

# Linux:
sudo apt-get install ca-certificates
```

---

#### MCP server not connecting

**Cause:** Incorrect path or permissions

**Solution:**
```bash
# Test MCP server manually
python -m cli.mcp_server
# Should wait for stdio input (Ctrl+C to exit)

# Check config path in Claude Code
# Ensure absolute path, not relative
```

---

### Getting Help

**Check logs:**
```bash
# View BuildRunner logs
cat ~/.buildrunner/logs/buildrunner.log

# View recent errors
br debug
```

**Run diagnostics:**
```bash
# System information
python3 --version
pip --version
git --version

# BuildRunner information
br --version
br config list
```

**Report issue:**
- GitHub Issues: https://github.com/buildrunner/buildrunner/issues
- Include: OS, Python version, error message, steps to reproduce

---

## Platform-Specific Notes

### macOS

**Recommended installation:** Homebrew
```bash
brew install buildrunner
```

**Notes:**
- ✅ Works on Intel and Apple Silicon (M1/M2/M3)
- ✅ Integrates with macOS Keychain for credentials
- ⚠️ May need to run `Install Certificates.command` for SSL

**Permissions:**
```bash
# If permission errors on .buildrunner directory
chmod 755 ~/.buildrunner
```

---

### Linux (Ubuntu/Debian)

**Recommended installation:** pip
```bash
sudo apt update
sudo apt install python3-pip git
pip install buildrunner
```

**Notes:**
- ✅ Works on Ubuntu 20.04+, Debian 11+
- ⚠️ May need to install `python3-venv` for virtual environments
- ⚠️ Ensure `~/.local/bin` is in PATH

**PATH configuration:**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

---

### Linux (Fedora/RHEL/CentOS)

```bash
sudo dnf install python3-pip git
pip install buildrunner
```

---

### Windows

**Recommended installation:** pip
```powershell
# In PowerShell
pip install buildrunner
```

**Notes:**
- ✅ Works on Windows 10, 11, Windows Server 2019+
- ⚠️ May need to enable long path support (for deep directory structures)
- ⚠️ Git Bash recommended for better compatibility

**Enable long paths:**
```powershell
# Run PowerShell as Administrator
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1
```

**PATH configuration:**
```powershell
# Add Python Scripts to PATH (if needed)
$env:Path += ";$env:USERPROFILE\AppData\Local\Programs\Python\Python311\Scripts"
```

---

### WSL (Windows Subsystem for Linux)

```bash
# Install in WSL Ubuntu
sudo apt update
sudo apt install python3-pip git
pip install buildrunner
```

**Notes:**
- ✅ Full Linux compatibility
- ✅ Can access Windows files via `/mnt/c/`
- ⚠️ Use WSL paths for projects (better performance)

---

## Upgrading

### pip

```bash
# Upgrade to latest version
pip install --upgrade buildrunner

# Upgrade to specific version
pip install buildrunner==3.0.1

# Check current version
br --version
```

### Homebrew

```bash
# Upgrade to latest version
brew upgrade buildrunner

# Check what will be upgraded
brew outdated | grep buildrunner
```

### Docker

```bash
# Pull latest image
docker pull buildrunner/buildrunner:latest

# Verify new version
docker run buildrunner/buildrunner --version
```

---

## Uninstallation

### pip

```bash
# Uninstall BuildRunner
pip uninstall buildrunner

# Remove configuration files (optional)
rm -rf ~/.buildrunner
```

### Homebrew

```bash
# Uninstall BuildRunner
brew uninstall buildrunner

# Remove configuration files (optional)
rm -rf ~/.buildrunner
```

### Docker

```bash
# Remove image
docker rmi buildrunner/buildrunner:latest

# Remove all BuildRunner images
docker images | grep buildrunner | awk '{print $3}' | xargs docker rmi
```

---

## Next Steps

After installation:

1. **[Quick Start Guide](../QUICKSTART.md)** - Create your first project
2. **[CLI Reference](CLI.md)** - Learn all commands
3. **[PRD Wizard](PRD_WIZARD.md)** - Generate PROJECT_SPEC
4. **[MCP Integration](MCP_INTEGRATION.md)** - Claude Code setup

---

## FAQ

**Q: Can I use BuildRunner without sudo/admin access?**
A: Yes! Use `pip install --user buildrunner` or a virtual environment.

**Q: Does BuildRunner work on Apple Silicon (M1/M2)?**
A: Yes, fully compatible with ARM64 architecture.

**Q: Can I use BuildRunner in CI/CD?**
A: Yes! Docker image recommended for CI. See [CI/CD Guide](#).

**Q: Do I need internet connection to use BuildRunner?**
A: After installation, BuildRunner works fully offline. Optional integrations (GitHub, Notion, etc.) require internet.

**Q: How do I update BuildRunner?**
A: `pip install --upgrade buildrunner` or `brew upgrade buildrunner`

---

**Installation Support:** If you encounter issues, please report them at [GitHub Issues](https://github.com/buildrunner/buildrunner/issues)

---

**BuildRunner Installation** - Get up and running in under 2 minutes 🚀
