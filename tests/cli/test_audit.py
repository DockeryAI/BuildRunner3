from __future__ import annotations

import argparse
import json

from cli.audit_commands import register, run
from cli.upgrade_commands import apply_attach_upgrade
from core.installer.drift_detector import DriftKind, detect_drift
from core.project_type.facets import Bundler, Framework, ProjectFacets


def test_audit_reports_missing_baseline_files_on_broken_react_vite_fixture(
    tmp_path,
    capsys,
) -> None:
    project = _write_minimal_react_package(tmp_path / "broken-react-vite")
    parser = _build_parser()
    args = parser.parse_args(["audit", str(project)])

    exit_code = run(args)
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Drift detected:" in output
    assert "missing_file" in output
    assert str(project / ".buildrunner" / "agents.json") in output
    assert str(project / "CLAUDE.md") in output


def test_apply_attach_upgrade_fixes_baseline_and_adapter_drift(tmp_path) -> None:
    project = _write_minimal_react_package(tmp_path / "upgrade-react-vite")
    facets = _react_vite_facets()

    report = apply_attach_upgrade(project, declared_facets=facets, interactive=False)
    redetected = detect_drift(project, declared_facets=facets)

    assert report.errors == []
    assert report.applied
    assert redetected.has_drift is False


def test_apply_attach_upgrade_is_idempotent_once_drift_is_fixed(tmp_path) -> None:
    project = _write_minimal_react_package(tmp_path / "idempotent-react-vite")
    facets = _react_vite_facets()

    apply_attach_upgrade(project, declared_facets=facets, interactive=False)
    second_report = apply_attach_upgrade(project, declared_facets=facets, interactive=False)

    assert second_report.applied == []
    assert second_report.errors == []


def test_detects_and_repairs_godot_autoload_drift(tmp_path) -> None:
    project = tmp_path / "godot-drift"
    project.mkdir()
    (project / "project.godot").write_text(
        "; Engine configuration file.\n"
        "config_version=5\n\n"
        "[autoload]\n"
        'BRLogger="*res://scripts/autoloads/BRLogger.gd"\n\n'
        "[application]\n"
        'config/name="Fixture"\n',
        encoding="utf-8",
    )

    report = detect_drift(project)
    missing_autoloads = {entry.expected for entry in report.entries if entry.kind is DriftKind.MISSING_AUTOLOAD}
    upgrade_report = apply_attach_upgrade(project, interactive=False)
    repaired = detect_drift(project)
    project_text = (project / "project.godot").read_text(encoding="utf-8")

    assert missing_autoloads == {"GameState", "EventBus", "SaveManager"}
    assert upgrade_report.errors == []
    assert repaired.has_drift is False
    assert 'BRLogger="*res://scripts/autoloads/BRLogger.gd"' in project_text
    assert 'GameState="*res://scripts/autoloads/GameState.gd"' in project_text
    assert 'EventBus="*res://scripts/autoloads/EventBus.gd"' in project_text
    assert 'SaveManager="*res://scripts/autoloads/SaveManager.gd"' in project_text


def test_audit_json_output_uses_expected_schema(tmp_path, capsys) -> None:
    project = _write_minimal_react_package(tmp_path / "json-react-vite")
    parser = _build_parser()
    args = parser.parse_args(["audit", str(project), "--json"])

    exit_code = run(args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert isinstance(payload, list)
    assert payload
    assert set(payload[0]) == {"kind", "path", "expected", "actual", "note"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    register(subparsers)
    return parser


def _react_vite_facets() -> ProjectFacets:
    return ProjectFacets(
        framework=Framework.react,
        bundler=Bundler.vite,
        backend=None,
        capabilities=set(),
    )


def _write_minimal_react_package(project) -> object:
    project.mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"vite": "^5.0.0"},
            }
        ),
        encoding="utf-8",
    )
    return project
