"""Next.js adapter installation."""

from __future__ import annotations

from pathlib import Path

from core.installer.adapters import AdapterResult, relative_import_path, write_template_if_missing
from core.installer.codemod import mount_br_logger_in_main_tsx


class NextAdapter:
    """Install the Next.js logger scaffold and root wiring."""

    def install(self, target_repo: Path) -> AdapterResult:
        repo_root = Path(target_repo).resolve()
        result = AdapterResult()

        app_dir = repo_root / "app"
        uses_app_router = app_dir.is_dir()
        component_dir = app_dir / "components" if uses_app_router else repo_root / "components"
        logger_path = component_dir / "BRLoggerNext.tsx"

        write_template_if_missing(
            asset_relative_path="templates/adapters/next/components/BRLoggerNext.tsx",
            target_path=logger_path,
            written=result.written,
            skipped=result.skipped,
        )
        write_template_if_missing(
            asset_relative_path="templates/adapters/next/app/api/br-log/route.ts.template",
            target_path=repo_root / "app" / "api" / "br-log" / "route.ts",
            written=result.written,
            skipped=result.skipped,
        )

        mount_path = _first_existing(
            repo_root / "app" / "layout.tsx",
            repo_root / "app" / "layout.jsx",
            repo_root / "pages" / "_app.tsx",
            repo_root / "pages" / "_app.jsx",
        )
        import_path = (
            relative_import_path(mount_path, logger_path)
            if mount_path is not None
            else "./components/BRLoggerNext"
        )
        result.codemods["logger_mount"] = mount_br_logger_in_main_tsx(
            mount_path or (repo_root / "app" / "layout.tsx"),
            import_path,
            "BRLoggerNext",
        )

        return result


def install(target_repo: Path) -> AdapterResult:
    return NextAdapter().install(target_repo)


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None
