# Creating Your First Build with BuildRunner 3.1

**Quick Start: 3 Simple Steps**

---

## Step 1: Initialize Your Project (2 min)

```bash
# Navigate to your project
cd /path/to/your-project

# Initialize BuildRunner
br init my-project

# This creates:
# - .buildrunner/features.json     (feature tracking)
# - .buildrunner/config.yaml       (project settings)
# - PROJECT_SPEC.md                (project specification template)
# - Updates .gitignore
```

---

## Step 2: Define Your Specification (5-10 min)

**Option A: Use the Interactive Wizard (Recommended)**
```bash
br spec wizard
```

This will guide you through:
- Industry selection (choose from 148 profiles)
- Use case pattern
- Technical stack
- Core features
- Generates complete PROJECT_SPEC.md

**Option B: Manually Edit PROJECT_SPEC.md**
```markdown
# Project: My App

## Overview
Brief description of what you're building.

## Features

### Feature 1: User Authentication
**Priority:** Critical
**Description:** JWT-based authentication with email/password

**Requirements:**
- User registration endpoint
- Login endpoint
- Password hashing with bcrypt
- JWT token generation

**Acceptance Criteria:**
- [ ] Users can register with email/password
- [ ] Users can login and receive JWT token
- [ ] Passwords are hashed in database
- [ ] 100% test coverage

### Feature 2: Dashboard
...
```

---

## Step 3: Add Features to Tracking (5 min)

```bash
# Add your features
br feature add "User Authentication" \
  --priority critical \
  --description "JWT-based auth system"

br feature add "Dashboard" \
  --priority high \
  --description "User analytics dashboard"

br feature add "API Integration" \
  --priority medium

# View your features
br feature list

# Check project status
br status
```

---

## What Happens Next?

BuildRunner tracks your features through these states:
- **planned** → **in_progress** → **complete**

### Working with Features

```bash
# Start working on a feature
br feature update user-authentication --status in_progress

# When complete
br feature complete user-authentication

# View progress
br status
br status generate  # Creates STATUS.md
```

---

## AI Assistant Integration (Claude Code)

BuildRunner exposes 9 MCP tools to Claude Code:

```
Tell Claude:
"Use BuildRunner to add feature 'Payment Processing'"
"Use BuildRunner to list all in-progress features"
"Use BuildRunner to mark user-auth as complete"
"Use BuildRunner to generate project status"
```

Available tools:
- `feature_add`, `feature_list`, `feature_get`, `feature_update`, `feature_complete`
- `status_get`, `status_generate`
- `governance_check`, `governance_validate`

---

## Best Practices

### 1. Start Small
Add 3-5 core features first. You can always add more later.

### 2. Use Priorities
- **critical** - Blocking everything else
- **high** - Core functionality
- **medium** - Important but not urgent
- **low** - Nice to have

### 3. Break Down Large Features
Instead of "Build entire backend", create:
- Database schema and models
- Authentication system
- API endpoints for users
- API endpoints for content
- Error handling and validation

### 4. Define Clear Acceptance Criteria
Each feature should have measurable completion criteria:
- ✅ Good: "Users can login and receive JWT token"
- ❌ Bad: "Authentication works"

### 5. Generate Status Reports
```bash
# Auto-generate STATUS.md after each feature completion
br feature complete user-auth
br status generate

# Commit the generated report
git add STATUS.md .buildrunner/features.json
git commit -m "feat: Complete user authentication"
```

---

## Advanced: Using the Design System

BuildRunner includes 148 industry-specific design profiles:

```bash
# Browse industries
br design list
br design list --category Healthcare

# View specific profile
br design profile restaurant
br design profile dentist

# Search for profiles
br design search "dental"
br design search "technology"

# Use in spec wizard
br spec wizard  # Will prompt for industry selection
```

---

## Example: Building a Restaurant Website

```bash
# 1. Initialize
cd ~/projects/italian-restaurant
br init italian-restaurant

# 2. Use wizard with restaurant profile
br spec wizard
# Select: "Restaurant" industry
# Select: "Local Business" use case
# Select: React + Node.js stack

# 3. Add features from generated spec
br feature add "Online Menu" --priority critical
br feature add "Reservation System" --priority critical
br feature add "Gallery" --priority high
br feature add "Contact Form" --priority medium

# 4. Start building
br feature update online-menu --status in_progress

# 5. Track progress
br status
```

---

## Next Steps

1. **Add your features** - Use `br feature add` for each core feature
2. **Update as you work** - Mark features in_progress and complete
3. **Generate status** - Run `br status generate` to track progress
4. **Use with Claude Code** - Let AI manage features via MCP tools
5. **Check quality** - Run `br quality check` before commits

---

## Getting Help

```bash
br --help                    # General help
br feature --help            # Feature commands
br design --help             # Design system
br status --help             # Status commands

# Or check the docs
cat COMMANDS.md              # Complete command reference
cat QUICKSTART.md            # Quick start guide
```

---

**That's it!** You're ready to start building with BuildRunner 3.1.

The system will track your progress, generate status reports, and integrate with AI assistants to help you build faster.
