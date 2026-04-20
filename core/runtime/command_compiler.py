"""BR3 command compiler for runtime-neutral command and skill bundles."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


MAX_CONTEXT_CHARS = 12_000


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _inventory_path() -> Path:
    return _repo_root() / ".buildrunner" / "runtime-command-inventory.json"


def _capabilities_path() -> Path:
    return Path(__file__).resolve().with_name("command_capabilities.json")


def _normalize_command_name(name: str) -> str:
    return str(name or "").strip().lower().lstrip("/")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@dataclass
class CommandContextFile:
    """Context file included in a compiled command bundle."""

    path: str
    content: str
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SkillTranslation:
    """Mapping from a Claude skill into a Codex skill package."""

    source_name: str
    source_path: str
    target_name: str
    target_path: str
    status: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompiledCommandBundle:
    """Runtime-neutral bundle for one BR3 command invocation."""

    command_name: str
    runtime: str
    support_level: str
    fallback_runtime: str
    workflow_name: str | None
    command_doc_path: str
    command_doc: str
    inventory_record: dict[str, Any]
    skill_mappings: list[SkillTranslation]
    context_files: list[CommandContextFile]
    user_request: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_name": self.command_name,
            "runtime": self.runtime,
            "support_level": self.support_level,
            "fallback_runtime": self.fallback_runtime,
            "workflow_name": self.workflow_name,
            "command_doc_path": self.command_doc_path,
            "inventory_record": self.inventory_record,
            "skill_mappings": [item.to_dict() for item in self.skill_mappings],
            "context_files": [item.to_dict() for item in self.context_files],
            "user_request": self.user_request,
            "notes": self.notes,
        }

    def render_prompt(self) -> str:
        """Render a BR3-owned prompt package for runtime adapters."""
        lines = [
            f"# BR3 Compiled Command Bundle: /{self.command_name}",
            f"Runtime: {self.runtime}",
            f"Support Level: {self.support_level}",
            f"Fallback Runtime: {self.fallback_runtime}",
        ]
        if self.workflow_name:
            lines.append(f"Workflow Name: {self.workflow_name}")
        if self.notes:
            lines.extend(["", "## BR3 Notes"])
            lines.extend(f"- {note}" for note in self.notes)
        lines.extend(
            [
                "",
                "## User Request",
                self.user_request.strip() or "No explicit user request supplied.",
                "",
                "## Command Source",
                f"Path: {self.command_doc_path}",
                self.command_doc.strip(),
            ]
        )
        if self.skill_mappings:
            lines.extend(["", "## Translated Skills"])
            for skill in self.skill_mappings:
                lines.append(
                    f"- {skill.target_name}: source={skill.source_path} target={skill.target_path} status={skill.status}"
                )
                for note in skill.notes:
                    lines.append(f"  note: {note}")
        if self.context_files:
            lines.extend(["", "## Project Context"])
            for item in self.context_files:
                lines.extend(
                    [
                        f"### {item.path}",
                        item.content.strip(),
                    ]
                )
                if item.truncated:
                    lines.append("[TRUNCATED]")
        lines.extend(
            [
                "",
                "## BR3 Output Contract",
                "Return only the BUILD/spec draft markdown body.",
                "Do not claim edits were applied.",
                "Do not bypass BR3 validation, adversarial review, or approval gates.",
            ]
        )
        return "\n".join(lines).strip() + "\n"


def load_command_inventory(path: Path | None = None) -> dict[str, Any]:
    """Load the authoritative runtime command inventory."""
    inventory_path = path or _inventory_path()
    payload = json.loads(_read_text(inventory_path))
    commands = payload.get("commands", [])
    if not isinstance(commands, list):
        raise ValueError("runtime-command-inventory.json.commands must be a list")
    payload["commands_by_name"] = {
        _normalize_command_name(item.get("name") or item.get("command")): item
        for item in commands
        if isinstance(item, dict)
    }
    return payload


def load_command_capabilities(path: Path | None = None) -> dict[str, Any]:
    """Load the curated BR3 command capability map."""
    capabilities_path = path or _capabilities_path()
    payload = json.loads(_read_text(capabilities_path))
    commands = payload.get("commands", {})
    if not isinstance(commands, dict):
        raise ValueError("command_capabilities.json.commands must be an object")
    payload["commands"] = {
        _normalize_command_name(name): value
        for name, value in commands.items()
        if isinstance(value, dict)
    }
    return payload


def _default_support_level(inventory_record: dict[str, Any], capabilities: dict[str, Any]) -> str:
    defaults = capabilities.get("defaults", {})
    if inventory_record.get("migration_bucket") == "keep-Claude-first" or inventory_record.get(
        "fallback_runtime"
    ) == "claude":
        return str(defaults.get("claude_first_support_level") or "claude_only")
    return str(defaults.get("non_claude_first_support_level") or "codex_ready")


def _load_skill_mapping_doc() -> list[dict[str, Any]]:
    mapping_doc = _repo_root() / ".buildrunner" / "runtime-skill-mapping.md"
    if not mapping_doc.exists():
        return []
    mappings: list[dict[str, Any]] = []
    for line in mapping_doc.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 5 or parts[0] == "`Claude Skill`":
            continue
        mappings.append(
            {
                "source_name": parts[0].strip("` "),
                "source_path": parts[1].strip("` "),
                "target_name": parts[2].strip("` "),
                "target_path": parts[3].strip("` "),
                "status": parts[4].strip("` "),
            }
        )
    return mappings


def _resolve_skill_translations(
    inventory_record: dict[str, Any], capability_entry: dict[str, Any]
) -> list[SkillTranslation]:
    source_skills = list(inventory_record.get("dependencies", {}).get("skills", []))
    preferred_targets = list(capability_entry.get("codex_skill_names", []))
    mapping_index = {item["source_name"]: item for item in _load_skill_mapping_doc()}
    translations: list[SkillTranslation] = []

    for target_name in preferred_targets:
        mapping = mapping_index.get(target_name)
        if mapping is None:
            source_path = str(Path.home() / ".claude" / "skills" / f"{target_name}.md")
            target_path = str(Path.home() / ".codex" / "skills" / target_name / "SKILL.md")
            translations.append(
                SkillTranslation(
                    source_name=target_name,
                    source_path=source_path,
                    target_name=target_name,
                    target_path=target_path,
                    status="installed",
                )
            )
            continue
        translations.append(
            SkillTranslation(
                source_name=mapping["source_name"],
                source_path=mapping["source_path"],
                target_name=mapping["target_name"],
                target_path=mapping["target_path"],
                status=mapping["status"],
                notes=(["Command-specific preferred skill"] if target_name in source_skills else []),
            )
        )
    return translations


def _collect_context_files(project_root: Path, patterns: list[str]) -> list[CommandContextFile]:
    files: list[CommandContextFile] = []
    for pattern in patterns:
        matches = sorted(project_root.glob(pattern))
        for match in matches:
            if not match.is_file():
                continue
            content = _read_text(match)
            truncated = len(content) > MAX_CONTEXT_CHARS
            if truncated:
                content = content[:MAX_CONTEXT_CHARS]
            relative_path = match.relative_to(project_root).as_posix()
            files.append(CommandContextFile(path=relative_path, content=content, truncated=truncated))
    deduped: dict[str, CommandContextFile] = {}
    for item in files:
        deduped[item.path] = item
    return list(deduped.values())


def compile_command_bundle(
    *,
    command_name: str,
    runtime: str,
    project_root: str | Path,
    user_request: str,
    inventory_path: Path | None = None,
    capabilities_path: Path | None = None,
) -> CompiledCommandBundle:
    """Compile one command into a runtime-neutral BR3 bundle."""
    normalized = _normalize_command_name(command_name)
    inventory = load_command_inventory(inventory_path)
    capabilities = load_command_capabilities(capabilities_path)
    inventory_record = inventory["commands_by_name"].get(normalized)
    if inventory_record is None:
        raise KeyError(f"Unknown command: {command_name}")
    capability_entry = capabilities["commands"].get(normalized, {})
    support_level = str(capability_entry.get("support_level") or _default_support_level(inventory_record, capabilities))
    command_doc_path = Path(inventory_record["path"])
    context_patterns = list(capability_entry.get("context_files", []))
    context_files = _collect_context_files(Path(project_root), context_patterns)
    notes = list(capability_entry.get("notes", []))
    notes.append(f"Inventory bucket: {inventory_record.get('migration_bucket')}")
    notes.append(f"Portability rating: {inventory_record.get('portability_rating')}")
    return CompiledCommandBundle(
        command_name=normalized,
        runtime=runtime,
        support_level=support_level,
        fallback_runtime=str(capability_entry.get("fallback_runtime") or inventory_record.get("fallback_runtime") or "claude"),
        workflow_name=capability_entry.get("workflow_name"),
        command_doc_path=str(command_doc_path),
        command_doc=_read_text(command_doc_path),
        inventory_record=inventory_record,
        skill_mappings=_resolve_skill_translations(inventory_record, capability_entry),
        context_files=context_files,
        user_request=user_request,
        notes=notes,
    )
