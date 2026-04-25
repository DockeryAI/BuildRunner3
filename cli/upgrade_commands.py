"""Upgrade packaged BuildRunner assets and repair attach drift."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from core.asset_resolver import install_legacy_attach_stub, sync_packaged_templates
from core.installer import CoreBaselineInstaller, install_hooks
from core.installer.adapters import expo, react_vite
from core.installer.adapters import next as next_adapter
from core.installer.adapters.godot import (
    GODOT_EXPECTED_FILES,
    GodotAdapter,
    verify_zshrc_br_project_helper,
)
from core.installer.adapters.next import NEXT_EXPECTED_FILES
from core.installer.capabilities import CAPABILITY_EXPECTED_FILES, CAPABILITY_REGISTRY
from core.installer.drift_detector import DriftEntry, DriftKind, detect_drift
from core.project_type.facets import Bundler, Framework, ProjectFacets

if TYPE_CHECKING:
    from collections.abc import Callable

console = Console()

_HENGE_ALIAS_START = "# >>> br3-henge-alias >>>"
_HENGE_ALIAS_END = "# <<< br3-henge-alias <<<"


@dataclass(slots=True)
class InstallResult:
    installed: bool
    path: Path
    note: str


@dataclass(slots=True)
class UpgradeReport:
    applied: list[DriftEntry] = field(default_factory=list)
    skipped: list[DriftEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"applied={len(self.applied)} skipped={len(self.skipped)} "
            f"errors={len(self.errors)}"
        )


def run_upgrade() -> None:
    """Sync packaged templates to ~/.buildrunner/templates and retire legacy br-attach."""
    try:
        template_result = sync_packaged_templates()
        attach_result = install_legacy_attach_stub()
    except Exception as exc:
        console.print(f"[red]❌ Upgrade failed: {exc}[/red]")
        raise typer.Exit(1) from exc

    written = len(template_result.written)
    skipped = len(template_result.skipped)

    if written:
        console.print(
            f"[green]✅ Synced {written} template file(s) to ~/.buildrunner/templates[/green]"
        )
    else:
        console.print("[dim]Templates already up to date in ~/.buildrunner/templates[/dim]")

    if skipped:
        console.print(f"[dim]Skipped {skipped} unchanged template file(s)[/dim]")

    if attach_result.changed and attach_result.backup_path is not None:
        console.print(
            f"[yellow]⚠️  Moved legacy br-attach to {attach_result.backup_path}[/yellow]"
        )
    elif attach_result.stub_path is not None:
        console.print("[dim]Legacy br-attach stub already installed[/dim]")


def upgrade_command() -> None:
    run_upgrade()


def install_henge_alias(
    *,
    project_path: Path,
    zshrc_path: Path | None = None,
    dry_run: bool = False,
) -> InstallResult:
    path = Path.home() / ".zshrc" if zshrc_path is None else Path(zshrc_path)
    if not verify_zshrc_br_project_helper(path):
        return InstallResult(
            installed=False,
            path=path,
            note="_br_project helper missing — run br upgrade first",
        )

    block = _render_henge_alias_block(Path(project_path))
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if _HENGE_ALIAS_START in existing and _HENGE_ALIAS_END in existing:
        return InstallResult(
            installed=False,
            path=path,
            note="henge alias already installed",
        )

    if dry_run:
        return InstallResult(
            installed=False,
            path=path,
            note=f"would install henge alias for {Path(project_path)}",
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    separator = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(existing + separator + block, encoding="utf-8")
    return InstallResult(
        installed=True,
        path=path,
        note="henge alias installed",
    )


def apply_attach_upgrade(
    target_repo: Path,
    *,
    declared_facets: ProjectFacets | None = None,
    interactive: bool = False,
) -> UpgradeReport:
    repo_root = Path(target_repo).resolve()
    drift_report = detect_drift(repo_root, declared_facets=declared_facets)
    facets = drift_report.facets
    if facets is None:
        return UpgradeReport(errors=[f"Could not determine facets for {repo_root}"])

    selected: list[DriftEntry] = []
    skipped: list[DriftEntry] = []
    for entry in drift_report.entries:
        if interactive and not _confirm_apply(entry):
            skipped.append(entry)
            continue
        selected.append(entry)

    grouped_entries: dict[str, list[DriftEntry]] = {}
    grouped_fixers: dict[str, Callable[[], None]] = {}
    for entry in selected:
        fix = _resolve_fix(entry, repo_root, facets)
        if fix is None:
            skipped.append(entry)
            continue
        key, apply_fix = fix
        grouped_entries.setdefault(key, []).append(entry)
        grouped_fixers.setdefault(key, apply_fix)

    applied: list[DriftEntry] = []
    errors: list[str] = []
    for key, apply_fix in grouped_fixers.items():
        try:
            apply_fix()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{key}: {exc}")
            continue
        applied.extend(grouped_entries[key])

    return UpgradeReport(applied=applied, skipped=skipped, errors=errors)


def _confirm_apply(entry: DriftEntry) -> bool:
    response = input(f"Apply {entry.kind.value} fix for {entry.path}? [y/N]: ")
    return response.strip().lower() in {"y", "yes"}


def _resolve_fix(
    entry: DriftEntry,
    repo_root: Path,
    facets: ProjectFacets,
) -> tuple[str, Callable[[], None]] | None:
    relative_path = entry.path.resolve().relative_to(repo_root)
    baseline_paths = set(CoreBaselineInstaller.expected_files())

    if entry.kind is DriftKind.MISSING_CONFIG_KEY or relative_path in baseline_paths:
        return (
            "baseline",
            lambda: CoreBaselineInstaller().install(repo_root, declared_facets=facets),
        )

    if entry.kind is DriftKind.MISSING_HOOK:
        return ("hooks", lambda: install_hooks(repo_root))

    if entry.kind is DriftKind.MISSING_AUTOLOAD or relative_path in set(GODOT_EXPECTED_FILES):
        return ("adapter:godot", lambda: GodotAdapter().install(repo_root))

    adapter_key = _adapter_fix_key(repo_root, relative_path, facets)
    if adapter_key is not None:
        return adapter_key

    for capability, expected_paths in CAPABILITY_EXPECTED_FILES.items():
        if relative_path not in expected_paths or capability not in facets.capabilities:
            continue
        installer_class = CAPABILITY_REGISTRY[capability]
        return (
            f"capability:{capability.value}",
            lambda installer_class=installer_class: installer_class().install(
                repo_root,
                declared_facets=facets,
            ),
        )

    return None


def _adapter_fix_key(
    repo_root: Path,
    relative_path: Path,
    facets: ProjectFacets,
) -> tuple[str, Callable[[], None]] | None:
    if (
        facets.framework is Framework.react
        and facets.bundler is Bundler.vite
        and relative_path in set(react_vite.REACT_VITE_EXPECTED_FILES)
    ):
        return ("adapter:react-vite", lambda: react_vite.install(repo_root))

    if facets.framework is Framework.react and facets.bundler is Bundler.next:
        expected_paths = set(_next_expected_files(repo_root))
        if relative_path in expected_paths:
            return ("adapter:next", lambda: next_adapter.install(repo_root))

    if facets.framework is Framework.expo and relative_path in set(expo.EXPO_EXPECTED_FILES):
        return ("adapter:expo", lambda: expo.install(repo_root))

    return None


def _next_expected_files(repo_root: Path) -> tuple[Path, ...]:
    if (repo_root / "app").is_dir() or not (repo_root / "pages").is_dir():
        return NEXT_EXPECTED_FILES
    return (Path("components/BRLoggerNext.tsx"), NEXT_EXPECTED_FILES[1])


def _render_henge_alias_block(project_path: Path) -> str:
    return (
        f"{_HENGE_ALIAS_START}\n"
        f"alias henge='_br_project {project_path}'\n"
        f"{_HENGE_ALIAS_END}\n"
    )


__all__ = [
    "InstallResult",
    "UpgradeReport",
    "apply_attach_upgrade",
    "install_henge_alias",
    "run_upgrade",
    "upgrade_command",
]
