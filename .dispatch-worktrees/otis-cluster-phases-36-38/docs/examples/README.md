# BuildRunner 3.0 Examples

This directory contains example configurations for BuildRunner 3.0.

---

## Feature Registry Examples

### features.json

Example features.json file showing:
- Multiple features with different statuses (complete, in_progress, planned)
- Priority levels (critical, high, medium)
- Week and build assignments
- Auto-calculated metrics

#### Usage

Copy `features.json` to your project's `.buildrunner/` directory and modify as needed:

```bash
cp docs/examples/features.json .buildrunner/features.json
```

Then use the FeatureRegistry API to manage features:

```python
from core.feature_registry import FeatureRegistry

# Initialize registry
registry = FeatureRegistry()

# Add a feature
registry.add_feature(
    feature_id="new-feature",
    name="New Feature",
    description="Feature description",
    priority="high",
    week=1,
    build="1A"
)

# Mark feature complete
registry.complete_feature("new-feature")

# Generate STATUS.md
from core.status_generator import StatusGenerator
generator = StatusGenerator()
generator.save()
```

#### Auto-Generated STATUS.md

Run the status generator to create a markdown status report:

```python
from core.status_generator import StatusGenerator

generator = StatusGenerator()
generator.save()  # Creates .buildrunner/STATUS.md
```

This generates a formatted report with:
- Project overview and metrics
- Features grouped by status
- Progress tracking
- Timestamps

---

## Governance Configuration Examples

This directory contains example governance configurations for different project types and requirements.

### Available Examples

#### 1. `governance-minimal.yaml`

**Use Case:** Small projects, prototypes, personal projects

**Characteristics:**
- Simple 3-state workflow (planned → in_progress → complete)
- Minimal validation (tests only)
- Warn-only enforcement (no blocking)
- Hooks disabled
- No checksum verification

**When to use:**
- Learning BuildRunner 3.0
- Quick prototypes
- Personal side projects
- When you want flexibility over strictness

#### 2. `governance-strict.yaml`

**Use Case:** Production systems, regulated industries, critical infrastructure

**Characteristics:**
- Complex 7-state workflow with code review and QA approval
- Comprehensive validation (tests, coverage 95%+, lint, security scans)
- Strict enforcement (blocks on all violations)
- All hooks enabled
- Signed commits required
- Two-reviewer approval for merges
- Security-focused

**When to use:**
- Production systems
- Financial/healthcare applications
- Open source projects with multiple contributors
- Any system where quality cannot be compromised

#### 3. `governance-team.yaml`

**Use Case:** Team projects with AI assistance

**Characteristics:**
- Balanced 6-state workflow
- Feature dependency tracking
- 85% coverage threshold (realistic for teams)
- Strict enforcement but coverage is warn-only
- AI-friendly context management
- Slash commands enabled
- Team velocity metrics

**When to use:**
- Team collaboration projects
- AI-assisted development
- BuildRunner 3.0 meta-development (like this project!)
- Projects with coordinated feature dependencies

### Customization Guide

#### Quick Start

1. **Copy example to your project:**
   ```bash
   cp docs/examples/governance-team.yaml .buildrunner/governance/governance.yaml
   ```

2. **Customize project metadata:**
   ```yaml
   project:
     name: "YourProject"
     version: "1.0.0"
     description: "Your project description"
   ```

3. **Define feature dependencies:**
   ```yaml
   dependencies:
     feature-a: []
     feature-b: ["feature-a"]
     feature-c: ["feature-a", "feature-b"]
   ```

4. **Generate checksum:**
   ```bash
   br governance checksum
   ```

#### Common Customizations

**Adjust Coverage Threshold:**
```yaml
validation:
  coverage_threshold: 80  # Lower for legacy codebases
```

**Change Enforcement Policy:**
```yaml
enforcement:
  policy: "warn"  # Options: strict, warn, off
```

**Customize Branch Patterns:**
```yaml
workflow:
  rules:
    branch_patterns:
      feature: "feat/{feature_name}"
      bugfix: "bug/{issue_number}"
      experimental: "exp/{description}"
```

**Add Custom States:**
```yaml
workflow:
  rules:
    allowed_states:
      - planned
      - in_progress
      - peer_review
      - security_review
      - complete

    transitions:
      peer_review:
        - security_review
        - in_progress
```

### Migration Path

Start lenient, tighten over time:

1. **Start:** `governance-minimal.yaml` (Week 1)
2. **Evolve:** `governance-team.yaml` (Week 2-4)
3. **Mature:** `governance-strict.yaml` (Production)

### Validation

Test your custom governance file:

```bash
# Validate syntax
br governance validate

# Test checksum
br governance checksum
br governance verify

# Dry-run enforcement
br governance check --dry-run
```

### Best Practices

1. **Version Control:** Always commit governance.yaml changes
2. **Team Agreement:** Get team buy-in before strict enforcement
3. **Gradual Adoption:** Start with warnings, then block
4. **Document Exceptions:** If you bypass rules, document why
5. **Review Regularly:** Governance should evolve with your project

### Troubleshooting

**"Governance violation: checksum mismatch"**

Someone modified governance.yaml. If intentional:
```bash
br governance reset
```

**"Invalid transition from X to Y"**

Check your workflow.rules.transitions. You may need to add the transition:
```yaml
transitions:
  X:
    - Y  # Allow X → Y
```

**"Unmet dependencies for feature-X"**

Complete prerequisite features first, or update dependencies:
```yaml
dependencies:
  feature-X: []  # Remove dependencies
```

---

## Need Help?

- See main docs: `README.md`
- Governance API: `docs/GOVERNANCE_API.md`
- Enforcement guide: `docs/ENFORCEMENT.md`
- Ask AI: `/br-wtf governance`

---

Remember: Governance is a tool, not a prison. Adjust to fit your team's needs.
