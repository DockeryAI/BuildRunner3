"""Installer utilities for BuildRunner project setup."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .core_baseline import CoreBaselineInstaller, CoreBaselineResult
from .hook_installer import HookInstallResult, install_hooks

if TYPE_CHECKING:
    from core.installer.adapters import AdapterResult
    from core.installer.capabilities import CapabilityResult
    from core.project_type.facets import Capability, ProjectFacets


@dataclass(slots=True)
class FullStackResult:
    """Outcome of running the full BR3 install stack on a project."""

    facets: ProjectFacets | None = None
    baseline: CoreBaselineResult | None = None
    hooks: HookInstallResult | None = None
    adapter: AdapterResult | None = None
    capabilities: dict[Capability, CapabilityResult] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def install_full_stack(
    target_repo: Path,
    *,
    declared_facets: ProjectFacets | None = None,
    dry_run: bool = False,
) -> FullStackResult:
    """Run baseline + hooks + framework adapter + capabilities in one shot.

    Used by ``br init`` and the default ``br attach <directory>`` flow so that
    every fresh project gets the full BR3 stack — not just the baseline.
    All underlying installers are skip-if-exists / idempotent.
    """
    from core.installer.adapters import expo as expo_adapter
    from core.installer.adapters import godot as godot_adapter
    from core.installer.adapters import next as next_adapter
    from core.installer.adapters import react_vite as react_vite_adapter
    from core.installer.capabilities import apply_capabilities
    from core.project_type.facets import Bundler, Framework
    from core.retrofit.codebase_scanner import CodebaseScanner

    repo_root = Path(target_repo).resolve()
    result = FullStackResult()

    if dry_run:
        result.notes.append("dry-run: no writes performed")
        if declared_facets is None:
            facets, _detection = CodebaseScanner(repo_root).detect_facets()
            result.facets = facets
        else:
            result.facets = declared_facets
        return result

    result.baseline = CoreBaselineInstaller().install(
        repo_root,
        declared_facets=declared_facets,
    )

    if (repo_root / ".git").is_dir():
        result.hooks = install_hooks(repo_root)
    else:
        result.notes.append("no .git directory — hooks skipped")

    if declared_facets is None:
        facets, _detection = CodebaseScanner(repo_root).detect_facets()
    else:
        facets = declared_facets
    result.facets = facets

    adapter_install = None
    if facets.framework is Framework.godot:
        adapter_install = godot_adapter.install
    elif facets.framework is Framework.expo:
        adapter_install = expo_adapter.install
    elif facets.framework is Framework.react and facets.bundler is Bundler.vite:
        adapter_install = react_vite_adapter.install
    elif facets.framework is Framework.react and facets.bundler is Bundler.next:
        adapter_install = next_adapter.install
    else:
        result.notes.append(
            f"no framework adapter for {facets.framework}/{facets.bundler}",
        )

    if adapter_install is not None:
        result.adapter = adapter_install(repo_root)

    if facets.capabilities:
        result.capabilities = apply_capabilities(repo_root, facets)

    return result


__all__ = [
    "CoreBaselineInstaller",
    "CoreBaselineResult",
    "FullStackResult",
    "HookInstallResult",
    "install_full_stack",
    "install_hooks",
]
