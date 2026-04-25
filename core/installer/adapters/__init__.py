"""Framework-specific installer adapters for BuildRunner."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from core.asset_resolver import resolve_asset_path

if TYPE_CHECKING:
    from core.installer.codemod import CodemodResult


@dataclass(slots=True)
class AdapterResult:
    """Summarize an adapter installation run."""

    written: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    codemods: dict[str, CodemodResult] = field(default_factory=dict)
    script_suggestions: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"written={len(self.written)} skipped={len(self.skipped)} "
            f"codemods={len(self.codemods)} scripts={len(self.script_suggestions)}"
        )


def write_template_if_missing(
    *,
    asset_relative_path: str,
    target_path: Path,
    written: list[Path],
    skipped: list[Path],
) -> None:
    """Copy a packaged template into a repository without overwriting local edits."""
    if target_path.exists():
        skipped.append(target_path)
        return

    source_path = resolve_asset_path(asset_relative_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    written.append(target_path)


def relative_import_path(from_file: Path, target_file: Path) -> str:
    """Build an extensionless relative import path."""
    from_dir = from_file.parent.resolve()
    target = target_file.resolve()
    relative = Path(os.path.relpath(str(target), str(from_dir))).with_suffix("")
    as_posix = relative.as_posix()
    if not as_posix.startswith("."):
        return f"./{as_posix}"
    return as_posix


__all__ = [
    "AdapterResult",
    "relative_import_path",
    "write_template_if_missing",
]
