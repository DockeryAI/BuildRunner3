#!/usr/bin/env python3
"""Audit Claude command portability for BR3 runtime migration planning."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import yaml

HOME = Path.home()
COMMANDS_DIR = HOME / ".claude" / "commands"
SKILLS_DIR = HOME / ".claude" / "skills"

CORE_COMMANDS = {
    "amend",
    "autopilot",
    "begin",
    "brainstorm",
    "commit",
    "dead",
    "design",
    "diag",
    "gaps",
    "guard",
    "research",
    "review",
    "roadmap",
    "spec",
    "test",
    "worktree",
}

LOW_VALUE_COMMANDS = {
    "brief": "session helper; auto-runs via hook and is not a migration priority",
    "concise": "formatting helper, not a substantive runtime workflow",
    "later": "response-style helper, low migration value",
    "restart": "redundant with /3 and narrower in scope",
    "rules": "policy display helper, not a core runtime workflow",
    "save": "session helper; low migration priority",
    "why": "explanation helper, not a substantive runtime workflow",
}

RESEARCH_PLANNING_COMMANDS = {
    "amend",
    "autopilot",
    "begin",
    "brainstorm",
    "design",
    "gaps",
    "guard",
    "learn",
    "llm",
    "opus",
    "prompt",
    "research",
    "research-audit",
    "roadmap",
    "spec",
    "worktree",
}

BUSINESS_DOMAIN_COMMANDS = {
    "business",
    "geo",
    "geo-coach",
    "sales",
    "setlist",
    "social",
}

EXTERNAL_TOOL_PATTERNS = {
    "claude": r"\bclaude\b",
    "codex": r"\bcodex\b",
    "curl": r"\bcurl\b",
    "docker": r"\bdocker(?:-compose)?\b",
    "gh": r"\bgh\b",
    "git": r"\bgit\b",
    "lsof": r"\blsof\b",
    "make": r"\bmake\b",
    "netlify": r"\bnetlify\b",
    "node": r"\bnode\b",
    "npm": r"\bnpm\b",
    "playwright": r"\bplaywright\b",
    "pnpm": r"\bpnpm\b",
    "python3": r"\bpython3\b",
    "supabase": r"\bsupabase\b",
    "vercel": r"\bvercel\b",
    "yarn": r"\byarn\b",
}

COMMAND_CATEGORY_KEYWORDS = {
    "cluster_ops": {"cluster", "lockwood", "walter", "semantic-search", "heartbeat", "node_url"},
    "design": {"design", "mockup", "figma", "recraft", "appdesign", "visual"},
    "execution": {"commit", "test", "review", "fix", "build", "dev server", "deploy"},
    "planning": {"phase", "build spec", "plan", "architecture", "governance", "drift"},
    "research": {"research", "websearch", "webfetch", "source", "evidence", "case study"},
    "session_helper": {"plain-language", "session start", "developer brief", "tone", "restart"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        default=".buildrunner/runtime-command-inventory.json",
        help="Path to write JSON inventory",
    )
    parser.add_argument(
        "--md-out",
        default=".buildrunner/runtime-command-inventory.md",
        help="Path to write Markdown inventory",
    )
    return parser.parse_args()


def load_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text
    raw_frontmatter = parts[0][4:]
    try:
        frontmatter = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError:
        frontmatter = {}
        for line in raw_frontmatter.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter, parts[1]


def discover_skills() -> list[dict]:
    skills: list[dict] = []
    seen = set()
    if not SKILLS_DIR.exists():
        return skills
    for path in sorted(SKILLS_DIR.iterdir()):
        if path.name.startswith("."):
            continue
        if path.is_dir() and (path / "SKILL.md").exists():
            name = path.name
            skill_path = path / "SKILL.md"
        elif path.is_file() and path.suffix == ".md":
            name = path.stem
            skill_path = path
        else:
            continue
        if name in seen:
            continue
        seen.add(name)
        skills.append({"name": name, "path": str(skill_path)})
    return skills


def slug(path: Path) -> str:
    return path.stem


def heading_or_description(body: str, frontmatter: dict, name: str) -> str:
    if frontmatter.get("description"):
        return str(frontmatter["description"]).strip()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ").strip()
        if stripped:
            return stripped
    return name


def find_matches(pattern: str, text: str) -> list[str]:
    return sorted(set(re.findall(pattern, text, flags=re.IGNORECASE)))


def classify_category(name: str, description: str, body: str) -> str:
    if name in BUSINESS_DOMAIN_COMMANDS:
        return "business_domain"
    lowered = f"{name}\n{description}\n{body}".lower()
    best = ("misc", 0)
    for category, keywords in COMMAND_CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best[1]:
            best = (category, score)
    return best[0]


def derive_usage_tier(name: str, category: str) -> str:
    if name in CORE_COMMANDS:
        return "core"
    if category in {"execution", "planning", "research", "cluster_ops", "design"}:
        return "standard"
    return "niche"


def derive_status(name: str, line_count: int) -> tuple[str, str | None]:
    if name in LOW_VALUE_COMMANDS:
        return "low_value", LOW_VALUE_COMMANDS[name]
    if line_count < 20 and name not in {"brief", "restart"}:
        return "low_value", "minimal helper command with narrow scope"
    return "active", None


def portability_profile(
    name: str,
    category: str,
    status: str,
    signals: dict,
    allowed_tools: list[str],
    model: str,
) -> tuple[str, str, str, list[str]]:
    reasons: list[str] = []
    if name in RESEARCH_PLANNING_COMMANDS or category in {"research", "design"}:
        reasons.append("planning/research/design command remains Claude-first by policy")
        return "claude_first", "keep-Claude-first", "claude", reasons
    score = 0
    if status == "low_value":
        score += 1
        reasons.append("low migration value")
    if signals["browser_tool_dependence"]:
        score += 3
        reasons.append("browser/web research dependence")
    if signals["cluster_usage"]:
        score += 2
        reasons.append("cluster integration")
    if signals["subagent_usage"]:
        score += 2
        reasons.append("subagent orchestration")
    if signals["hook_dependence"]:
        score += 3
        reasons.append("hook/governance coupling")
    if signals["interactive_gate"]:
        score += 2
        reasons.append("user gating / interactive stop points")
    if signals["skill_dependence"]:
        score += 1
        reasons.append("skill-specific behavior")
    if "AskUserQuestion" in allowed_tools or "Skill" in allowed_tools:
        score += 1
    if model == "opus":
        score += 1
    if score <= 1:
        return "high", "trivial", "codex", reasons or ["simple local command flow"]
    if score <= 3:
        return "medium", "moderate", "hybrid", reasons
    if score <= 5:
        return "low", "hard", "hybrid", reasons
    return "claude_first", "keep-Claude-first", "claude", reasons


def effort_estimate(bucket: str) -> str:
    return {
        "trivial": "S",
        "moderate": "M",
        "hard": "L",
        "keep-Claude-first": "XL",
    }[bucket]


def collect_inventory() -> dict:
    command_paths = sorted(COMMANDS_DIR.glob("*.md"))
    command_names = {path.stem for path in command_paths}
    skills = discover_skills()
    skill_names = {entry["name"] for entry in skills}
    commands = []

    for path in command_paths:
        frontmatter, body = load_frontmatter(path)
        text = path.read_text(encoding="utf-8")
        name = slug(path)
        description = heading_or_description(body, frontmatter, name)
        allowed_tools_raw = frontmatter.get("allowed-tools", [])
        if isinstance(allowed_tools_raw, str):
            allowed_tools = [tool.strip() for tool in allowed_tools_raw.split(",") if tool.strip()]
        else:
            allowed_tools = [str(tool).strip() for tool in allowed_tools_raw]
        scripts = find_matches(r"~/.buildrunner/scripts/[A-Za-z0-9._/\-]+", text)
        docs = [doc.lstrip("@") for doc in find_matches(r"@?~/.claude/docs/[A-Za-z0-9._/\-]+", text)]
        command_refs = sorted(
            {
                ref
                for ref in find_matches(r"/([a-z0-9][a-z0-9-]*)", text.lower())
                if ref in command_names and ref != name
            }
        )
        external_tools = sorted(
            tool_name
            for tool_name, pattern in EXTERNAL_TOOL_PATTERNS.items()
            if re.search(pattern, text, flags=re.IGNORECASE)
        )
        matched_skills = sorted(
            skill
            for skill in skill_names
            if skill in text.lower() or skill == name
        )
        signals = {
            "cluster_usage": bool(
                re.search(r"cluster-check|lockwood|walter|node_url|/api/", text, flags=re.IGNORECASE)
            ),
            "subagent_usage": "Task" in allowed_tools
            or "Agent" in allowed_tools
            or bool(re.search(r"subagent|explore subagents?|agent tool", text, flags=re.IGNORECASE)),
            "hook_dependence": bool(
                re.search(
                    r"hook|pretooluse|pre-commit|sessionstart|enforce-skill-steps|platform_hook",
                    text,
                    flags=re.IGNORECASE,
                )
            ),
            "browser_tool_dependence": any(tool in {"WebSearch", "WebFetch"} for tool in allowed_tools)
            or bool(re.search(r"playwright|browser|crawl|screenshot|perplexity|recraft", text, flags=re.IGNORECASE)),
            "skill_dependence": "Skill" in allowed_tools or bool(matched_skills),
            "interactive_gate": "AskUserQuestion" in allowed_tools
            or bool(re.search(r"wait for user|which option|approval gate|stop and wait", text, flags=re.IGNORECASE)),
        }
        category = classify_category(name, description, body)
        usage_tier = derive_usage_tier(name, category)
        status, status_reason = derive_status(name, len(text.splitlines()))
        portability, bucket, fallback_runtime, portability_reasons = portability_profile(
            name=name,
            category=category,
            status=status,
            signals=signals,
            allowed_tools=allowed_tools,
            model=str(frontmatter.get("model", "default")),
        )

        commands.append(
            {
                "command": f"/{name}",
                "name": name,
                "path": str(path),
                "description": description,
                "model": str(frontmatter.get("model", "default")),
                "allowed_tools": allowed_tools,
                "category": category,
                "usage_tier": usage_tier,
                "status": status,
                "status_reason": status_reason,
                "dependencies": {
                    "scripts": scripts,
                    "docs": docs,
                    "skills": matched_skills,
                    "commands": command_refs,
                    "external_tools": external_tools,
                },
                "cluster_usage": signals["cluster_usage"],
                "subagent_usage": signals["subagent_usage"],
                "hook_dependence": signals["hook_dependence"],
                "browser_tool_dependence": signals["browser_tool_dependence"],
                "portability_rating": portability,
                "fallback_runtime": fallback_runtime,
                "effort_estimate": effort_estimate(bucket),
                "migration_bucket": bucket,
                "portability_rationale": portability_reasons,
                "line_count": len(text.splitlines()),
            }
        )

    bucket_counts = Counter(command["migration_bucket"] for command in commands)
    category_counts = Counter(command["category"] for command in commands)
    portability_counts = Counter(command["portability_rating"] for command in commands)
    core_commands = [command for command in commands if command["usage_tier"] == "core"]
    constrained_core = [
        command
        for command in core_commands
        if command["portability_rating"] in {"low", "claude_first"}
    ]
    low_portability_share = round(len(constrained_core) / max(len(core_commands), 1), 4)
    hybrid_strategy = low_portability_share > 0.25

    rollout_order = [
        {
            "stage": "Stage 1",
            "bucket": "trivial",
            "commands": [command["command"] for command in commands if command["migration_bucket"] == "trivial"],
            "focus": "simple local execution commands with minimal orchestration coupling",
        },
        {
            "stage": "Stage 2",
            "bucket": "moderate",
            "commands": [command["command"] for command in commands if command["migration_bucket"] == "moderate"],
            "focus": "commands with manageable cluster or interaction coupling after runtime selection exists",
        },
        {
            "stage": "Stage 3",
            "bucket": "hard",
            "commands": [command["command"] for command in commands if command["migration_bucket"] == "hard"],
            "focus": "commands needing explicit adapter or policy extraction work",
        },
        {
            "stage": "Stage 4",
            "bucket": "keep-Claude-first",
            "commands": [
                command["command"] for command in commands if command["migration_bucket"] == "keep-Claude-first"
            ],
            "focus": "research, planning, architecture, and browser-heavy commands retained on Claude",
        },
    ]

    return {
        "generated_at": "2026-04-15",
        "source": {
            "commands_dir": str(COMMANDS_DIR),
            "skills_dir": str(SKILLS_DIR),
        },
        "summary": {
            "total_commands": len(commands),
            "total_skills": len(skills),
            "bucket_counts": dict(bucket_counts),
            "category_counts": dict(category_counts),
            "portability_counts": dict(portability_counts),
            "core_command_count": len(core_commands),
            "core_low_portability_count": len(constrained_core),
            "core_low_portability_share": low_portability_share,
        },
        "decision_gate": {
            "result": "formalize_long_term_hybrid_strategy" if hybrid_strategy else "near_term_parity_still_viable",
            "reason": (
                f"{len(constrained_core)} of {len(core_commands)} core commands "
                f"({low_portability_share:.0%}) are low-portability or Claude-first."
            ),
        },
        "rollout_order": rollout_order,
        "skills": skills,
        "commands": commands,
    }


def markdown_table_row(command: dict) -> str:
    def esc(value: str) -> str:
        return value.replace("|", "\\|")

    signals = []
    if command["cluster_usage"]:
        signals.append("cluster")
    if command["subagent_usage"]:
        signals.append("subagents")
    if command["hook_dependence"]:
        signals.append("hooks")
    if command["browser_tool_dependence"]:
        signals.append("browser")
    signal_text = ", ".join(signals) or "local"
    return (
        f"| `{esc(command['command'])}` | {esc(command['category'])} | {esc(command['portability_rating'])} | "
        f"{esc(command['migration_bucket'])} | {esc(command['fallback_runtime'])} | "
        f"{esc(command['effort_estimate'])} | {esc(command['status'])} | {esc(signal_text)} |"
    )


def render_markdown(inventory: dict) -> str:
    summary = inventory["summary"]
    decision = inventory["decision_gate"]
    lines = [
        "# Runtime Command Inventory",
        "",
        f"Generated: {inventory['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Total commands cataloged: {summary['total_commands']}",
        f"- Total skills discovered: {summary['total_skills']}",
        f"- Migration buckets: {json.dumps(summary['bucket_counts'], sort_keys=True)}",
        f"- Portability ratings: {json.dumps(summary['portability_counts'], sort_keys=True)}",
        "",
        "## Decision Gate",
        "",
        f"- Result: `{decision['result']}`",
        f"- Basis: {decision['reason']}",
        "- Recommendation: retain a long-term hybrid split with Claude default for research, planning, architecture, and browser-heavy flows while migrating execution-centric commands first."
        if decision["result"] == "formalize_long_term_hybrid_strategy"
        else "- Recommendation: near-term parity remains viable for most core commands.",
        "",
        "## Rollout Order",
        "",
    ]
    for stage in inventory["rollout_order"]:
        lines.extend(
            [
                f"### {stage['stage']} — `{stage['bucket']}`",
                "",
                f"- Focus: {stage['focus']}",
                f"- Commands: {', '.join(f'`{command}`' for command in stage['commands']) or '_none_'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Skill Inputs",
            "",
            "| Skill | Path |",
            "| ---- | ---- |",
        ]
    )
    for skill in inventory["skills"]:
        lines.append(f"| `{skill['name']}` | `{skill['path']}` |")

    lines.extend(
        [
            "",
            "## Command Catalog",
            "",
            "| Command | Category | Portability | Bucket | Fallback | Effort | Status | Signals |",
            "| ------- | -------- | ----------- | ------ | -------- | ------ | ------ | ------- |",
        ]
    )
    for command in inventory["commands"]:
        lines.append(markdown_table_row(command))

    lines.extend(["", "## Notes", ""])
    for command in inventory["commands"]:
        if command["status"] != "active" or command["migration_bucket"] == "keep-Claude-first":
            reason = command["status_reason"] or "; ".join(command["portability_rationale"])
            lines.append(f"- `{command['command']}`: {reason}")

    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    inventory = collect_inventory()
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(inventory), encoding="utf-8")
    print(f"Wrote {json_out}")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
