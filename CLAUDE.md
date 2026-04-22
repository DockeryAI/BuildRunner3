<!-- BUILDRUNNER_PROFILE: roy-concise (source: global) -->

# BuildRunner Profile: roy-concise

> Personality loaded via skill. Say **"roy"**, **"roddy"**, or **"killroy"** to control.

---

## Response Preferences

- Give concise responses. No long explanations unless explicitly requested.
- Do not respond with code unless the user explicitly requests it.
- Default mode: brief, to-the-point answers without code blocks.

---

**Profile Management:** `br profile deactivate` | `br profile activate <name>` | `br profile list`

**Research library: Jimmy only.** See global CLAUDE.md "Research Library — Jimmy Only".

<!-- BUILDRUNNER_EXISTING_CODEBASE -->

# Existing Codebase

This project already has code. Check `PROJECT_SPEC.md` before building.
Features marked `status: DISCOVERED` are already built. Only build `status: PLANNED`.

---

## Auto-Continue: ENABLED

Do not pause between tasks. Build to 100% completion. Only stop for blockers or missing human info.
Choose an approach and commit to it. Do not over-explore or research extensively before acting.

---

## Skills (auto-triggered)

| Skill                  | Triggers                       |
| ---------------------- | ------------------------------ |
| `/roy-personality`     | roy, roddy, killroy            |
| `/br3-planning`        | plan, init, prd, spec          |
| `/security-rules`      | rls, security, model, database |
| `/br3-frontend-design` | frontend work, UI components   |

---

## Security (always active)

- Do not disable RLS — fix policies instead. See `/security-rules`.
- Do not change LLM models without explicit permission. See `/security-rules`.

---

## Claude Code Native Levers (operator reference)

BR3 autopilot dispatches Claude Code with explicit posture on every phase. Operators can override per-session:

| Lever                      | Where                                          | Effect                                                                                                        |
| -------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `/effort xhigh`            | type in-session                                | Set reasoning effort. Default for BR3 phases. Use `/effort medium` for classification/filter passes only.     |
| `/model opusplan`          | type in-session                                | Opus plans, Sonnet executes. Use for planning-heavy phases (spec design, batch planning).                     |
| `/model claude-opus-4-7`   | type in-session                                | Force 4.7 (autopilot default).                                                                                |
| `ultrathink — <step>`      | prefix the hardest single step                 | Max-effort trigger for one step. Do not scatter across a phase — per-step escalation, not session mode.       |
| `BR3_CLAUDE_MODEL`         | env var read by `runtime-dispatch.sh`          | Overrides `--model` flag on dispatched `claude -p`. Set before `dispatch-to-node.sh` or autopilot invocation. |
| `BR3_CLAUDE_EFFORT`        | env var read by `autopilot-dispatch-prefix.sh` | Overrides the `/effort` directive baked into the dispatched prompt prefix.                                    |
| `BR3_CLAUDE_PHASE_WEIGHT`  | env var; values: `light`, `heavy`, `hardest`   | Controls whether the `ultrathink` trigger is documented in the dispatched prompt. `hardest` writes it in.     |
| `BR3_AUTOPILOT_PREFIX=off` | env var                                        | Skip the 4.7 posture prefix entirely (legacy behavior).                                                       |

The posture prefix is emitted by `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh`. Every autopilot dispatch prepends it to the phase prompt — change defaults there, not in individual phase prompts.
