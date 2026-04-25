from __future__ import annotations

from core.project_type.composition import CompositionConflict, apply_composition_rules
from core.project_type.facets import Bundler, Capability, Framework, ProjectFacets


def test_reference_projects_are_expressible_as_project_facets() -> None:
    synapse = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={
            Capability.pwa,
            Capability.supabase_edge,
            Capability.web_push_vapid,
        },
    )
    trailsync = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={
            Capability.pwa,
            Capability.dexie_offline,
            Capability.supabase_edge,
        },
    )
    phatti = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={Capability.capacitor, Capability.supabase_edge},
    )
    henge_wars = ProjectFacets(
        framework=Framework.godot,
        bundler=Bundler.godot_editor,
        backend=None,
        capabilities=set(),
    )

    assert synapse.framework is Framework.react
    assert trailsync.bundler is Bundler.vite
    assert phatti.capabilities == {
        Capability.capacitor,
        Capability.supabase_edge,
    }
    assert henge_wars.to_dict() == {
        "framework": "godot",
        "bundler": "godot_editor",
        "backend": None,
        "capabilities": [],
    }


def test_apply_composition_rules_removes_pwa_when_capacitor_present() -> None:
    facets = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={Capability.capacitor, Capability.pwa, Capability.supabase_edge},
    )

    normalized, conflicts = apply_composition_rules(facets)

    assert normalized.capabilities == {
        Capability.capacitor,
        Capability.supabase_edge,
    }
    assert facets.capabilities == {
        Capability.capacitor,
        Capability.pwa,
        Capability.supabase_edge,
    }
    assert conflicts == [
        CompositionConflict(
            name="pwa-vs-capacitor",
            removed=Capability.pwa,
            kept=Capability.capacitor,
            reason="capacitor wraps the same SW boundary",
        )
    ]


def test_to_dict_serializes_enums_and_sorts_capabilities() -> None:
    facets = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={
            Capability.web_push_vapid,
            Capability.capacitor,
            Capability.supabase_edge,
        },
    )

    assert facets.to_dict() == {
        "framework": "react",
        "bundler": "vite",
        "backend": "supabase",
        "capabilities": ["capacitor", "supabase_edge", "web_push_vapid"],
    }


def test_str_is_deterministic_with_sorted_capabilities() -> None:
    facets = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={
            Capability.web_push_vapid,
            Capability.capacitor,
            Capability.supabase_edge,
        },
    )

    expected = (
        "framework=react bundler=vite backend=supabase "
        "capabilities=[capacitor,supabase_edge,web_push_vapid]"
    )

    assert str(facets) == expected
    assert str(facets) == expected
