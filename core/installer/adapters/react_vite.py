"""React/Vite adapter installation."""

from __future__ import annotations

from pathlib import Path

from core.installer.adapters import AdapterResult, write_template_if_missing
from core.installer.codemod import add_vite_plugin, mount_br_logger_in_main_tsx


class ReactViteAdapter:
    """Install the React/Vite logger scaffold and entry-point wiring."""

    def install(self, target_repo: Path) -> AdapterResult:
        repo_root = Path(target_repo).resolve()
        result = AdapterResult(script_suggestions={"br:listen": "node br-listen.mjs"})

        for asset_relative_path, target_path in (
            (
                "templates/adapters/react-vite/components/BRLogger.tsx",
                repo_root / "src" / "components" / "BRLogger.tsx",
            ),
            (
                "templates/adapters/react-vite/components/supabaseLogger.ts",
                repo_root / "src" / "components" / "supabaseLogger.ts",
            ),
            (
                "templates/adapters/react-vite/components/brLoggerTransport.ts",
                repo_root / "src" / "components" / "brLoggerTransport.ts",
            ),
            (
                "templates/adapters/react-vite/components/vite-br-unified-plugin.ts",
                repo_root / "src" / "plugins" / "vite-br-unified-plugin.ts",
            ),
            (
                "templates/adapters/react-vite/br-listen.mjs",
                repo_root / "br-listen.mjs",
            ),
        ):
            write_template_if_missing(
                asset_relative_path=asset_relative_path,
                target_path=target_path,
                written=result.written,
                skipped=result.skipped,
            )

        vite_config_path = _first_existing(repo_root / "vite.config.ts", repo_root / "vite.config.js")
        if vite_config_path is None:
            result.codemods["vite_plugin"] = add_vite_plugin(
                repo_root / "vite.config.ts",
                "./src/plugins/vite-br-unified-plugin",
                "brUnifiedPlugin",
            )
        else:
            result.codemods["vite_plugin"] = add_vite_plugin(
                vite_config_path,
                "./src/plugins/vite-br-unified-plugin",
                "brUnifiedPlugin",
            )

        main_entry_path = _first_existing(repo_root / "src" / "main.tsx", repo_root / "src" / "main.jsx")
        if main_entry_path is None:
            result.codemods["logger_mount"] = mount_br_logger_in_main_tsx(
                repo_root / "src" / "main.tsx",
                "./components/BRLogger",
                "BRLogger",
            )
        else:
            result.codemods["logger_mount"] = mount_br_logger_in_main_tsx(
                main_entry_path,
                "./components/BRLogger",
                "BRLogger",
            )

        return result


def install(target_repo: Path) -> AdapterResult:
    return ReactViteAdapter().install(target_repo)


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None
