"""Patch ``project.godot`` while preserving unchanged section bytes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SECTION_PATTERN = re.compile(r"^\s*\[([^\]]+)\]\s*$")


@dataclass(frozen=True, slots=True)
class PatchResult:
    """Summarize a ``project.godot`` patch operation."""

    changed: bool
    sections: list[str]
    notes: list[str]


@dataclass(slots=True)
class _SectionBlock:
    name: str
    header: str
    body: list[str]


def register_autoload(
    project_godot_path: Path,
    *,
    name: str,
    script_path: str,
) -> PatchResult:
    """Ensure a Godot autoload singleton entry exists."""
    project_path = Path(project_godot_path)
    content = project_path.read_text(encoding="utf-8")
    line_ending = _detect_line_ending(content)
    preamble, sections = _parse_sections(content)
    notes: list[str] = []

    autoload_value = _normalize_autoload_value(script_path)
    desired_line = f'{name}="{autoload_value}"{line_ending}'
    autoload_section = _find_section(sections, "autoload")
    changed = False

    if autoload_section is None:
        notes.append("created [autoload] section")
        sections.append(
            _SectionBlock(
                name="autoload",
                header=f"[autoload]{line_ending}",
                body=[desired_line],
            )
        )
        notes.append(f"registered autoload {name}")
        changed = True
    else:
        existing_index = _find_autoload_entry_index(autoload_section.body, name)
        if existing_index is None:
            autoload_section.body.append(desired_line)
            notes.append(f"registered autoload {name}")
            changed = True
        else:
            existing_line = autoload_section.body[existing_index]
            existing_value = _parse_autoload_value(existing_line)
            if existing_value == autoload_value:
                notes.append(f"autoload {name} already registered")
            else:
                autoload_section.body[existing_index] = desired_line
                notes.append(f"updated autoload {name}")
                changed = True

    rendered = _render_project(preamble, sections)
    if changed and rendered != content:
        project_path.write_text(rendered, encoding="utf-8")
    else:
        changed = False

    return PatchResult(
        changed=changed,
        sections=[section.name for section in sections],
        notes=notes,
    )


def _detect_line_ending(content: str) -> str:
    if "\r\n" in content:
        return "\r\n"
    return "\n"


def _parse_sections(content: str) -> tuple[str, list[_SectionBlock]]:
    lines = content.splitlines(keepends=True)
    if not lines:
        return "", []

    preamble_lines: list[str] = []
    sections: list[_SectionBlock] = []
    current_section: _SectionBlock | None = None

    for line in lines:
        match = _SECTION_PATTERN.match(line.strip())
        if match:
            current_section = _SectionBlock(
                name=match.group(1),
                header=line,
                body=[],
            )
            sections.append(current_section)
            continue

        if current_section is None:
            preamble_lines.append(line)
        else:
            current_section.body.append(line)

    return "".join(preamble_lines), sections


def _find_section(sections: list[_SectionBlock], name: str) -> _SectionBlock | None:
    for section in sections:
        if section.name == name:
            return section
    return None


def _find_autoload_entry_index(lines: list[str], name: str) -> int | None:
    for index, line in enumerate(lines):
        key = _extract_key_name(line)
        if key == name:
            return index
    return None


def _extract_key_name(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped or stripped.startswith((";", "#")) or "=" not in line:
        return None

    key, _separator, _value = line.partition("=")
    normalized = key.strip()
    if not normalized:
        return None
    return normalized


def _parse_autoload_value(line: str) -> str | None:
    _key, _separator, value = line.partition("=")
    raw = value.strip()
    if not raw:
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        raw = raw[1:-1]
    return _normalize_autoload_value(raw)


def _normalize_autoload_value(script_path: str) -> str:
    normalized = script_path.strip()
    if normalized.startswith("*"):
        normalized = normalized[1:]
    return f"*{normalized}"


def _render_project(preamble: str, sections: list[_SectionBlock]) -> str:
    content = preamble
    if sections and content and not content.endswith(("\n", "\r")):
        content += "\n"

    for index, section in enumerate(sections):
        if index > 0 and not content.endswith(("\n", "\r")):
            content += "\n"
        content += section.header
        content += "".join(section.body)
        if index != len(sections) - 1 and not content.endswith(("\n", "\r")):
            content += "\n"

    return content


__all__ = ["PatchResult", "register_autoload"]
