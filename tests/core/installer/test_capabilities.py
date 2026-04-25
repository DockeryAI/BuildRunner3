from __future__ import annotations

import pytest

from core.installer.capabilities import (
    CAPABILITY_REGISTRY,
    CapabilityConflictError,
    CapacitorCapability,
    DexieOfflineCapability,
    NetlifyCapability,
    PwaCapability,
    SupabaseEdgeCapability,
    WebPushVapidCapability,
    apply_capabilities,
)
from core.project_type.facets import Bundler, Capability, Framework, ProjectFacets


@pytest.mark.parametrize(
    ("installer", "expected_paths"),
    [
        (PwaCapability(), ("src/sw.ts",)),
        (
            CapacitorCapability(),
            (
                "capacitor.config.ts",
                "src/captures/capacitor/BRLoggerCapacitor.tsx",
                "src/captures/capacitor/capacitorCapture.ts",
            ),
        ),
        (
            SupabaseEdgeCapability(),
            ("supabase/functions/_shared/devLog.ts",),
        ),
        (DexieOfflineCapability(), ("src/db.ts",)),
        (WebPushVapidCapability(), ("src/components/PushDebug.tsx",)),
        (NetlifyCapability(), ("netlify.toml",)),
    ],
)
def test_each_capability_installs_files_and_reinstall_is_noop(
    tmp_path,
    installer,
    expected_paths: tuple[str, ...],
) -> None:
    project = tmp_path / installer.name
    project.mkdir()

    result = installer.install(project)

    for relative_path in expected_paths:
        path = project / relative_path
        assert path.is_file()
        assert path.read_text(encoding="utf-8").strip() != ""

    assert result.name == installer.name
    assert result.written == [project / relative_path for relative_path in expected_paths]

    second_result = installer.install(project)

    assert second_result.written == []
    assert second_result.skipped == [project / relative_path for relative_path in expected_paths]


def test_apply_capabilities_raises_on_capacitor_and_pwa_conflict(tmp_path) -> None:
    project = tmp_path / "conflict"
    project.mkdir()
    facets = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={Capability.pwa, Capability.capacitor},
    )

    with pytest.raises(CapabilityConflictError, match=r"capacitor.*pwa|pwa.*capacitor"):
        apply_capabilities(project, facets)


def test_supabase_edge_adds_device_logs_note_when_capacitor_is_declared(tmp_path) -> None:
    project = tmp_path / "supabase-edge"
    project.mkdir()
    facets = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={Capability.supabase_edge, Capability.capacitor},
    )

    result = SupabaseEdgeCapability().install(project, declared_facets=facets)

    assert any("device_logs" in note for note in result.notes)


def test_pwa_trailsync_style_fixture_writes_sw_with_inject_manifest(tmp_path) -> None:
    project = tmp_path / "trailsync"
    project.mkdir()

    result = PwaCapability().install(project)
    sw_path = project / "src" / "sw.ts"

    assert sw_path.is_file()
    assert "injectManifest" in sw_path.read_text(encoding="utf-8")
    assert result.package_suggestions == {"vite-plugin-pwa": "^0.21"}


def test_capacitor_phatti_style_fixture_succeeds_without_pwa_requested(tmp_path) -> None:
    project = tmp_path / "phatti"
    project.mkdir()
    facets = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={Capability.capacitor},
    )

    result = CapacitorCapability().install(project, declared_facets=facets)

    assert result.written
    assert (project / "capacitor.config.ts").is_file()
    assert result.package_suggestions == {
        "@capacitor/core": "^8",
        "@capacitor/cli": "^8",
        "@capacitor/ios": "^8",
    }


def test_capability_registry_exposes_phase_7_installers() -> None:
    assert {
        Capability.pwa: PwaCapability,
        Capability.capacitor: CapacitorCapability,
        Capability.supabase_edge: SupabaseEdgeCapability,
        Capability.dexie_offline: DexieOfflineCapability,
        Capability.web_push_vapid: WebPushVapidCapability,
        Capability.netlify_deploy: NetlifyCapability,
    } == CAPABILITY_REGISTRY
