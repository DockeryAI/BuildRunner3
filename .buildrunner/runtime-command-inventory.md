# Runtime Command Inventory

Generated: 2026-04-15

## Summary

- Total commands cataloged: 65
- Total skills discovered: 12
- Migration buckets: {"hard": 9, "keep-Claude-first": 35, "moderate": 11, "trivial": 10}
- Portability ratings: {"claude_first": 35, "high": 10, "low": 9, "medium": 11}

## Decision Gate

- Result: `formalize_long_term_hybrid_strategy`
- Basis: 14 of 16 core commands (88%) are low-portability or Claude-first.
- Recommendation: retain a long-term hybrid split with Claude default for research, planning, architecture, and browser-heavy flows while migrating execution-centric commands first.

## Rollout Order

### Stage 1 — `trivial`

- Focus: simple local execution commands with minimal orchestration coupling
- Commands: `/3`, `/business`, `/concise`, `/fixplan`, `/mobile`, `/restart`, `/sales`, `/supa`, `/switch`, `/test`

### Stage 2 — `moderate`

- Focus: commands with manageable cluster or interaction coupling after runtime selection exists
- Commands: `/cluster`, `/commit`, `/impact`, `/intel-review`, `/predict`, `/production`, `/pw-test`, `/reset-cluster`, `/rules`, `/swap`, `/tuning`

### Stage 3 — `hard`

- Focus: commands needing explicit adapter or policy extraction work
- Commands: `/brief`, `/dbg`, `/device`, `/preview`, `/query`, `/sdb`, `/setlist`, `/website-build`, `/why`

### Stage 4 — `keep-Claude-first`

- Focus: research, planning, architecture, and browser-heavy commands retained on Claude
- Commands: `/amend`, `/appdesign`, `/autopilot`, `/begin`, `/brainstorm`, `/cluster-research`, `/dash`, `/dead`, `/design`, `/diag`, `/e2e`, `/explore-qa`, `/gaps`, `/geo-coach`, `/geo`, `/guard`, `/hunt`, `/later`, `/learn`, `/llm`, `/monitor`, `/opus`, `/perplexity`, `/prompt`, `/recraft`, `/research-audit`, `/research`, `/review`, `/roadmap`, `/root`, `/save`, `/social`, `/spec`, `/steal`, `/worktree`

## Skill Inputs

| Skill | Path |
| ---- | ---- |
| `2nd` | `/Users/byronhudson/.claude/skills/2nd/SKILL.md` |
| `br3-frontend-design` | `/Users/byronhudson/.claude/skills/br3-frontend-design/SKILL.md` |
| `br3-planning` | `/Users/byronhudson/.claude/skills/br3-planning/SKILL.md` |
| `business` | `/Users/byronhudson/.claude/skills/business.md` |
| `chet` | `/Users/byronhudson/.claude/skills/chet/SKILL.md` |
| `codex-do` | `/Users/byronhudson/.claude/skills/codex-do/SKILL.md` |
| `geo` | `/Users/byronhudson/.claude/skills/geo.md` |
| `prodlog` | `/Users/byronhudson/.claude/skills/prodlog/SKILL.md` |
| `roy-personality` | `/Users/byronhudson/.claude/skills/roy-personality/SKILL.md` |
| `sales` | `/Users/byronhudson/.claude/skills/sales.md` |
| `security-rules` | `/Users/byronhudson/.claude/skills/security-rules/SKILL.md` |
| `template` | `/Users/byronhudson/.claude/skills/template/SKILL.md` |

## Command Catalog

