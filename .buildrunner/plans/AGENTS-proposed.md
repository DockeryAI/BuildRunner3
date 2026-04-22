# AGENTS.md

## Build & Test

- Test research worker: `python -m pytest core/cluster/below/tests/`
- Lint single file: `ruff check <path>`
- Type-check: `mypy <path>`
- Reindex trigger: `core/cluster/scripts/reindex-research.sh`
- Retrieve test: `curl -X POST http://10.0.1.106:8100/retrieve -d '{"query":"<q>","top_k":5}'`
- Cluster health: `~/.buildrunner/scripts/cluster-check.sh semantic-search`

## Library Access — HARD RULE

- Library lives only at `/srv/jimmy/research-library/` on Jimmy (10.0.1.106).
- Access via `POST /retrieve` on `:8100`. No other read path is supported.
- Never read, grep, cat, or find against any local `research-library/` path.
- Write path: SSH to Jimmy, edit, commit, push to GitHub origin. Or enqueue via `.buildrunner/research-queue/pending.jsonl` and let the Below worker commit.

## Queue Conventions

- Pending records: `.buildrunner/research-queue/pending.jsonl`
- Completed records: `.buildrunner/research-queue/completed.jsonl`
- One JSON object per line. Schema in `core/cluster/below/queue_schema.py`.
- Never drop a pending record silently; fatal errors must become `status: error` completed records.

## Prohibitions

- Do not re-create `~/Projects/research-library/` on Muddy. The `block-muddy-library` hook rejects reads.
- Do not commit directly to Jimmy's repo from Muddy — go through the Below worker or SSH.
- Do not change the /research skill's model pin (claude-sonnet-4-6 is deliberate — 4.7 long-context regression).
- Do not add `temperature`, `top_p`, `top_k`, or `budget_tokens` to any Claude API call in this project.

## Effort Allocation for Codex

- Phase 1, 8, 10: xHigh (irreversibility / security)
- Phase 6: Medium with GPT-5.3-Codex (terminal-heavy worker)
- All others: Medium default
