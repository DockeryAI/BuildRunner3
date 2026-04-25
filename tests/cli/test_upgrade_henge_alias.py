from __future__ import annotations

from pathlib import Path

from cli.upgrade_commands import install_henge_alias


def test_install_henge_alias_requires_br_project_helper(tmp_path) -> None:
    zshrc_path = tmp_path / "missing-helper.zshrc"
    zshrc_path.write_text("alias ll='ls -la'\n", encoding="utf-8")

    result = install_henge_alias(
        project_path=Path("/Users/byronhudson/Projects/HengeWars"),
        zshrc_path=zshrc_path,
    )

    assert result.installed is False
    assert "_br_project helper missing" in result.note


def test_install_henge_alias_writes_marker_block_when_helper_is_present(tmp_path) -> None:
    zshrc_path = _write_helper_zshrc(tmp_path / "with-helper.zshrc")

    result = install_henge_alias(
        project_path=Path("/Users/byronhudson/Projects/HengeWars"),
        zshrc_path=zshrc_path,
    )
    contents = zshrc_path.read_text(encoding="utf-8")

    assert result.installed is True
    assert contents.endswith(
        "# >>> br3-henge-alias >>>\n"
        "alias henge='_br_project /Users/byronhudson/Projects/HengeWars'\n"
        "# <<< br3-henge-alias <<<\n"
    )


def test_install_henge_alias_is_noop_when_marker_block_exists(tmp_path) -> None:
    zshrc_path = _write_helper_zshrc(tmp_path / "already-installed.zshrc")
    install_henge_alias(
        project_path=Path("/Users/byronhudson/Projects/HengeWars"),
        zshrc_path=zshrc_path,
    )
    original = zshrc_path.read_text(encoding="utf-8")

    result = install_henge_alias(
        project_path=Path("/Users/byronhudson/Projects/HengeWars"),
        zshrc_path=zshrc_path,
    )

    assert result.installed is False
    assert result.note == "henge alias already installed"
    assert zshrc_path.read_text(encoding="utf-8") == original


def test_install_henge_alias_dry_run_does_not_write(tmp_path) -> None:
    zshrc_path = _write_helper_zshrc(tmp_path / "dry-run.zshrc")
    original = zshrc_path.read_text(encoding="utf-8")

    result = install_henge_alias(
        project_path=Path("/Users/byronhudson/Projects/HengeWars"),
        zshrc_path=zshrc_path,
        dry_run=True,
    )

    assert result.installed is False
    assert "would install henge alias" in result.note
    assert zshrc_path.read_text(encoding="utf-8") == original


def test_install_henge_alias_uses_custom_project_path_verbatim(tmp_path) -> None:
    zshrc_path = _write_helper_zshrc(tmp_path / "custom-path.zshrc")

    install_henge_alias(
        project_path=Path("/workspace/some-other-game"),
        zshrc_path=zshrc_path,
    )

    assert "alias henge='_br_project /workspace/some-other-game'" in zshrc_path.read_text(
        encoding="utf-8"
    )


def _write_helper_zshrc(path: Path) -> Path:
    path.write_text(
        'export PATH="$HOME/bin:$PATH"\n\n_br_project() {\n  echo hello\n}\n',
        encoding="utf-8",
    )
    return path
