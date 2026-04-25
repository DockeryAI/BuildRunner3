from __future__ import annotations

import stat

from core.installer.adapters.godot import GodotAdapter, verify_zshrc_br_project_helper


def test_install_godot_adapter_and_reinstall_is_noop(tmp_path) -> None:
    project = _write_godot_project(tmp_path / "godot-fixture")
    original_application_section = b'[application]\nconfig/name="Test"\n'

    result = GodotAdapter().install(project)

    expected_paths = (
        project / "scripts" / "autoloads" / "BRLogger.gd",
        project / "scripts" / "autoloads" / "GameState.gd",
        project / "scripts" / "autoloads" / "EventBus.gd",
        project / "scripts" / "autoloads" / "SaveManager.gd",
        project / "scripts" / "godot-run.sh",
        project / "scripts" / "godot-test.sh",
        project / "CLAUDE.md.godot-addendum",
        project / "Makefile",
    )
    for path in expected_paths:
        assert path.is_file()

    assert not (project / "scripts" / "autoloads" / "GameState.gd.template").exists()
    assert not (project / "scripts" / "autoloads" / "EventBus.gd.template").exists()
    assert not (project / "scripts" / "autoloads" / "SaveManager.gd.template").exists()

    run_mode = (project / "scripts" / "godot-run.sh").stat().st_mode
    test_mode = (project / "scripts" / "godot-test.sh").stat().st_mode
    assert run_mode & stat.S_IXUSR
    assert test_mode & stat.S_IXUSR

    makefile_text = (project / "Makefile").read_text(encoding="utf-8")
    assert makefile_text.count("# >>> br3-godot-targets >>>") == 1
    assert makefile_text.count("# <<< br3-godot-targets <<<") == 1
    assert "run-logged:" in makefile_text
    assert "test-logged:" in makefile_text
    assert "logs-clean:" in makefile_text

    project_text = (project / "project.godot").read_text(encoding="utf-8")
    assert "[autoload]" in project_text
    assert 'BRLogger="*res://scripts/autoloads/BRLogger.gd"' in project_text
    assert 'GameState="*res://scripts/autoloads/GameState.gd"' in project_text
    assert 'EventBus="*res://scripts/autoloads/EventBus.gd"' in project_text
    assert 'SaveManager="*res://scripts/autoloads/SaveManager.gd"' in project_text
    assert original_application_section in (project / "project.godot").read_bytes()
    assert project / "project.godot" in result.written

    second_result = GodotAdapter().install(project)
    project_text_again = (project / "project.godot").read_text(encoding="utf-8")
    assert second_result.written == []
    assert project_text_again.count("[autoload]") == 1
    assert project_text_again.count('BRLogger="*res://scripts/autoloads/BRLogger.gd"') == 1
    assert project_text_again.count('GameState="*res://scripts/autoloads/GameState.gd"') == 1
    assert project_text_again.count('EventBus="*res://scripts/autoloads/EventBus.gd"') == 1
    assert project_text_again.count('SaveManager="*res://scripts/autoloads/SaveManager.gd"') == 1
    assert (project / "Makefile").read_text(encoding="utf-8").count(
        "# >>> br3-godot-targets >>>"
    ) == 1


def test_install_godot_adapter_without_project_is_noop(tmp_path) -> None:
    project = tmp_path / "not-godot"
    project.mkdir()

    result = GodotAdapter().install(project)

    assert result.written == []
    assert result.skipped == []
    assert result.notes == ["no project.godot found; skipping"]


def test_verify_zshrc_br_project_helper(tmp_path) -> None:
    with_helper = tmp_path / "with-helper.zshrc"
    with_helper.write_text(
        'export PATH="$HOME/bin:$PATH"\n\n_br_project() {\n  echo hello\n}\n',
        encoding="utf-8",
    )
    without_helper = tmp_path / "without-helper.zshrc"
    without_helper.write_text("alias ll='ls -la'\n", encoding="utf-8")

    assert verify_zshrc_br_project_helper(with_helper) is True
    assert verify_zshrc_br_project_helper(without_helper) is False
    assert verify_zshrc_br_project_helper(tmp_path / "missing.zshrc") is False


def _write_godot_project(project_path) -> object:
    project_path.mkdir(parents=True)
    (project_path / "project.godot").write_text(
        "; Engine configuration file.\n"
        "config_version=5\n\n"
        "[application]\n"
        'config/name="Test"\n',
        encoding="utf-8",
    )
    return project_path