| Command | Category | Portability | Bucket | Fallback | Effort | Status | Signals |
| ------- | -------- | ----------- | ------ | -------- | ------ | ------ | ------- |
| `/3` | execution | high | trivial | codex | S | active | local |
| `/amend` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents |
| `/appdesign` | design | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/autopilot` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, hooks, browser |
| `/begin` | execution | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, hooks, browser |
| `/brainstorm` | planning | claude_first | keep-Claude-first | claude | XL | active | local |
| `/brief` | execution | low | hard | hybrid | L | low_value | hooks |
| `/business` | business_domain | high | trivial | codex | S | active | local |
| `/cluster-research` | execution | claude_first | keep-Claude-first | claude | XL | active | hooks, browser |
| `/cluster` | cluster_ops | medium | moderate | hybrid | M | active | cluster |
| `/commit` | execution | medium | moderate | hybrid | M | active | cluster |
| `/concise` | execution | high | trivial | codex | S | low_value | local |
| `/dash` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/dbg` | execution | low | hard | hybrid | L | active | browser |
| `/dead` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, browser |
| `/design` | execution | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, browser |
| `/device` | execution | low | hard | hybrid | L | active | browser |
| `/diag` | execution | claude_first | keep-Claude-first | claude | XL | active | subagents, browser |
| `/e2e` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, browser |
| `/explore-qa` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/fixplan` | execution | high | trivial | codex | S | active | local |
| `/gaps` | execution | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/geo-coach` | business_domain | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/geo` | business_domain | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/guard` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/hunt` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/impact` | cluster_ops | medium | moderate | hybrid | M | active | cluster |
| `/intel-review` | cluster_ops | medium | moderate | hybrid | M | active | cluster |
| `/later` | design | claude_first | keep-Claude-first | claude | XL | low_value | local |
| `/learn` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster |
| `/llm` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster |
| `/mobile` | misc | high | trivial | codex | S | active | local |
| `/monitor` | execution | claude_first | keep-Claude-first | claude | XL | active | browser |
| `/opus` | execution | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, hooks |
| `/perplexity` | execution | claude_first | keep-Claude-first | claude | XL | active | cluster, browser |
| `/predict` | cluster_ops | medium | moderate | hybrid | M | active | cluster |
| `/preview` | execution | low | hard | hybrid | L | active | cluster, browser |
| `/production` | execution | medium | moderate | hybrid | M | active | local |
| `/prompt` | planning | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, browser |
| `/pw-test` | execution | medium | moderate | hybrid | M | active | browser |
| `/query` | execution | low | hard | hybrid | L | active | browser |
| `/recraft` | design | claude_first | keep-Claude-first | claude | XL | active | cluster, hooks, browser |
| `/research-audit` | research | claude_first | keep-Claude-first | claude | XL | active | local |
| `/research` | research | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, browser |
| `/reset-cluster` | cluster_ops | medium | moderate | hybrid | M | active | cluster |
| `/restart` | execution | high | trivial | codex | S | low_value | local |
| `/review` | execution | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, browser |
| `/roadmap` | execution | claude_first | keep-Claude-first | claude | XL | active | local |
| `/root` | cluster_ops | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, browser |
| `/rules` | execution | medium | moderate | hybrid | M | low_value | local |
| `/sales` | business_domain | high | trivial | codex | S | active | local |
| `/save` | cluster_ops | claude_first | keep-Claude-first | claude | XL | low_value | cluster, browser |
| `/sdb` | execution | low | hard | hybrid | L | active | browser |
| `/setlist` | business_domain | low | hard | hybrid | L | active | cluster, subagents |
| `/social` | business_domain | claude_first | keep-Claude-first | claude | XL | active | cluster, hooks |
| `/spec` | execution | claude_first | keep-Claude-first | claude | XL | active | cluster, subagents, hooks |
| `/steal` | execution | claude_first | keep-Claude-first | claude | XL | active | subagents, hooks, browser |
| `/supa` | misc | high | trivial | codex | S | active | local |
| `/swap` | cluster_ops | medium | moderate | hybrid | M | active | cluster |
| `/switch` | session_helper | high | trivial | codex | S | active | local |
| `/test` | execution | high | trivial | codex | S | active | local |
| `/tuning` | misc | medium | moderate | hybrid | M | active | subagents |
| `/website-build` | execution | low | hard | hybrid | L | active | browser |
| `/why` | execution | low | hard | hybrid | L | low_value | cluster |
| `/worktree` | execution | claude_first | keep-Claude-first | claude | XL | active | local |

## Notes

- `/amend`: planning/research/design command remains Claude-first by policy
- `/appdesign`: planning/research/design command remains Claude-first by policy
- `/autopilot`: planning/research/design command remains Claude-first by policy
- `/begin`: planning/research/design command remains Claude-first by policy
- `/brainstorm`: planning/research/design command remains Claude-first by policy
- `/brief`: session helper; auto-runs via hook and is not a migration priority
- `/cluster-research`: browser/web research dependence; hook/governance coupling; skill-specific behavior
- `/concise`: formatting helper, not a substantive runtime workflow
- `/dash`: browser/web research dependence; cluster integration; skill-specific behavior
- `/dead`: browser/web research dependence; cluster integration; subagent orchestration; skill-specific behavior
- `/design`: planning/research/design command remains Claude-first by policy
- `/diag`: browser/web research dependence; subagent orchestration; skill-specific behavior
- `/e2e`: browser/web research dependence; cluster integration; subagent orchestration
- `/explore-qa`: browser/web research dependence; cluster integration
- `/gaps`: planning/research/design command remains Claude-first by policy
- `/geo-coach`: browser/web research dependence; cluster integration; skill-specific behavior
- `/geo`: browser/web research dependence; cluster integration; skill-specific behavior
- `/guard`: planning/research/design command remains Claude-first by policy
- `/hunt`: browser/web research dependence; cluster integration; skill-specific behavior
- `/later`: response-style helper, low migration value
- `/learn`: planning/research/design command remains Claude-first by policy
- `/llm`: planning/research/design command remains Claude-first by policy
- `/monitor`: browser/web research dependence; user gating / interactive stop points
- `/opus`: planning/research/design command remains Claude-first by policy
- `/perplexity`: browser/web research dependence; cluster integration; skill-specific behavior
- `/prompt`: planning/research/design command remains Claude-first by policy
- `/recraft`: planning/research/design command remains Claude-first by policy
- `/research-audit`: planning/research/design command remains Claude-first by policy
- `/research`: planning/research/design command remains Claude-first by policy
- `/restart`: redundant with /3 and narrower in scope
- `/review`: browser/web research dependence; cluster integration; subagent orchestration; skill-specific behavior
- `/roadmap`: planning/research/design command remains Claude-first by policy
- `/root`: browser/web research dependence; cluster integration; subagent orchestration; skill-specific behavior
- `/rules`: policy display helper, not a core runtime workflow
- `/save`: session helper; low migration priority
- `/social`: cluster integration; hook/governance coupling; skill-specific behavior
- `/spec`: planning/research/design command remains Claude-first by policy
- `/steal`: browser/web research dependence; subagent orchestration; hook/governance coupling; skill-specific behavior
- `/why`: explanation helper, not a substantive runtime workflow
- `/worktree`: planning/research/design command remains Claude-first by policy
