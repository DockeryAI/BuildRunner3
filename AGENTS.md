# AGENTS.md — BR3 Root Router

## Build & Test (file-scoped — never full suite)

- Python: `pytest tests/<area>/test_<file>.py -x && ruff check <path>/<file>.py`
- JS (dashboard): `npx eslint --fix ui/dashboard/panels/<file>.js`
- Shell: `shellcheck ~/.buildrunner/scripts/<file>.sh`
- UI (main app): `npm run lint -- <file>` and `npm run test -- <testfile>`

## Quick Rules

- NEVER run the full suite. File-scoped commands only.
- NEVER disable RLS. Fix the policy.
- NEVER change LLM model names without explicit instruction.
- NEVER invent conventions by reading code — transcribe only rules from this file or a sub-AGENTS.md.
- NEVER commit or deploy from a sub-agent. Orchestrator only.
- IMPORTANT: Codex effort defaults to `medium`. Use `xhigh` only for agentic coding when explicitly requested.

## Router

- For runtime registry, capability levels, and fallback contracts, see @core/runtime/AGENTS.md
- For cluster nodes, dispatcher, quality firewall, feature flags, see @core/cluster/AGENTS.md
- For Cluster Max dashboard (port 4400), see @ui/dashboard/AGENTS.md
- For Jimmy (10.0.1.106) conventions, see `~/.buildrunner/agents-md/jimmy.md` (staged; deployed in Phase 3)
- For Otis (10.0.1.103) Codex execution, see `~/.buildrunner/agents-md/otis.md` (staged; deployed in Phase 12)

## Feature flags (all default OFF until Phase 13)

- `BR3_RUNTIME_OLLAMA` — enables OllamaRuntime selection
- `BR3_CACHE_BREAKPOINTS` — enables 3-breakpoint prompt cache contract
- `BR3_ADVERSARIAL_3WAY` — enables Sonnet+gpt-5.4 parallel review with Opus arbiter on disagreement
- `BR3_AUTO_CONTEXT` — UserPromptSubmit hook injection (context-bundle at :4500)

## Deploy field

The BUILD spec `**Deploy:**` header is authoritative. Run its command after every batch that modifies deployed files.
