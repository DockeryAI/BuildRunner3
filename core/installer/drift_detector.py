"""Read-only BR3 drift detection for attached repositories."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from core.asset_resolver import resolve_asset_path
from core.installer import CoreBaselineInstaller
from core.installer.adapters.expo import EXPO_EXPECTED_FILES
from core.installer.adapters.godot import GODOT_AUTOLOAD_NAMES, GODOT_EXPECTED_FILES
from core.installer.adapters.next import NEXT_EXPECTED_FILES
from core.installer.adapters.react_vite import REACT_VITE_EXPECTED_FILES
from core.installer.capabilities import CAPABILITY_EXPECTED_FILES
from core.installer.hook_installer import HOOK_EXPECTED_FILES
from core.project_type.facets import Bundler, Framework, ProjectFacets
from core.retrofit.codebase_scanner import CodebaseScanner

_STRUCTURED_BASELINE_FILES = {
    Path(".buildrunner/agents.json"): "templates/core-baseline/agents.json",
    Path(".buildrunner/skill-state.json"): "templates/core-baseline/skill-state.json",
    Path(".buildrunner/orchestration_state.json"): "templates/core-baseline/orchestration_state.json",
}


class DriftKind(StrEnum):
    MISSING_FILE = "missing_file"
    MODIFIED_FILE = "modified_file"
    MISSING_CONFIG_KEY = "missing_config_key"
    MISSING_HOOK = "missing_hook"
    MISSING_AUTOLOAD = "missing_autoload"
    STALE_TEMPLATE = "stale_template"


@dataclass(slots=True)
class DriftEntry:
    kind: DriftKind
    path: Path
    expected: str | None
    actual: str | None
    note: str


@dataclass(slots=True)
class DriftReport:
    entries: list[DriftEntry]
    facets: ProjectFacets | None

    @property
    def has_drift(self) -> bool:
        return bool(self.entries)

    def by_kind(self) -> dict[DriftKind, list[DriftEntry]]:
        grouped: dict[DriftKind, list[DriftEntry]] = defaultdict(list)
        for entry in self.entries:
            grouped[entry.kind].append(entry)
        return dict(grouped)

    def summary(self) -> str:
        if not self.entries:
            facets_text = f" ({self.facets})" if self.facets is not None else ""
            return f"No drift detected{facets_text}"

        return (
            f"Drift detected: {len(self.entries)} issue(s) across "
            f"{len(self.by_kind())} kind(s)"
        )


def detect_drift(
    target_repo: Path,
    *,
    declared_facets: ProjectFacets | None = None,
) -> DriftReport:
    repo_root = Path(target_repo).resolve()
    facets = declared_facets
    if facets is None:
        facets, _report = CodebaseScanner(repo_root).detect_facets()

    entries: list[DriftEntry] = []

    for relative_path in CoreBaselineInstaller.expected_files():
        _record_missing_file(entries, repo_root, relative_path, "baseline file missing")

    _detect_missing_baseline_keys(repo_root, entries)

    for relative_path in _expected_adapter_files(repo_root, facets):
        _record_missing_file(entries, repo_root, relative_path, "adapter file missing")

    for capability in facets.capabilities:
        for relative_path in CAPABILITY_EXPECTED_FILES.get(capability, ()):
            _record_missing_file(
                entries,
                repo_root,
                relative_path,
                f"capability file missing ({capability.value})",
            )

    if facets.framework is Framework.godot:
        _detect_godot_autoload_drift(repo_root, entries)

    if (repo_root / ".git").is_dir():
        for relative_path in HOOK_EXPECTED_FILES:
            absolute_path = repo_root / relative_path
            if not absolute_path.exists():
                entries.append(
                    DriftEntry(
                        kind=DriftKind.MISSING_HOOK,
                        path=absolute_path,
                        expected=relative_path.as_posix(),
                        actual=None,
                        note="BR3 hook asset missing",
                    )
                )

    return DriftReport(entries=entries, facets=facets)


def _record_missing_file(
    entries: list[DriftEntry],
    repo_root: Path,
    relative_path: Path,
    note: str,
) -> None:
    absolute_path = repo_root / relative_path
    if absolute_path.exists():
        return
    entries.append(
        DriftEntry(
            kind=DriftKind.MISSING_FILE,
            path=absolute_path,
            expected=relative_path.as_posix(),
            actual=None,
            note=note,
        )
    )


def _detect_missing_baseline_keys(repo_root: Path, entries: list[DriftEntry]) -> None:
    for relative_path, asset_relative_path in _STRUCTURED_BASELINE_FILES.items():
        target_path = repo_root / relative_path
        if not target_path.exists():
            continue

        try:
            current = json.loads(target_path.read_text(encoding="utf-8"))
            template = json.loads(resolve_asset_path(asset_relative_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(current, dict) or not isinstance(template, dict):
            continue

        missing_keys = sorted(key for key in template if key not in current)
        if missing_keys:
            entries.append(
                DriftEntry(
                    kind=DriftKind.MISSING_CONFIG_KEY,
                    path=target_path,
                    expected=", ".join(missing_keys),
                    actual=", ".join(sorted(current.keys())),
                    note="baseline structured file is missing required top-level key(s)",
                )
            )


def _expected_adapter_files(repo_root: Path, facets: ProjectFacets) -> tuple[Path, ...]:
    if facets.framework is Framework.godot:
        return GODOT_EXPECTED_FILES
    if facets.framework is Framework.expo:
        return EXPO_EXPECTED_FILES
    if facets.framework is Framework.react and facets.bundler is Bundler.vite:
        return REACT_VITE_EXPECTED_FILES
    if facets.framework is Framework.react and facets.bundler is Bundler.next:
        logger_path = Path("app/components/BRLoggerNext.tsx")
        if not (repo_root / "app").is_dir() and (repo_root / "pages").is_dir():
            logger_path = Path("components/BRLoggerNext.tsx")
        return (logger_path, *NEXT_EXPECTED_FILES[1:])
    return ()


def _detect_godot_autoload_drift(repo_root: Path, entries: list[DriftEntry]) -> None:
    project_path = repo_root / "project.godot"
    if not project_path.exists():
        return

    registered_names = _load_godot_autoload_names(project_path)
    for autoload_name in GODOT_AUTOLOAD_NAMES:
        if autoload_name in registered_names:
            continue
        entries.append(
            DriftEntry(
                kind=DriftKind.MISSING_AUTOLOAD,
                path=project_path,
                expected=autoload_name,
                actual=", ".join(sorted(registered_names)) or None,
                note=f"missing Godot autoload '{autoload_name}'",
            )
        )


def _load_godot_autoload_names(project_path: Path) -> set[str]:
    section_name: str | None = None
    autoload_names: set[str] = set()

    for raw_line in project_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith((";", "#")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section_name = stripped[1:-1]
            continue
        if section_name != "autoload" or "=" not in stripped:
            continue
        name, _separator, _value = stripped.partition("=")
        normalized_name = name.strip()
        if normalized_name:
            autoload_names.add(normalized_name)

    return autoload_names


__all__ = ["DriftEntry", "DriftKind", "DriftReport", "detect_drift"]
