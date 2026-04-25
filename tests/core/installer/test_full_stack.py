"""Tests for the install_full_stack helper used by br init / br attach."""

from __future__ import annotations

from pathlib import Path

from core.installer import install_full_stack
from core.installer.drift_detector import detect_drift
from core.project_type.facets import Bundler, Capability, Framework, ProjectFacets


def _write_godot_fixture(project_root: Path) -> None:
    project_root.mkdir(parents=True)
    (project_root / "project.godot").write_text(
        "; Engine configuration file.\n"
        "config_version=5\n\n"
        "[application]\n"
        'config/name="FullStackGame"\n',
        encoding="utf-8",
    )
    (project_root / ".git").mkdir()


def _write_react_vite_fixture(project_root: Path) -> None:
    project_root.mkdir(parents=True)
    (project_root / "package.json").write_text(
        '{"name": "fs-app", "dependencies": {"react": "^18", "vite": "^5"}}\n',
        encoding="utf-8",
    )
    (project_root / "vite.config.ts").write_text("export default {};\n", encoding="utf-8")
    (project_root / "src").mkdir()
    (project_root / "src" / "main.tsx").write_text(
        "import React from 'react';\nReact.render(null, document.body);\n",
        encoding="utf-8",
    )
    (project_root / ".git").mkdir()


def test_install_full_stack_godot_clean_after_one_call(tmp_path: Path) -> None:
    project = tmp_path / "godot-game"
    _write_godot_fixture(project)

    result = install_full_stack(project)

    assert result.facets is not None
    assert result.facets.framework is Framework.godot
    assert result.baseline is not None
    assert result.adapter is not None
    assert result.hooks is not None

    audit = detect_drift(project)
    assert audit.has_drift is False, [
        (e.kind.value, str(e.path)) for e in audit.entries
    ]


def test_install_full_stack_is_idempotent(tmp_path: Path) -> None:
    project = tmp_path / "godot-idempotent"
    _write_godot_fixture(project)

    install_full_stack(project)
    second = install_full_stack(project)

    assert second.adapter is not None
    assert second.adapter.written == []
    audit = detect_drift(project)
    assert audit.has_drift is False


def test_install_full_stack_dry_run_writes_nothing(tmp_path: Path) -> None:
    project = tmp_path / "dry-run"
    _write_godot_fixture(project)

    result = install_full_stack(project, dry_run=True)

    assert result.baseline is None
    assert result.adapter is None
    assert result.hooks is None
    assert any("dry-run" in note for note in result.notes)
    assert not (project / ".buildrunner" / "agents.json").exists()
    assert not (project / "scripts" / "autoloads" / "BRLogger.gd").exists()


def test_install_full_stack_react_vite_with_capability(tmp_path: Path) -> None:
    project = tmp_path / "react-vite-app"
    _write_react_vite_fixture(project)

    declared = ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend=None,
        capabilities=frozenset({Capability.dexie_offline}),
    )
    result = install_full_stack(project, declared_facets=declared)

    assert result.adapter is not None
    assert (project / "src" / "components" / "BRLogger.tsx").exists()
    assert Capability.dexie_offline in result.capabilities
    assert (project / "src" / "db.ts").exists()
