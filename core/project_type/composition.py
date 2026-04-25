from __future__ import annotations

from dataclasses import dataclass, replace

from core.project_type.facets import Capability, ProjectFacets


@dataclass(frozen=True, slots=True)
class CompositionConflict:
    name: str
    removed: Capability
    kept: Capability
    reason: str


def apply_composition_rules(
    facets: ProjectFacets,
) -> tuple[ProjectFacets, list[CompositionConflict]]:
    capabilities = set(facets.capabilities)
    conflicts: list[CompositionConflict] = []

    if Capability.capacitor in capabilities and Capability.pwa in capabilities:
        capabilities.remove(Capability.pwa)
        conflicts.append(
            CompositionConflict(
                name="pwa-vs-capacitor",
                removed=Capability.pwa,
                kept=Capability.capacitor,
                reason="capacitor wraps the same SW boundary",
            )
        )

    return replace(facets, capabilities=capabilities), conflicts
