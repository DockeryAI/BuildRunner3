"""Project-type facets for installer composition.

`Framework.expo` identifies a project built on the managed Expo app model.
`Capability.expo_native` is narrower: it signals that the project uses the EAS
native build pipeline. A project can be `Framework.expo` without advertising
`Capability.expo_native`, and non-Expo projects should not use the framework
tag as a proxy for native build behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Framework(StrEnum):
    react = "react"
    vue = "vue"
    svelte = "svelte"
    vanilla = "vanilla"
    godot = "godot"
    expo = "expo"
    unknown = "unknown"


class Bundler(StrEnum):
    vite = "vite"
    next = "next"
    remix = "remix"
    astro = "astro"
    sveltekit = "sveltekit"
    metro = "metro"
    godot_editor = "godot_editor"
    none = "none"


class Capability(StrEnum):
    pwa = "pwa"
    capacitor = "capacitor"
    expo_native = "expo_native"
    web_push_vapid = "web_push_vapid"
    dexie_offline = "dexie_offline"
    react_query_persist = "react_query_persist"
    supabase_edge = "supabase_edge"
    netlify_deploy = "netlify_deploy"
    electron = "electron"
    tauri = "tauri"


@dataclass(slots=True)
class ProjectFacets:
    framework: Framework
    bundler: Bundler
    backend: str | None
    capabilities: set[Capability] = field(default_factory=set)

    def sorted_capabilities(self) -> list[Capability]:
        return sorted(self.capabilities, key=lambda capability: capability.value)

    def to_dict(self) -> dict[str, str | None | list[str]]:
        return {
            "framework": self.framework.value,
            "bundler": self.bundler.value,
            "backend": self.backend,
            "capabilities": [capability.value for capability in self.sorted_capabilities()],
        }

    def __str__(self) -> str:
        capabilities = ",".join(
            capability.value for capability in self.sorted_capabilities()
        )
        return (
            f"framework={self.framework.value} "
            f"bundler={self.bundler.value} "
            f"backend={self.backend} "
            f"capabilities=[{capabilities}]"
        )
