"""Expo adapter installation."""

from __future__ import annotations

from pathlib import Path

from core.installer.adapters import AdapterResult, write_template_if_missing
from core.installer.codemod import mount_br_logger_in_main_tsx


class ExpoAdapter:
    """Install the Expo logger scaffold and app-root wiring."""

    def install(self, target_repo: Path) -> AdapterResult:
        repo_root = Path(target_repo).resolve()
        result = AdapterResult()

        write_template_if_missing(
            asset_relative_path="templates/adapters/expo/components/BRLoggerNative.tsx",
            target_path=repo_root / "components" / "BRLoggerNative.tsx",
            written=result.written,
            skipped=result.skipped,
        )

        mount_path = _first_existing(repo_root / "App.tsx", repo_root / "App.js")
        result.codemods["logger_mount"] = mount_br_logger_in_main_tsx(
            mount_path or (repo_root / "App.tsx"),
            "./components/BRLoggerNative",
            "BRLoggerNative",
        )
        return result


def install(target_repo: Path) -> AdapterResult:
    return ExpoAdapter().install(target_repo)


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None
