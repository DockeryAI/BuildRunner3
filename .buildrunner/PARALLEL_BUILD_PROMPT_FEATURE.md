# Parallel Build Prompt Feature

**Date:** 2025-11-18
**Status:** Feature request for Build 4E Phase 7

## User Request

When generating a build plan, the system should ask the user whether they want to use parallel builds.

## Prompt Design

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build Plan Generated: Build 4E (v3.1.0-alpha.9)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sequential Timeline: 9 days
Parallel Timeline:   6 days (33% faster)

⚡ Parallel builds are available for this project!

Parallelization will split work across 3 independent streams:
  • Stream A: Model Routing (2 days)
  • Stream B: Telemetry (3 days)
  • Stream C: Orchestration (3 days)

⚠️  Note: Parallel builds require manual coordination:
  • You'll need to manage 4 Claude instances (1 orchestrator + 3 workers)
  • Type "continue", "check", and "merge" commands as prompted
  • More context switching but faster completion

Enable parallel builds for this build? [yes/no/always/never]
  yes     - Enable for this build only
  no      - Sequential build (9 days)
  always  - Enable for all future builds
  never   - Sequential for all future builds
```

## Implementation Details

### Configuration Storage

Store user preference in `.buildrunner/config.yaml`:

```yaml
build:
  parallel_builds:
    enabled: true|false|prompt  # Default: prompt
    preference: null|always|never
```

### Logic Flow

1. **Generate Build Plan:**
   - System analyzes feature complexity
   - Identifies parallelizable components
   - Calculates sequential vs parallel timelines

2. **Check Preference:**
   ```python
   if config.parallel_builds.preference == 'always':
       use_parallel = True
   elif config.parallel_builds.preference == 'never':
       use_parallel = False
   else:  # prompt
       use_parallel = prompt_user_for_parallel()
   ```

3. **Prompt User (if needed):**
   - Show comparison (sequential vs parallel)
   - List streams and their duration
   - Explain manual requirements
   - Get user choice

4. **Handle Response:**
   - `yes` - Enable parallel, save preference=None (prompt next time)
   - `no` - Disable parallel, save preference=None
   - `always` - Enable parallel, save preference='always'
   - `never` - Disable parallel, save preference='never'

5. **Execute Build:**
   - If parallel: Run `br orchestrate --parallel`
   - If sequential: Run `br run --sequential`

### CLI Commands

```bash
# Check current preference
br config get build.parallel_builds

# Set preference manually
br config set build.parallel_builds.preference always
br config set build.parallel_builds.preference never
br config set build.parallel_builds.preference prompt  # Default

# Override for single build
br run --parallel      # Force parallel
br run --sequential    # Force sequential
```

### Implementation Location

Add to:
1. **`core/orchestration/session_manager.py`** - Check preference before starting
2. **`cli/orchestration_commands.py`** - Prompt user if needed
3. **`core/config.py`** - Add parallel_builds config section

## Benefits

- **User Control:** Explicit choice with clear tradeoffs
- **Flexibility:** Can change preference anytime
- **Convenience:** "always" or "never" options reduce repetitive prompts
- **Transparency:** Shows time savings upfront

## Example Session

```
$ br run --auto

Generating build plan...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Build Plan: Build 4E
Sequential: 9 days | Parallel: 6 days (33% faster)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enable parallel builds? [yes/no/always/never]: yes

✓ Parallel builds enabled for this build

Starting orchestrator...
Dashboard: http://localhost:8080

Please open 3 additional Claude instances:
  Instance 1: br worker --stream model-routing
  Instance 2: br worker --stream telemetry
  Instance 3: br worker --stream orchestration
```

## Future Enhancements

- **Auto-detect capability:** Check if user has multiple terminals available
- **Progress estimation:** Update ETA based on actual progress
- **Learning:** Track whether user prefers parallel, adjust default
- **Team coordination:** Multi-user parallel builds (future)

---

**Status:** Ready for implementation in Build 4E Phase 7
