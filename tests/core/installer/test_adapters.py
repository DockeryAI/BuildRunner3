from __future__ import annotations

import json
from typing import TYPE_CHECKING

from core.installer.adapters.expo import ExpoAdapter
from core.installer.adapters.next import NextAdapter
from core.installer.adapters.react_vite import ReactViteAdapter

if TYPE_CHECKING:
    from pathlib import Path


def test_install_react_vite_adapter_and_reinstall_is_noop(tmp_path) -> None:
    project = _write_react_vite_project(tmp_path / "react-vite")

    result = ReactViteAdapter().install(project)

    expected_paths = (
        project / "src" / "components" / "BRLogger.tsx",
        project / "src" / "components" / "supabaseLogger.ts",
        project / "src" / "components" / "brLoggerTransport.ts",
        project / "src" / "plugins" / "vite-br-unified-plugin.ts",
        project / "br-listen.mjs",
    )
    for path in expected_paths:
        assert path.is_file()

    vite_config = (project / "vite.config.ts").read_text(encoding="utf-8")
    assert "from './src/plugins/vite-br-unified-plugin'" in vite_config
    assert "brUnifiedPlugin()" in vite_config

    main_tsx = (project / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "from './components/BRLogger'" in main_tsx
    assert "<BRLogger />" in main_tsx
    assert result.script_suggestions == {"br:listen": "node br-listen.mjs"}
    assert result.codemods["vite_plugin"].mode in {"ts-morph", "fallback"}
    assert result.codemods["logger_mount"].mode in {"ts-morph", "fallback"}

    second_result = ReactViteAdapter().install(project)
    vite_config_again = (project / "vite.config.ts").read_text(encoding="utf-8")
    main_tsx_again = (project / "src" / "main.tsx").read_text(encoding="utf-8")

    assert vite_config_again.count("from './src/plugins/vite-br-unified-plugin'") == 1
    assert vite_config_again.count("brUnifiedPlugin()") == 1
    assert main_tsx_again.count("<BRLogger") == 1
    assert second_result.codemods["vite_plugin"].applied is False
    assert second_result.codemods["logger_mount"].applied is False


def test_install_next_adapter(tmp_path) -> None:
    project = _write_next_project(tmp_path / "next-app")

    result = NextAdapter().install(project)

    assert (project / "app" / "components" / "BRLoggerNext.tsx").is_file()
    assert (project / "app" / "api" / "br-log" / "route.ts").is_file()
    layout = (project / "app" / "layout.tsx").read_text(encoding="utf-8")
    assert "BRLoggerNext" in layout
    assert "<BRLoggerNext />" in layout
    assert result.codemods["logger_mount"].mode in {"ts-morph", "fallback"}


def test_install_expo_adapter(tmp_path) -> None:
    project = _write_expo_project(tmp_path / "expo-app")

    result = ExpoAdapter().install(project)

    assert (project / "components" / "BRLoggerNative.tsx").is_file()
    app_tsx = (project / "App.tsx").read_text(encoding="utf-8")
    assert "BRLoggerNative" in app_tsx
    assert "<BRLoggerNative />" in app_tsx
    assert result.codemods["logger_mount"].mode in {"ts-morph", "fallback"}


def test_react_vite_adapter_reports_manual_instructions_when_codemod_confidence_is_low(
    tmp_path,
    capsys,
) -> None:
    project = tmp_path / "manual-react-vite"
    project.mkdir()
    (project / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^19.0.0"}}),
        encoding="utf-8",
    )
    (project / "src").mkdir()
    (project / "src" / "main.tsx").write_text(
        "import App from './App';\nbootstrap(App);\n",
        encoding="utf-8",
    )
    (project / "vite.config.ts").write_text(
        "import { defineConfig } from 'vite';\nexport default defineConfig({});\n",
        encoding="utf-8",
    )

    result = ReactViteAdapter().install(project)
    output = capsys.readouterr().out

    assert (project / "src" / "components" / "BRLogger.tsx").is_file()
    assert result.codemods["vite_plugin"].mode == "manual"
    assert result.codemods["logger_mount"].mode == "manual"
    assert "Manual update required" in output
    assert "plugins: [...]" in output
    assert "Render `<BRLogger />` once near the root component mount." in output


def _write_react_vite_project(project_path: Path) -> Path:
    project_path.mkdir(parents=True)
    (project_path / "src").mkdir()
    (project_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^19.0.0"}}),
        encoding="utf-8",
    )
    (project_path / "src" / "App.tsx").write_text(
        "export function App() { return <div>Hello</div>; }\nexport default App;\n",
        encoding="utf-8",
    )
    (project_path / "vite.config.ts").write_text(
        "import { defineConfig } from 'vite';\n"
        "export default defineConfig({ plugins: [] });\n",
        encoding="utf-8",
    )
    (project_path / "src" / "main.tsx").write_text(
        "import React from 'react';\n"
        "import ReactDOM from 'react-dom/client';\n"
        "import App from './App';\n\n"
        "ReactDOM.createRoot(document.getElementById('root')!).render(\n"
        "  <React.StrictMode>\n"
        "    <App />\n"
        "  </React.StrictMode>\n"
        ");\n",
        encoding="utf-8",
    )
    return project_path


def _write_next_project(project_path: Path) -> Path:
    project_path.mkdir(parents=True)
    (project_path / "app").mkdir()
    (project_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "^16.0.0", "react": "^19.0.0"}}),
        encoding="utf-8",
    )
    (project_path / "app" / "layout.tsx").write_text(
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return (\n"
        "    <html>\n"
        "      <body>{children}</body>\n"
        "    </html>\n"
        "  );\n"
        "}\n",
        encoding="utf-8",
    )
    return project_path


def _write_expo_project(project_path: Path) -> Path:
    project_path.mkdir(parents=True)
    (project_path / "package.json").write_text(
        json.dumps({"dependencies": {"expo": "^54.0.0", "react-native": "^0.82.0"}}),
        encoding="utf-8",
    )
    (project_path / "app.json").write_text(
        json.dumps({"expo": {"name": "Fixture"}}),
        encoding="utf-8",
    )
    (project_path / "App.tsx").write_text(
        "import { View } from 'react-native';\n\n"
        "export default function App() {\n"
        "  return <View />;\n"
        "}\n",
        encoding="utf-8",
    )
    return project_path
