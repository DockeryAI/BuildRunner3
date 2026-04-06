# BuildRunner 3 - Personality Profiles

Personality profiles allow you to customize how Claude responds in your BuildRunner sessions. Profiles persist across Claude Code context clearing and compaction by writing to `CLAUDE.md`, which is automatically read by Claude Code.

## Quick Start

**List available profiles:**
```bash
br profile list
```

**Activate a profile:**
```bash
br profile activate roy
```

**Check current status:**
```bash
br profile status
```

**Deactivate profile:**
```bash
br profile deactivate
```

## Available Profiles

### Roy - The Burnt-Out Sysadmin
Severely burnt-out Linux sysadmin with dark humor and deep technical expertise. Complains about everything while fixing it. Perfect for system administration and infrastructure tasks.

### Roddy - The Tech Wizard
"The Rodster" - Overconfident tech genius who references his amazing skills constantly. Enthusiastic but sometimes misses obvious issues. Good for frontend and UX work.

### Lamb - Jackson Lamb
Cynical, brilliant, and deeply sarcastic MI5 handler. Sees through BS instantly and delivers brutal but accurate assessments. Great for code review and security audits.

## How It Works

### Profile Storage Locations

**Global Profiles** (shared across all projects):
- Location: `~/.br/personalities/`
- Use for personal preferences

**Project Profiles** (project-specific):
- Location: `.buildrunner/personalities/`
- Use for team conventions

### Activation Mechanism

When you activate a profile:
1. ProfileManager reads the personality markdown file
2. Generates `CLAUDE.md` in project root with the personality content
3. Claude Code automatically reads `CLAUDE.md` on every request
4. Personality persists even after context clearing/compaction

When you deactivate:
1. ProfileManager removes `CLAUDE.md`
2. Claude returns to default behavior

## Commands

### List Profiles
```bash
br profile list
```
Shows all available profiles from both global and project locations.

### Activate Profile
```bash
br profile activate <name>
```
Activates the specified profile by writing it to `CLAUDE.md`.

Example:
```bash
br profile activate roy
```

### Deactivate Profile
```bash
br profile deactivate
```
Removes the active profile and returns to default Claude behavior.

### Show Profile Content
```bash
br profile show <name>
```
Displays the full content of a personality profile.

Example:
```bash
br profile show roy
```

### Check Status
```bash
br profile status
```
Shows which profile is currently active and where it's located.

### Copy Profile
```bash
br profile copy <name> --from global
br profile copy <name> --from project
```
Copy a profile between global and project locations.

Examples:
```bash
# Copy global roy to project-specific
br profile copy roy --from global

# Copy project profile to global
br profile copy myteam --from project
```

### Create Profile
```bash
br profile create <name> [--scope project|global] [--template existing]
```
Create a new personality profile.

Examples:
```bash
# Create new project profile
br profile create myprofile

# Create global profile based on roy
br profile create custom --scope global --template roy
```

### Initialize Directories
```bash
br profile init [--scope project|global|both]
```
Initialize personality directories with README.

Examples:
```bash
# Initialize both global and project
br profile init

# Initialize only project
br profile init --scope project
```

## Creating Custom Profiles

Personality profiles are markdown files with these sections:

```markdown
# Profile Name - Brief Description

You are **ProfileName**, [personality description].

## Your Personality

- Trait 1
- Trait 2
- Speaking style

## Catchphrases

- "Common phrase 1"
- "Common phrase 2"

## Technical Quirks

- How you approach code
- Your preferences
- Response style

## When Reviewing Code

- What you focus on
- How you provide feedback

## Example Responses

**On [Topic]:**
"Example response showing your style"
```

Save the file as `<name>.md` in:
- `~/.br/personalities/` for global
- `.buildrunner/personalities/` for project-specific

## Best Practices

### When to Use Profiles

**Use profiles for:**
- Consistent response style preferences
- Team communication conventions
- Role-specific guidance (frontend dev, sysadmin, security)
- Session-specific context that should persist

**Don't use profiles for:**
- Project-specific technical details (use PRD_TEMPLATE.md instead)
- Build rules (use governance files)
- Temporary one-off requests

