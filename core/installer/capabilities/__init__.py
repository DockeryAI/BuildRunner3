"""Opt-in capability installers that layer onto the BR3 baseline and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from core.asset_resolver import resolve_asset_path
from core.project_type.facets import Capability

if TYPE_CHECKING:
    from core.project_type.facets import ProjectFacets


@dataclass(slots=True)
class CapabilityResult:
    """Summarize a capability installation run."""

    name: str
    written: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    package_suggestions: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


class CapabilityConflictError(ValueError):
    """Raised when the requested capability set cannot be installed together."""


def write_template_if_missing(
    *,
    asset_relative_path: str,
    target_path: Path,
    result: CapabilityResult,
) -> None:
    """Copy a packaged template into a repository without overwriting local edits."""
    if target_path.exists():
        result.skipped.append(target_path)
        return

    source_path = resolve_asset_path(asset_relative_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    result.written.append(target_path)


def assert_no_capability_conflicts(declared_facets: ProjectFacets | None) -> None:
    """Validate capability combinations before installation work starts."""
    if declared_facets is None:
        return

    capabilities = declared_facets.capabilities
    if Capability.pwa in capabilities and Capability.capacitor in capabilities:
        raise CapabilityConflictError(
            "Cannot install capability 'capacitor' alongside 'pwa': "
            "capacitor wraps the same service-worker boundary."
        )


def _build_registry() -> dict[Capability, type]:
    return {
        Capability.pwa: import_module(".pwa", __name__).PwaCapability,
        Capability.capacitor: import_module(".capacitor", __name__).CapacitorCapability,
        Capability.supabase_edge: import_module(
            ".supabase_edge",
            __name__,
        ).SupabaseEdgeCapability,
        Capability.dexie_offline: import_module(
            ".dexie_offline",
            __name__,
        ).DexieOfflineCapability,
        Capability.web_push_vapid: import_module(
            ".web_push_vapid",
            __name__,
        ).WebPushVapidCapability,
        Capability.netlify_deploy: import_module(".netlify", __name__).NetlifyCapability,
    }


CAPABILITY_REGISTRY: dict[Capability, type] = _build_registry()
PwaCapability = CAPABILITY_REGISTRY[Capability.pwa]
CapacitorCapability = CAPABILITY_REGISTRY[Capability.capacitor]
SupabaseEdgeCapability = CAPABILITY_REGISTRY[Capability.supabase_edge]
DexieOfflineCapability = CAPABILITY_REGISTRY[Capability.dexie_offline]
WebPushVapidCapability = CAPABILITY_REGISTRY[Capability.web_push_vapid]
NetlifyCapability = CAPABILITY_REGISTRY[Capability.netlify_deploy]


def apply_capabilities(
    target_repo: Path,
    declared_facets: ProjectFacets,
) -> dict[Capability, CapabilityResult]:
    """Install the declared capabilities in a stable order."""
    assert_no_capability_conflicts(declared_facets)

    results: dict[Capability, CapabilityResult] = {}
    for capability in sorted(declared_facets.capabilities, key=lambda item: item.value):
        installer_class = CAPABILITY_REGISTRY.get(capability)
        if installer_class is None:
            continue

        installer = installer_class()
        results[capability] = installer.install(
            Path(target_repo),
            declared_facets=declared_facets,
        )

    return results


__all__ = [
    "CAPABILITY_REGISTRY",
    "CapabilityConflictError",
    "CapabilityResult",
    "CapacitorCapability",
    "DexieOfflineCapability",
    "NetlifyCapability",
    "PwaCapability",
    "SupabaseEdgeCapability",
    "WebPushVapidCapability",
    "apply_capabilities",
    "assert_no_capability_conflicts",
    "write_template_if_missing",
]
