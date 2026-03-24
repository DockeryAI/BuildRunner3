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
