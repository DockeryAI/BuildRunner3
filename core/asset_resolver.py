"""Resolve packaged BuildRunner assets with repo and user-overlay fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


DEFAULT_RESOURCE_PACKAGES = ("core", "templates")
DEFAULT_TEMPLATE_OVERLAY_ROOT = Path.home() / ".buildrunner" / "templates"
DEFAULT_SCRIPT_FALLBACK_ROOT = Path.home() / ".buildrunner" / "scripts"
DEFAULT_CACHE_ROOT = Path.home() / ".buildrunner" / "_asset_cache"


class AssetNotFoundError(FileNotFoundError):
    """Raised when a requested asset cannot be resolved."""


@dataclass(frozen=True)
class TemplateSyncResult:
    """Summarize a template sync into the user overlay."""

    written: list[Path]
    skipped: list[Path]


@dataclass(frozen=True)
class LegacyAttachMigrationResult:
    """Summarize the legacy br-attach migration."""

    backup_path: Path | None
    stub_path: Path | None
    changed: bool


def get_install_root() -> Path:
    """Return the BuildRunner install root for repo-relative assets."""
    return Path(__file__).resolve().parent.parent


def resolve_install_path(relative_path: str | Path) -> Path:
    """Resolve a path relative to the active BuildRunner install root."""
    return get_install_root() / _normalize_relative_path(relative_path)


def resolve_asset_path(
    relative_path: str | Path,
    *,
    overlay_root: Path | None = None,
    repo_root: Path | None = None,
    package_names: tuple[str, ...] = DEFAULT_RESOURCE_PACKAGES,
    cache_root: Path | None = None,
) -> Path:
    """Resolve a BuildRunner asset path across overlays, package data, and repo checkout."""
    relative = _normalize_relative_path(relative_path)

    overlay_candidate = _template_overlay_path(relative, overlay_root)
    if overlay_candidate is not None and overlay_candidate.exists():
        return overlay_candidate

    packaged_candidate = _resolve_packaged_asset(relative, package_names, cache_root)
    if packaged_candidate is not None:
        return packaged_candidate

    repo_candidate = (repo_root or get_install_root()) / relative
    if repo_candidate.exists():
        return repo_candidate

    script_fallback = _script_fallback_path(relative)
    if script_fallback is not None and script_fallback.exists():
        return script_fallback

    raise AssetNotFoundError(f"BuildRunner asset not found: {relative.as_posix()}")


def iter_packaged_templates(
    *,
    repo_root: Path | None = None,
    package_names: tuple[str, ...] = DEFAULT_RESOURCE_PACKAGES,
) -> Iterator[tuple[Path, bytes]]:
    """Yield packaged template files relative to the templates root."""
    seen: set[Path] = set()

    for root in _template_resource_roots(package_names):
        for relative, content in _iter_traversable_files(root):
            if relative in seen:
                continue
            seen.add(relative)
            yield relative, content

    repo_templates = (repo_root or get_install_root()) / "templates"
    if repo_templates.exists():
        for path in sorted(repo_templates.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(repo_templates)
            if relative in seen:
                continue
            seen.add(relative)
            yield relative, path.read_bytes()


def sync_packaged_templates(
    *,
    overlay_root: Path | None = None,
    repo_root: Path | None = None,
    package_names: tuple[str, ...] = DEFAULT_RESOURCE_PACKAGES,
) -> TemplateSyncResult:
    """Sync packaged templates into ~/.buildrunner/templates, writing only changed files."""
    destination_root = overlay_root or DEFAULT_TEMPLATE_OVERLAY_ROOT
    written: list[Path] = []
    skipped: list[Path] = []

    for relative, content in iter_packaged_templates(repo_root=repo_root, package_names=package_names):
        destination = destination_root / relative
        if destination.exists() and destination.read_bytes() == content:
            skipped.append(destination)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        written.append(destination)

    return TemplateSyncResult(written=written, skipped=skipped)


def install_legacy_attach_stub(legacy_path: Path | None = None) -> LegacyAttachMigrationResult:
    """Back up ~/.br/bin/br-attach and replace it with a loud deprecation stub."""
    current_path = legacy_path or (Path.home() / ".br" / "bin" / "br-attach")
    if not current_path.exists():
        return LegacyAttachMigrationResult(backup_path=None, stub_path=None, changed=False)

    backup_path = current_path.with_name(f"{current_path.name}.deprecated.bak")
    stub_content = _legacy_attach_stub(current_path, backup_path)

    if current_path.read_text() == stub_content:
        return LegacyAttachMigrationResult(
            backup_path=backup_path if backup_path.exists() else None,
            stub_path=current_path,
            changed=False,
        )

    current_path.parent.mkdir(parents=True, exist_ok=True)
    if not backup_path.exists():
        current_path.rename(backup_path)
    else:
        current_path.unlink()

    current_path.write_text(stub_content)
    current_path.chmod(0o755)

    return LegacyAttachMigrationResult(backup_path=backup_path, stub_path=current_path, changed=True)


def _normalize_relative_path(relative_path: str | Path) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute():
        raise ValueError(f"Expected a relative asset path, got: {relative}")
    return relative


def _template_overlay_path(relative: Path, overlay_root: Path | None) -> Path | None:
    if not relative.parts or relative.parts[0] != "templates":
        return None
    root = overlay_root or DEFAULT_TEMPLATE_OVERLAY_ROOT
    return root.joinpath(*relative.parts[1:])


def _script_fallback_path(relative: Path) -> Path | None:
    if len(relative.parts) < 3 or relative.parts[:2] != (".buildrunner", "scripts"):
        return None
    return DEFAULT_SCRIPT_FALLBACK_ROOT.joinpath(*relative.parts[2:])


def _resolve_packaged_asset(
    relative: Path,
    package_names: tuple[str, ...],
    cache_root: Path | None,
) -> Path | None:
    traversable = _resolve_packaged_traversable(relative, package_names)
    if traversable is None:
        return None
    return _materialize_traversable(relative, traversable, cache_root or DEFAULT_CACHE_ROOT)


def _resolve_packaged_traversable(relative: Path, package_names: tuple[str, ...]):
    if not relative.parts:
        return None

    for root in _resource_roots_for(relative, package_names):
        tail = relative.parts[1:]
        candidate = root.joinpath(*tail) if tail else root
        if candidate.is_file():
            return candidate

    return None


def _resource_roots_for(relative: Path, package_names: tuple[str, ...]):
    head = relative.parts[0]
    if head == "templates":
        yield from _template_resource_roots(package_names)
        return

    if head != ".buildrunner" or len(relative.parts) < 2:
        return

    for package_name in package_names:
        try:
            root = resources.files(package_name)
        except ModuleNotFoundError:
            continue
        candidate = root.joinpath(".buildrunner")
        if _traversable_exists(candidate):
            yield candidate


def _template_resource_roots(package_names: tuple[str, ...]):
    for package_name in package_names:
        try:
            root = resources.files(package_name)
        except ModuleNotFoundError:
            continue

        candidate = root if package_name == "templates" else root.joinpath("templates")
        if _traversable_exists(candidate):
            yield candidate


def _traversable_exists(candidate) -> bool:
    return candidate.is_file() or candidate.is_dir()


def _materialize_traversable(relative: Path, traversable, cache_root: Path) -> Path:
    if isinstance(traversable, Path):
        return traversable

    destination = cache_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = traversable.read_bytes()
    if not destination.exists() or destination.read_bytes() != content:
        destination.write_bytes(content)

    if len(relative.parts) >= 3 and relative.parts[:2] == (".buildrunner", "scripts"):
        destination.chmod(0o755)

    return destination


def _iter_traversable_files(root, prefix: Path = Path()) -> Iterator[tuple[Path, bytes]]:
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        child_relative = prefix / child.name
        if child.is_dir():
            yield from _iter_traversable_files(child, child_relative)
        elif child.is_file():
            yield child_relative, child.read_bytes()


def _legacy_attach_stub(stub_path: Path, backup_path: Path) -> str:
    return (
        "#!/usr/bin/env bash\n"
        f'echo "Deprecated: {stub_path} moved to {backup_path}; use \'br attach\' instead." >&2; exit 1\n'
    )
