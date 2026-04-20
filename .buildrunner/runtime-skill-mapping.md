# Runtime Skill Mapping

Generated for Phase 9 command compiler support.

## Purpose

- Translate selected high-value Claude skill/context packages into Codex-readable skill bundles.
- Keep Claude-first command boundaries explicit while still giving Codex portable domain context for approved workflows.
- Avoid hidden capability drift: BR3 chooses which Codex skills are installed and which commands may consume them.

## Skill Mapping

| `Claude Skill` | `Claude Path` | `Codex Skill` | `Codex Path` | `Status` |
| --- | --- | --- | --- | --- |
| `br3-planning` | `/Users/byronhudson/.claude/skills/br3-planning/SKILL.md` | `br3-planning` | `/Users/byronhudson/.codex/skills/br3-planning/SKILL.md` | `installed` |
| `br3-frontend-design` | `/Users/byronhudson/.claude/skills/br3-frontend-design/SKILL.md` | `br3-frontend-design` | `/Users/byronhudson/.codex/skills/br3-frontend-design/SKILL.md` | `installed` |
| `chet` | `/Users/byronhudson/.claude/skills/chet/SKILL.md` | `chet` | `/Users/byronhudson/.codex/skills/chet/SKILL.md` | `installed` |
| `prodlog` | `/Users/byronhudson/.claude/skills/prodlog/SKILL.md` | `prodlog` | `/Users/byronhudson/.codex/skills/prodlog/SKILL.md` | `installed` |
| `business` | `/Users/byronhudson/.claude/skills/business.md` | `business` | `/Users/byronhudson/.codex/skills/business/SKILL.md` | `installed` |
| `geo` | `/Users/byronhudson/.claude/skills/geo.md` | `geo` | `/Users/byronhudson/.codex/skills/geo/SKILL.md` | `installed` |
| `sales` | `/Users/byronhudson/.claude/skills/sales.md` | `sales` | `/Users/byronhudson/.codex/skills/sales/SKILL.md` | `installed` |
| `security-rules` | `/Users/byronhudson/.claude/skills/security-rules/SKILL.md` | `security-rules` | `/Users/byronhudson/.codex/skills/security-rules/SKILL.md` | `installed` |

## Command Policy Notes

- `/spec` is still Claude-first in the audited inventory, but Phase 10 permits Codex drafting only through the BR3-owned `spec_workflow`.
- `/review` remains advisory-only for Codex shadow mode and is not promoted here.
- `/begin` remains Claude-only until Phase 11.
- The compiler reads `.buildrunner/runtime-command-inventory.json` plus `core/runtime/command_capabilities.json`; if they disagree, the capability map wins for explicitly-curated workflow exceptions only.
