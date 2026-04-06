# Phase 2: Below Scoring Pipeline — Verification

## Deliverables

| # | Deliverable | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Intel scoring function | PASS | `_build_intel_prompt` + `_parse_intel_score` — 5 unit tests (valid, malformed, missing fields, out-of-range, prompt construction) |
| 2 | Deal scoring function | PASS | `_build_deal_prompt` + `_parse_deal_score` — 5 unit tests (valid, malformed, invalid verdict, out-of-range, prompt construction) |
| 3 | Deduplication before scoring | PASS | URL hash (Phase 1 schema), title cosine similarity via Below embeddings — 3 unit tests (identical, orthogonal, threshold) |
| 4 | Confidence flagging | PASS | `_flag_needs_opus_review` sets `needs_opus_review=1` on parse failure — 1 unit test with real DB |
| 5 | Scoring cron | PASS | `start_scoring_cron()` in `intel_scoring.py`, triggered from `node_intelligence.py` startup when `DISABLE_SCORING=false`, 30-min interval |
| 6 | Below offline fallback | PASS | 3s connect timeout, returns None on error, cycle stops gracefully — 1 async unit test |
| 7 | Exceptional deal Discord alert | PASS | `_send_discord_alert` fires when deal_score >= 80, configurable URL via env — 2 unit tests (payload construction, no-URL skip) |

## Test Results
- 17/17 tests passing
- All imports verified

## Files Modified
- `core/cluster/intel_scoring.py` (NEW — 535 lines)
- `core/cluster/node_intelligence.py` (MODIFIED — scoring cron + 2 endpoints)
- `core/cluster/intel_schema.sql` (MODIFIED — added below_assessment column)
- `tests/test_intel_scoring.py` (NEW — 17 tests)
