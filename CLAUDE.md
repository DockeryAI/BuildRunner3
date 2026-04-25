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

| Skill                  | Triggers                                    |
| ---------------------- | ------------------------------------------- |
| `/roy-personality`     | roy, roddy, killroy                         |
| `/br3-planning`        | plan, init, prd, spec                       |
| `/security-rules`      | rls, security, model, database              |
| `/br3-frontend-design` | frontend work, UI components                |
| `/ship`                | ship, push, deploy, gate, publish, pre-push |

---

## Security (always active)

- Do not disable RLS — fix policies instead. See `/security-rules`.
- Do not change LLM models without explicit permission. See `/security-rules`.

---

## Operator overrides (reference)

Per-session knobs: `/effort xhigh|medium`, `/model opusplan|claude-opus-4-7`, `ultrathink —` prefix on a single hardest step.

Env vars (autopilot dispatch): `BR3_CLAUDE_MODEL`, `BR3_CLAUDE_EFFORT`, `BR3_CLAUDE_PHASE_WEIGHT` (`light|heavy|hardest`), `BR3_AUTOPILOT_PREFIX=off`. Posture prefix lives in `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` — edit there, not in phase prompts.
