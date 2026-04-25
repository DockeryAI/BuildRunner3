"""Install enforced BR3 git hooks with conservative legacy BR2 handling."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.asset_resolver import resolve_asset_path

_BR2_MARKER_PATH = Path(".buildrunner/hooks/brandock-spec.marker")
_PRE_PUSH_FRAGMENT_ASSETS = (".buildrunner/hooks/pre-push.d/50-ship-gate.sh",)
_UTC = getattr(datetime, "UTC", timezone.utc)  # noqa: UP017


@dataclass(frozen=True)
class HookInstallResult:
    """Summarize a hook installation run."""

    replaced: list[str]
    backed_up: list[Path]
    installed: list[Path]
    pre_push_d: Path


def install_hooks(target_repo: Path) -> HookInstallResult:
    """Install BR3 enforced hooks into the target git repository."""
    repo_root = Path(target_repo).resolve()
    git_dir = repo_root / ".git"
    if not git_dir.is_dir():
        raise FileNotFoundError(f"Not a git repository: {repo_root}")

    git_hooks_dir = git_dir / "hooks"
    git_hooks_dir.mkdir(parents=True, exist_ok=True)

    buildrunner_dir = repo_root / ".buildrunner"
    legacy_dir = buildrunner_dir / "hooks" / "legacy"
    decisions_log = buildrunner_dir / "decisions.log"
    pre_push_d = git_hooks_dir / "pre-push.d"
    pre_push_d.mkdir(parents=True, exist_ok=True)

    pre_commit_source = resolve_asset_path(".buildrunner/hooks/pre-commit-enforced")
    pre_push_source = resolve_asset_path(".buildrunner/hooks/pre-push-enforced")

    source_specs = {
        "pre-commit": pre_commit_source,
        "pre-push": pre_push_source,
    }
    source_bytes = {name: path.read_bytes() for name, path in source_specs.items()}

    marker_exists = (repo_root / _BR2_MARKER_PATH).exists()
    replaced: list[str] = []
    backed_up: list[Path] = []
    installed: list[Path] = []

    for hook_name, source_path in source_specs.items():
        target_path = git_hooks_dir / hook_name
        if _is_legacy_br2_hook(
            hook_path=target_path,
            expected_br3_bytes=source_bytes[hook_name],
            marker_exists=marker_exists,
        ):
            backup_path = _backup_hook(target_path, legacy_dir)
            replaced.append(hook_name)
            backed_up.append(backup_path)
            _append_decision_log(
                decisions_log,
                hook_name=hook_name,
                backup_path=backup_path,
                source_path=source_path,
            )

        _install_file(source_path, target_path)
        installed.append(target_path)

    for relative_path in _PRE_PUSH_FRAGMENT_ASSETS:
        source_path = resolve_asset_path(relative_path)
        target_path = pre_push_d / source_path.name
        _install_file(source_path, target_path)
        installed.append(target_path)

    return HookInstallResult(
        replaced=replaced,
        backed_up=backed_up,
        installed=installed,
        pre_push_d=pre_push_d,
    )


def _is_legacy_br2_hook(
    *,
    hook_path: Path,
    expected_br3_bytes: bytes,
    marker_exists: bool,
) -> bool:
    if not hook_path.is_file():
        return False

    current_bytes = hook_path.read_bytes()
    if current_bytes == expected_br3_bytes:
        return False

    current_text = current_bytes.decode("utf-8", errors="ignore")
    if "brandock-spec" in current_text:
        return True

    return marker_exists


def _backup_hook(hook_path: Path, legacy_dir: Path) -> Path:
    legacy_dir.mkdir(parents=True, exist_ok=True)
    backup_path = legacy_dir / f"{hook_path.name}.{_utc_iso_timestamp()}"
    shutil.copy2(hook_path, backup_path)
    return backup_path


def _install_file(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    target_path.chmod(0o755)


def _append_decision_log(
    decisions_log: Path,
    *,
    hook_name: str,
    backup_path: Path,
    source_path: Path,
) -> None:
    decisions_log.parent.mkdir(parents=True, exist_ok=True)
    with decisions_log.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{_utc_iso_timestamp()} hook-installer replaced={hook_name} "
            f"backup={backup_path} source={source_path}\n"
        )


def _utc_iso_timestamp() -> str:
    return datetime.now(_UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
