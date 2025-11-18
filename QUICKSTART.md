# BuildRunner 3.0 - Quick Start Guide

**Get from zero to first project in 5 minutes**

---

## Step 1: Installation (1 minute)

### Option A: pip (Recommended)
```bash
pip install buildrunner
```

### Option B: Homebrew (macOS)
```bash
brew install buildrunner
```

### Option C: Docker
```bash
docker pull buildrunner/buildrunner:latest
alias br="docker run -it -v $(pwd):/project buildrunner/buildrunner"
```

**Verify installation:**
```bash
br --version
# Output: BuildRunner 3.0.0
```

---

## Step 2: Initialize Your First Project (1 minute)

```bash
# Create a new project
br init my-healthcare-app
cd my-healthcare-app

# Your project now has:
# .buildrunner/
#   ├── features.json        # Feature tracking
#   ├── governance/          # Governance rules
#   └── standards/           # Coding standards
```

---

## Step 3: Create Your PROJECT_SPEC (2 minutes)

Run the interactive PRD Wizard:

```bash
br spec wizard
```

The wizard will guide you through:

**1. Describe your app:**
```
What do you want to build?
> A healthcare patient dashboard for doctors to view patient vitals,
> medication lists, and appointment schedules.
```

**2. Confirm industry & use case:**
```
Detected Industry: healthcare
Detected Use Case: dashboard
Is this correct? (y/n): y
```

**3. Review Opus pre-filled sections:**
- Product Requirements ✓
- Technical Architecture ✓
- Design Architecture ✓

**4. Review design profile:**
```
Design Profile: Healthcare + Dashboard
- Colors: Trust blue (#0066CC), Medical green (#00A86B)
- Components: PatientCard, VitalsWidget, MedicationList
- Compliance: HIPAA, WCAG 2.1 AA, ADA
Accept? (y/n): y
```

**5. Confirm tech stack:**
```
Suggested: React + TypeScript, FastAPI, PostgreSQL
Accept? (y/n): y
```

**Result:** Complete PROJECT_SPEC.md created in `.buildrunner/`

---

## Step 4: Generate Features (30 seconds)

Sync your spec to features.json:

```bash
br spec sync
```

Output:
```
✅ Synced PROJECT_SPEC → features.json
   Features: 8
   Phases: 3
   💡 5 features can be built in parallel
```

---

## Step 5: View Project Status (30 seconds)

```bash
br status
```

Output:
```
📊 Project Status
─────────────────────────
  my-healthcare-app - v1.0.0

Metrics:
  Features Complete:     0
  Features In Progress:  0
  Features Planned:      8
  Completion:            0%

Features:
  📋 Patient Vitals View
  📋 Medication Management
  📋 Appointment Scheduling
  📋 Doctor Dashboard
  ... 4 more
```

---

## Step 6: Start Building (Optional)

### Generate STATUS.md
```bash
br generate
```

Creates a markdown status file for your project.

### Add MCP Integration (Claude Code)

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "buildrunner": {
      "command": "python",
      "args": ["-m", "cli.mcp_server"],
      "cwd": "/path/to/my-healthcare-app"
    }
  }
}
```

Now you can manage features directly from Claude Code!

### Configure Optional Integrations

```bash
# GitHub integration
br config set github.token ghp_your_token_here
br config set github.repo your-org/my-healthcare-app

# Notion integration
br config set notion.token secret_your_token_here
br config set notion.database_id your_database_id

# Slack notifications
br config set slack.webhook_url https://hooks.slack.com/xxx
```

---

## Next Steps

### 🎓 Learn More
- [First Project Tutorial](docs/tutorials/FIRST_PROJECT.md) - Complete walkthrough
- [Design System Guide](docs/tutorials/DESIGN_SYSTEM_GUIDE.md) - Industry profiles
- [Quality Gates Setup](docs/tutorials/QUALITY_GATES.md) - Code standards

### 📖 Documentation
- [CLI Reference](docs/CLI.md) - All commands
- [PRD Wizard Guide](docs/PRD_WIZARD.md) - Detailed wizard docs
- [MCP Integration](docs/MCP_INTEGRATION.md) - Claude Code setup

### 💡 Examples
- [Healthcare Dashboard](examples/healthcare-dashboard/) - Full example
- [Fintech API](examples/fintech-api/) - API service
- [E-commerce Marketplace](examples/ecommerce-marketplace/) - Multi-service

### ⚙️ Advanced Features
- **Migration from BR 2.0**: `br migrate from-v2 /path/to/old-project`
- **Multi-repo Dashboard**: `br dashboard show`
- **Quality Checks**: `br quality check`
- **Gap Analysis**: `br gaps analyze`

---

## Common Commands

```bash
# Feature management
br feature add "User Authentication"
br feature complete auth-001
br feature list --status planned

# PRD Wizard
br spec wizard              # Create/edit PROJECT_SPEC
br spec sync                # Sync to features.json
br spec validate            # Check completeness

# Design system
br design profile healthcare dashboard
br design research

# Status and metrics
br status                   # Show project status
br generate                 # Generate STATUS.md

# Dashboard
br dashboard show           # View all projects
br dashboard show --watch   # Live dashboard
```

---

## Troubleshooting

**Q: Wizard doesn't detect my industry**
```bash
# Be more specific in your app description
# Or manually override:
br spec wizard --industry fintech --use-case dashboard
```

**Q: How do I edit my PROJECT_SPEC after creation?**
```bash
# Re-run wizard to edit specific sections
br spec wizard

# Or edit .buildrunner/PROJECT_SPEC.md directly, then:
br spec sync
```

**Q: Can I use BuildRunner without Supabase/GitHub/etc?**
```bash
# Yes! All integrations are optional.
# BuildRunner works fully offline with just Git.
```

---

## Support

- **Documentation**: [https://buildrunner.dev/docs](https://buildrunner.dev/docs)
- **Issues**: [GitHub Issues](https://github.com/buildrunner/buildrunner/issues)
- **Discord**: [Join our community](https://discord.gg/buildrunner)

---

**You're ready to build!** 🚀

BuildRunner will help ensure your project is complete, high-quality, and aligned with your spec. Start adding features and let the AI build with confidence.