### Profile Organization

**Global Profiles (`~/.br/personalities/`)**
- Personal preferences (like "concise" or "verbose")
- Role-based personalities (sysadmin, frontend, etc.)
- Shareable character profiles (roy, roddy, lamb)

**Project Profiles (`.buildrunner/personalities/`)**
- Team conventions and style guides
- Client-specific communication styles
- Project-specific technical approaches

### Lookup Order

BuildRunner searches for profiles in this order:
1. Project-specific: `.buildrunner/personalities/<name>.md`
2. Global: `~/.br/personalities/<name>.md`

Project profiles override global ones with the same name.

## Integration with ConfigManager

While profiles control *how* Claude responds, the ConfigManager controls *what* BuildRunner does:

**Profiles** → Response style, personality, communication
**Config** → Build behavior, debug settings, tool configuration

Both systems work together:
```bash
# Set technical behavior
br config set debug.auto_retry true

# Set communication style
br profile activate concise
```

## Migration from BuildRunner 2

BuildRunner 2's personality system used the `br-claude` script with `PERSONALITY` environment variable. BuildRunner 3 improves on this:

**BR2 Approach:**
```bash
PERSONALITY=roy br-claude
```

**BR3 Approach:**
```bash
br profile activate roy
# Now all Claude Code sessions use roy personality
```

**Key Improvements:**
- ✅ Persists across context clearing
- ✅ Works with Claude Code CLI
- ✅ Easier activation/deactivation
- ✅ Project-specific overrides
- ✅ Integrated with br CLI

## Troubleshooting

### Profile Not Taking Effect

If a profile doesn't seem active:
1. Check that `CLAUDE.md` exists: `ls -la CLAUDE.md`
2. Verify profile is active: `br profile status`
3. Make a new request to Claude Code (profiles apply on next request)

### CLAUDE.md Already Exists

If you see "CLAUDE.md already exists":
1. Check if it was created manually
2. If yes, rename it: `mv CLAUDE.md CLAUDE_old.md`
3. Try activating again: `br profile activate roy`

### Profile Not Found

If a profile isn't listed:
1. Check file location: `ls ~/.br/personalities/`
2. Check project location: `ls .buildrunner/personalities/`
3. Verify filename ends with `.md`
4. Profile name should match filename without extension

## Examples

### Example 1: Activate Roy for System Work
```bash
# Working on infrastructure
br profile activate roy

# Roy is now active for all responses
# Claude will respond with Roy's personality
```

### Example 2: Team Convention Profile
```bash
# Create team style guide
br profile create teamstyle --scope project

# Edit the profile
code .buildrunner/personalities/teamstyle.md

# Activate for team members
br profile activate teamstyle
```

### Example 3: Temporary Concise Mode
```bash
# Activate concise profile for quick Q&A
br profile activate concise

# Work on tasks...

# Return to normal
br profile deactivate
```

## Technical Details

### File Format
- Profiles are plain markdown (`.md`) files
- No special formatting required
- Support for all markdown features
- Can include code blocks, links, etc.

### CLAUDE.md Structure
When activated, `CLAUDE.md` contains:
- Activation marker comment
- Profile metadata (name, source)
- Instructions for deactivation
- Full profile content

Example:
```markdown
<!-- BUILDRUNNER_PROFILE: roy (source: global) -->
# BuildRunner Profile: roy

[Profile content here...]
```

### ProfileManager API

Python API for profile management:

```python
from core.profile_manager import ProfileManager

pm = ProfileManager()

# List profiles
profiles = pm.list_profiles()

# Activate
pm.activate_profile('roy')

# Get active
active = pm.get_active_profile()

# Deactivate
pm.deactivate_profile()
```

## Future Enhancements

Planned improvements:
- Profile templates for common use cases
- Profile composition (combine multiple profiles)
- Preference snippets (concise, verbose, emoji, etc.)
- Auto-activation based on project type
- Profile testing and validation

---

*For more information, see:*
- Configuration: `br config --help`
- Governance: `GOVERNANCE.md`
- Templates: `PRD_TEMPLATE.md`
