"""core/cluster/private_filter.py — Shared [private] scrubber.

Single source of truth for the `[private]` line filter used by every
egress path (context bundles, /retrieve responses, future channels).

Pattern is word-boundary anchored so `[privately]`, `[private-note]`,
and `foo[private]bar` DO NOT match — only a bare `[private]` token.

Layer 1 of defense-in-depth runs in sync-cluster-context.sh at the mirror.
THIS module is Layer 2 (in-process). Every egress must pipe content
through `filter_private_lines` before returning it to any model.
"""

from __future__ import annotations

import re

# (?<![a-zA-Z0-9_]) — not preceded by a word char (rejects foo[private])
# \[private\]        — literal bracketed token (case-sensitive)
# (?![a-zA-Z0-9_-])  — not followed by a word char or hyphen (rejects [private-note])
_PRIVATE_PATTERN = re.compile(r"(?<![a-zA-Z0-9_])\[private\](?![a-zA-Z0-9_-])")


def filter_private_lines(text: str) -> str:
    """Drop any line containing a word-anchored `[private]` token.

    Case-sensitive. Preserves original line endings of surviving lines.
    Idempotent — running twice produces the same output.
    """
    lines = text.splitlines(keepends=True)
    return "".join(line for line in lines if not _PRIVATE_PATTERN.search(line))
