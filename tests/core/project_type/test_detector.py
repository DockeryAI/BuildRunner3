from __future__ import annotations

import json
from typing import TYPE_CHECKING

from core.project_type.composition import CompositionConflict
from core.project_type.detector import detect_facets
from core.project_type.facets import Bundler, Capability, Framework, ProjectFacets

if TYPE_CHECKING:
    from pathlib import Path


def test_detects_react_vite_pwa_supabase(tmp_path: Path) -> None:
    project_path = _write_react_vite_project(
        tmp_path / "react-vite-pwa-supabase",
        dependencies={
            "react": "^19.0.0",
            "@supabase/supabase-js": "^2.0.0",
        },
        dev_dependencies={"vite-plugin-pwa": "^1.0.0"},
        extra_files=("vite.config.ts", "src/sw.ts"),
    )

    facets, report = detect_facets(project_path)

    assert facets == ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={Capability.pwa, Capability.supabase_edge},
    )
    assert report.composition_conflicts == []


def test_detects_react_vite_capacitor_supabase_and_normalizes_pwa(tmp_path: Path) -> None:
    project_path = _write_react_vite_project(
        tmp_path / "react-vite-capacitor-supabase",
        dependencies={
            "react": "^19.0.0",
            "@capacitor/core": "^8.0.0",
            "@supabase/supabase-js": "^2.0.0",
        },
        dev_dependencies={"vite-plugin-pwa": "^1.0.0"},
        extra_files=("vite.config.ts", "src/sw.ts", "capacitor.config.ts"),
    )

    facets, report = detect_facets(project_path)

    assert facets == ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend="supabase",
        capabilities={Capability.capacitor, Capability.supabase_edge},
    )
    assert report.composition_conflicts == [
        CompositionConflict(
            name="pwa-vs-capacitor",
            removed=Capability.pwa,
            kept=Capability.capacitor,
            reason="capacitor wraps the same SW boundary",
        )
    ]


def test_detects_next_supabase(tmp_path: Path) -> None:
    project_path = _write_project(
        tmp_path / "next-supabase",
        package_json={
            "dependencies": {
                "@supabase/supabase-js": "^2.0.0",
            }
        },
        files=("next.config.mjs",),
    )

    facets, _report = detect_facets(project_path)

    assert facets == ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.next,
        backend="supabase",
        capabilities={Capability.supabase_edge},
    )


def test_detects_godot_only(tmp_path: Path) -> None:
    project_path = _write_project(
        tmp_path / "godot-only",
        package_json=None,
        files=("project.godot",),
    )

    facets, _report = detect_facets(project_path)

    assert facets == ProjectFacets(
        framework=Framework.godot,
        bundler=Bundler.godot_editor,
        backend=None,
        capabilities=set(),
    )


def test_detects_expo_only(tmp_path: Path) -> None:
    project_path = _write_project(
        tmp_path / "expo-only",
        package_json={"dependencies": {}},
        files=("eas.json",),
        app_json={"expo": {"name": "Expo Only"}},
    )

    facets, _report = detect_facets(project_path)

    assert facets == ProjectFacets(
        framework=Framework.expo,
        bundler=Bundler.metro,
        backend=None,
        capabilities=set(),
    )


def _write_react_vite_project(
    project_path: Path,
    dependencies: dict[str, str],
    dev_dependencies: dict[str, str],
    extra_files: tuple[str, ...],
) -> Path:
    return _write_project(
        project_path,
        package_json={
            "dependencies": dependencies,
            "devDependencies": dev_dependencies,
        },
        files=extra_files,
    )


def _write_project(
    project_path: Path,
    package_json: dict[str, object] | None,
    files: tuple[str, ...],
    app_json: dict[str, object] | None = None,
) -> Path:
    project_path.mkdir(parents=True)

    if package_json is not None:
        (project_path / "package.json").write_text(json.dumps(package_json), encoding="utf-8")

    if app_json is not None:
        (project_path / "app.json").write_text(json.dumps(app_json), encoding="utf-8")

    for relative_path in files:
        file_path = project_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if relative_path.endswith("/") or relative_path == "supabase/functions":
            file_path.mkdir(parents=True, exist_ok=True)
        else:
            file_path.write_text("// fixture\n", encoding="utf-8")

    return project_path
