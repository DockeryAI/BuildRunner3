from __future__ import annotations

from core.asset_resolver import resolve_asset_path


def test_resolve_asset_path_finds_packaged_template_for_pipx_style_install(
    tmp_path, monkeypatch
):
    package_root = tmp_path / "site-packages" / "pipx_assets"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("")
    (package_root / "templates").mkdir()
    packaged_template = package_root / "templates" / "example.txt"
    packaged_template.write_text("packaged")

    monkeypatch.syspath_prepend(str(tmp_path / "site-packages"))

    resolved = resolve_asset_path(
        "templates/example.txt",
        overlay_root=tmp_path / "overlay",
        repo_root=tmp_path / "repo",
        package_names=("pipx_assets",),
        cache_root=tmp_path / "cache",
    )

    assert resolved == packaged_template
    assert resolved.read_text() == "packaged"


def test_resolve_asset_path_finds_repo_template_for_dev_install(tmp_path):
    repo_root = tmp_path / "repo"
    repo_template = repo_root / "templates" / "example.txt"
    repo_template.parent.mkdir(parents=True)
    repo_template.write_text("repo")

    resolved = resolve_asset_path(
        "templates/example.txt",
        overlay_root=tmp_path / "overlay",
        repo_root=repo_root,
        package_names=(),
        cache_root=tmp_path / "cache",
    )

    assert resolved == repo_template
    assert resolved.read_text() == "repo"


def test_resolve_asset_path_prefers_overlay_template_over_packaged_or_repo(tmp_path):
    repo_root = tmp_path / "repo"
    repo_template = repo_root / "templates" / "example.txt"
    repo_template.parent.mkdir(parents=True)
    repo_template.write_text("repo")

    overlay_root = tmp_path / "overlay"
    overlay_template = overlay_root / "example.txt"
    overlay_template.parent.mkdir(parents=True)
    overlay_template.write_text("overlay")

    resolved = resolve_asset_path(
        "templates/example.txt",
        overlay_root=overlay_root,
        repo_root=repo_root,
        package_names=(),
        cache_root=tmp_path / "cache",
    )

    assert resolved == overlay_template
    assert resolved.read_text() == "overlay"
