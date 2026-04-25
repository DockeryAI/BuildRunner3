"""Godot 4 adapter installation."""

from __future__ import annotations

import re
from pathlib import Path

from core.asset_resolver import resolve_asset_path
from core.installer.adapters import AdapterResult, write_template_if_missing
from core.installer.godot_project_patcher import register_autoload

_AUTLOAD_SCRIPTS = (
    ("BRLogger", "BRLogger.gd"),
    ("GameState", "GameState.gd"),
    ("EventBus", "EventBus.gd"),
    ("SaveManager", "SaveManager.gd"),
)
GODOT_EXPECTED_FILES = (
    Path("scripts/autoloads/BRLogger.gd"),
    Path("scripts/autoloads/GameState.gd"),
    Path("scripts/autoloads/EventBus.gd"),
    Path("scripts/autoloads/SaveManager.gd"),
    Path("scripts/godot-run.sh"),
    Path("scripts/godot-test.sh"),
    Path("CLAUDE.md.godot-addendum"),
    Path("Makefile"),
)
GODOT_AUTOLOAD_NAMES = tuple(name for name, _filename in _AUTLOAD_SCRIPTS)
_MAKEFILE_MARKER_START = "# >>> br3-godot-targets >>>"
_MAKEFILE_MARKER_END = "# <<< br3-godot-targets <<<"
_BR_PROJECT_PATTERN = re.compile(
    r"(^|\n)\s*(?:function\s+)?_br_project\s*\(\s*\)",
    re.MULTILINE,
)


class GodotAdapter:
    """Install the Godot logger scaffolding and project wiring."""

    def install(self, target_repo: Path) -> AdapterResult:
        repo_root = Path(target_repo).resolve()
        project_path = repo_root / "project.godot"
        result = AdapterResult()

        if not project_path.exists():
            result.notes.append("no project.godot found; skipping")
            return result

        write_template_if_missing(
            asset_relative_path="templates/adapters/godot/scripts/autoloads/BRLogger.gd",
            target_path=repo_root / "scripts" / "autoloads" / "BRLogger.gd",
            written=result.written,
            skipped=result.skipped,
        )

        for template_name in ("GameState", "EventBus", "SaveManager"):
            self._write_renamed_template_if_missing(
                asset_relative_path=(
                    f"templates/adapters/godot/scripts/autoloads/{template_name}.gd.template"
                ),
                target_path=repo_root / "scripts" / "autoloads" / f"{template_name}.gd",
                result=result,
            )

        self._write_template_with_mode_if_missing(
            asset_relative_path="templates/adapters/godot/scripts/godot-run.sh",
            target_path=repo_root / "scripts" / "godot-run.sh",
            result=result,
            mode=0o755,
        )
        self._write_template_with_mode_if_missing(
            asset_relative_path="templates/adapters/godot/scripts/godot-test.sh",
            target_path=repo_root / "scripts" / "godot-test.sh",
            result=result,
            mode=0o755,
        )

        write_template_if_missing(
            asset_relative_path="templates/adapters/godot/CLAUDE.md.godot-addendum",
            target_path=repo_root / "CLAUDE.md.godot-addendum",
            written=result.written,
            skipped=result.skipped,
        )

        self._append_makefile_snippet(repo_root / "Makefile", result)
        self._register_autoloads(project_path, result)
        return result

    def _write_renamed_template_if_missing(
        self,
        *,
        asset_relative_path: str,
        target_path: Path,
        result: AdapterResult,
    ) -> None:
        self._write_template_with_mode_if_missing(
            asset_relative_path=asset_relative_path,
            target_path=target_path,
            result=result,
        )

    def _write_template_with_mode_if_missing(
        self,
        *,
        asset_relative_path: str,
        target_path: Path,
        result: AdapterResult,
        mode: int | None = None,
    ) -> None:
        if target_path.exists():
            result.skipped.append(target_path)
            return

        source_path = resolve_asset_path(asset_relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        if mode is not None:
            target_path.chmod(mode)
        result.written.append(target_path)

    def _append_makefile_snippet(self, makefile_path: Path, result: AdapterResult) -> None:
        snippet = resolve_asset_path("templates/adapters/godot/Makefile.snippet").read_text(
            encoding="utf-8"
        )
        if makefile_path.exists():
            existing = makefile_path.read_text(encoding="utf-8")
            if _MAKEFILE_MARKER_START in existing and _MAKEFILE_MARKER_END in existing:
                result.skipped.append(makefile_path)
                return
            separator = "" if existing.endswith("\n") or not existing else "\n"
            makefile_path.write_text(existing + separator + snippet, encoding="utf-8")
        else:
            makefile_path.write_text(snippet, encoding="utf-8")
        result.written.append(makefile_path)

    def _register_autoloads(self, project_path: Path, result: AdapterResult) -> None:
        any_changed = False
        for autoload_name, filename in _AUTLOAD_SCRIPTS:
            patch_result = register_autoload(
                project_path,
                name=autoload_name,
                script_path=f"res://scripts/autoloads/{filename}",
            )
            result.notes.extend(patch_result.notes)
            any_changed = any_changed or patch_result.changed

        if any_changed:
            if project_path not in result.written:
                result.written.append(project_path)
            return

        if project_path not in result.skipped:
            result.skipped.append(project_path)


def verify_zshrc_br_project_helper(
    zshrc_path: Path | None = None,
) -> bool:
    """Return True when ``.zshrc`` defines the ``_br_project`` helper."""
    path = Path.home() / ".zshrc" if zshrc_path is None else Path(zshrc_path)
    if not path.exists():
        return False
    return _BR_PROJECT_PATTERN.search(path.read_text(encoding="utf-8")) is not None


def install(target_repo: Path) -> AdapterResult:
    return GodotAdapter().install(target_repo)


__all__ = [
    "GODOT_AUTOLOAD_NAMES",
    "GODOT_EXPECTED_FILES",
    "GodotAdapter",
    "install",
    "verify_zshrc_br_project_helper",
]
