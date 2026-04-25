from __future__ import annotations

import json

from core.asset_resolver import resolve_asset_path
from core.installer.core_baseline import CoreBaselineInstaller


def test_install_core_baseline_on_empty_project(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    result = CoreBaselineInstaller().install(project)

    buildrunner_dir = project / ".buildrunner"
    expected_files = (
        buildrunner_dir / "agents.json",
        buildrunner_dir / "skill-state.json",
        buildrunner_dir / "behavior.yaml",
        buildrunner_dir / "orchestration_state.json",
        buildrunner_dir / "runtime.json",
        buildrunner_dir / "bypass-justification.md",
        buildrunner_dir / "scripts" / "log-rotation.sh",
        project / "CLAUDE.md",
    )
    for path in expected_files:
        assert path.is_file()

    expected_dirs = (
        buildrunner_dir / "plans",
        buildrunner_dir / "codex-briefs",
        buildrunner_dir / "fixit-briefs",
        buildrunner_dir / "adversarial-reviews",
        buildrunner_dir / "validation",
        buildrunner_dir / "verification",
        buildrunner_dir / "reviews",
        buildrunner_dir / "prompts-golden",
        buildrunner_dir / "mockups",
        buildrunner_dir / "specs",
        buildrunner_dir / "design",
        buildrunner_dir / "decisions",
    )
    for path in expected_dirs:
        assert path.is_dir()

    assert set(result.created_dirs) >= set(expected_dirs)


def test_install_core_baseline_is_noop_on_reinstall(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    CoreBaselineInstaller().install(project)
    second_result = CoreBaselineInstaller().install(project)

    assert second_result.written == []
    assert second_result.merged == []
    assert second_result.created_dirs == []


def test_install_core_baseline_preserves_custom_structured_keys(tmp_path) -> None:
    project = tmp_path / "project"
    buildrunner_dir = project / ".buildrunner"
    buildrunner_dir.mkdir(parents=True)
    agents_path = buildrunner_dir / "agents.json"
    agents_path.write_text(
        json.dumps({"agents": [], "version": 1, "custom_key": "preserved"}, indent=2) + "\n",
        encoding="utf-8",
    )

    result = CoreBaselineInstaller().install(project)
    agents_data = json.loads(agents_path.read_text(encoding="utf-8"))

    assert agents_data["custom_key"] == "preserved"
    assert agents_data["agents"] == []
    assert agents_data["version"] == 1
    assert agents_path not in result.merged


def test_install_core_baseline_does_not_override_existing_runtime_default(tmp_path) -> None:
    project = tmp_path / "project"
    buildrunner_dir = project / ".buildrunner"
    buildrunner_dir.mkdir(parents=True)
    runtime_path = buildrunner_dir / "runtime.json"
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": "br3.runtime.config.v1",
                "default_runtime": "claude",
                "custom_key": "preserved",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    CoreBaselineInstaller().install(project)
    runtime_data = json.loads(runtime_path.read_text(encoding="utf-8"))

    assert runtime_data["default_runtime"] == "claude"
    assert runtime_data["custom_key"] == "preserved"


def test_install_core_baseline_writes_suggested_claude_when_project_claude_exists(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    project_claude = project / "CLAUDE.md"
    project_claude.write_text("repo-specific guidance\n", encoding="utf-8")

    CoreBaselineInstaller().install(project)

    suggested_path = project / "CLAUDE.md.br3-suggested"
    assert project_claude.read_text(encoding="utf-8") == "repo-specific guidance\n"
    assert suggested_path.read_text(encoding="utf-8") == resolve_asset_path(
        "templates/core-baseline/CLAUDE.md.universal"
    ).read_text(encoding="utf-8")
