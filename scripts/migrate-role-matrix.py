#!/usr/bin/env python3
"""scripts/migrate-role-matrix.py — Phase 1 migration tool.

Converts the prose Role Matrix table in BUILD_cluster-max.md into a
structured role_matrix YAML block and appends it to the file.

Usage:
    python3 scripts/migrate-role-matrix.py [--build-path PATH] [--dry-run]

Arguments:
    --build-path    Path to BUILD_cluster-max.md (default: .buildrunner/builds/BUILD_cluster-max.md)
    --dry-run       Print the YAML block without modifying the file

The script:
1. Parses the Markdown table under "### Role Matrix" in BUILD_cluster-max.md
2. Constructs a role_matrix YAML block with all phases
3. Appends the YAML block to the file (inside a fenced code block)
4. Skips if a role_matrix block already exists

Exit codes:
    0 — Success (appended or already present)
    1 — File not found
    2 — Parse error
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_BUILD_PATH = ".buildrunner/builds/BUILD_cluster-max.md"

# Maps prose builder names from the table to canonical role_matrix values
BUILDER_MAP = {
    "gpt-5.4": "codex",
    "gpt-5.3-codex": "codex",
    "gpt-5.3": "codex",
    "human": "human",
    "(human hardware install)": "human",
    "claude": "claude",
    "opus": "claude",
    "sonnet": "claude",
}

# Maps prose node names to canonical assigned_node values
# For cluster-max, Muddy is the primary command node
PHASE_NODE_MAP = {
    "0": "muddy",
    "1": "muddy",
    "2": "otis",
    "3": "otis",
    "4": "muddy",
    "5": "muddy",
    "6": "muddy",
    "7": "muddy",
    "8": "muddy",
    "9": "muddy",
    "10": "muddy",
    "11": "muddy",
    "12": "muddy",
    "13": "otis",
    "14": "otis",
    "15": "muddy",
}

# Context paths per phase (from BUILD_cluster-max phase specs)
PHASE_CONTEXT_MAP = {
    "0": ["core/cluster", "core/runtime"],
    "1": [],
    "2": ["core/cluster", "core/runtime"],
    "3": ["core/cluster", "core/runtime"],
    "4": ["core/cluster", "core/runtime"],
    "5": ["core/cluster", "core/runtime"],
    "6": ["core/cluster", "core/runtime"],
    "7": ["core/cluster", "core/runtime", "api/routes"],
    "8": ["core/cluster", "core/runtime"],
    "9": ["core/cluster", "core/review"],
    "10": ["core/cluster", "api/routes"],
    "11": ["core/cluster", "ui/dashboard", "api/routes"],
    "12": ["core/cluster", "api/routes", "core/runtime"],
    "13": ["core/cluster", "core/runtime"],
    "14": ["core/cluster"],
    "15": ["core/telemetry", "core/runtime", "core/cluster", "api/routes"],
}


def _normalize_builder(raw: str) -> str:
    """Normalize a prose builder string to a canonical role_matrix builder value."""
    raw = raw.strip()
    for key, val in BUILDER_MAP.items():
        if key.lower() in raw.lower():
            return val
    # Default: claude handles anything else
    return "claude"


def _extract_codex_model(raw: str) -> str | None:
    """Extract codex model from prose builder string."""
    raw = raw.strip()
    if "gpt-5.4" in raw and "codex" not in raw.lower():
        return "gpt-5.4"
    if "gpt-5.4" in raw:
        return "gpt-5.4"
    if "gpt-5.3-codex" in raw:
        return "gpt-5.3-codex"
    if "gpt-5.3" in raw:
        return "gpt-5.3-codex"
    return None


def _extract_effort(raw: str) -> str | None:
    """Extract effort level from prose builder string."""
    m = re.search(r"effort:(xhigh|high|medium|low)", raw)
    if m:
        return m.group(1)
    return None


def parse_role_matrix_table(content: str) -> list[dict]:
    """Parse the prose Role Matrix markdown table from BUILD_cluster-max.md.

    Returns a list of phase dicts with keys:
        phase_num, builder, codex_model, codex_effort, assigned_node, context
    """
    # Find the Role Matrix table
    table_match = re.search(
        r"### Role Matrix.*?\n(\|.*?\n)+",
        content,
        re.DOTALL,
    )
    if not table_match:
        # Try alternate pattern
        table_match = re.search(
            r"\| Ph\s*\|.*?(?=\n\n|\n##|\Z)",
            content,
            re.DOTALL,
        )
    if not table_match:
        return []

    table_text = table_match.group(0)
    phases = []

    for line in table_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Skip header and separator rows
        if "---" in line or "Ph " in line or "Architect" in line:
            continue

        cols = [c.strip() for c in line.split("|") if c.strip()]
        if len(cols) < 3:
            continue

        # Column order: Ph | Architect | Builder | Reviewers (parallel) | Arbiter | Notes
        ph_raw = cols[0].strip()
        # Extract phase number
        ph_match = re.match(r"^(\d+)", ph_raw)
        if not ph_match:
            continue
        phase_num = ph_match.group(1)

        builder_raw = cols[2] if len(cols) > 2 else ""
        builder = _normalize_builder(builder_raw)
        codex_model = _extract_codex_model(builder_raw)
        codex_effort = _extract_effort(builder_raw)

        phases.append({
            "phase_num": phase_num,
            "builder": builder,
            "codex_model": codex_model,
            "codex_effort": codex_effort,
            "assigned_node": PHASE_NODE_MAP.get(phase_num, "muddy"),
            "context": PHASE_CONTEXT_MAP.get(phase_num, ["core/cluster"]),
        })

    return phases


def build_role_matrix_yaml(phases: list[dict]) -> str:
    """Build role_matrix YAML block string from parsed phases."""
    lines = [
        "## Role Matrix (inline YAML — appended by migrate-role-matrix.py Phase 1)",
        "",
        "```yaml",
        "role_matrix:",
        "  spec: BUILD_cluster-max",
        "  default_architect: opus-4-7",
        "  default_reviewers: [sonnet-4-6, codex-gpt-5.4]",
        "  default_arbiter: opus-4-7",
        "  phases:",
    ]

    for p in phases:
        phase_key = f"phase_{p['phase_num']}"
        lines.append(f"    {phase_key}:")
        lines.append(f"      builder: {p['builder']}")
        if p.get("codex_model"):
            lines.append(f"      codex_model: {p['codex_model']}")
        if p.get("codex_effort"):
            lines.append(f"      codex_effort: {p['codex_effort']}")
        lines.append(f"      reviewers: [sonnet-4-6, codex-gpt-5.4]")
        lines.append(f"      arbiter: opus-4-7")
        lines.append(f"      assigned_node: {p['assigned_node']}")
        context_list = p.get("context", ["core/cluster"])
        if context_list:
            context_str = "[" + ", ".join(context_list) + "]"
        else:
            context_str = "[]"
        lines.append(f"      context: {context_str}")

    lines.append("```")
    return "\n".join(lines) + "\n"


def migrate(build_path: str, dry_run: bool = False) -> int:
    """Run the migration. Returns exit code."""
    path = Path(build_path)
    if not path.exists():
        print(f"ERROR: BUILD file not found: {build_path}", file=sys.stderr)
        return 1

    content = path.read_text()

    # Check if already migrated
    if "role_matrix:" in content:
        print(f"role_matrix already present in {build_path} — skipping (idempotent)")
        return 0

    # Parse the prose Role Matrix table
    phases = parse_role_matrix_table(content)
    if not phases:
        print(
            "WARNING: Could not parse Role Matrix table from prose. "
            "Using fallback phase list from known phases 0-15.",
            file=sys.stderr,
        )
        # Fallback: generate entries for all known cluster-max phases
        phases = [
            {
                "phase_num": str(n),
                "builder": "codex" if n not in (1,) else "human",
                "codex_model": "gpt-5.4" if n % 2 == 0 else "gpt-5.3-codex",
                "codex_effort": "high",
                "assigned_node": PHASE_NODE_MAP.get(str(n), "muddy"),
                "context": PHASE_CONTEXT_MAP.get(str(n), ["core/cluster"]),
            }
            for n in range(0, 16)
        ]

    yaml_block = build_role_matrix_yaml(phases)

    if dry_run:
        print("--- DRY RUN: Would append the following to", build_path, "---")
        print(yaml_block)
        return 0

    # Append to end of file
    with open(path, "a") as f:
        f.write("\n\n")
        f.write(yaml_block)

    print(f"Appended role_matrix YAML block to {build_path} ({len(phases)} phases)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate prose Role Matrix in BUILD_cluster-max.md to YAML block"
    )
    parser.add_argument(
        "--build-path",
        default=DEFAULT_BUILD_PATH,
        help=f"Path to BUILD_cluster-max.md (default: {DEFAULT_BUILD_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print YAML block without modifying the file",
    )
    args = parser.parse_args()
    sys.exit(migrate(args.build_path, args.dry_run))


if __name__ == "__main__":
    main()
