"""Conservative codemod helpers for framework adapter install steps."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CodemodMode = Literal["ts-morph", "fallback", "manual"]
_IMPORT_TEMPLATE = "import {{ {symbol} }} from '{specifier}';\n"
_MANUAL_CONFIDENCE_THRESHOLD = 0.74


@dataclass(frozen=True, slots=True)
class CodemodResult:
    applied: bool
    mode: CodemodMode
    notes: list[str]


def add_vite_plugin(
    vite_config_path: Path,
    import_specifier: str,
    plugin_name: str,
) -> CodemodResult:
    """Ensure a Vite plugin import and plugin registration exist."""
    vite_config_path = Path(vite_config_path)
    if not vite_config_path.exists():
        return _manual_result(
            vite_config_path,
            [
                f"Add `{_format_import(import_specifier, plugin_name).strip()}` near the top.",
                f"Add `{plugin_name}()` inside the `plugins: [...]` array.",
            ],
        )

    if _ts_morph_available():
        return _run_ts_morph_vite_plugin(vite_config_path, import_specifier, plugin_name)

    return _fallback_add_vite_plugin(vite_config_path, import_specifier, plugin_name)


def mount_br_logger_in_main_tsx(
    main_tsx_path: Path,
    component_import_path: str,
    component_name: str,
) -> CodemodResult:
    """Ensure a logger component is imported and rendered near the app root."""
    main_tsx_path = Path(main_tsx_path)
    if not main_tsx_path.exists():
        return _manual_result(
            main_tsx_path,
            [
                f"Add `{_format_import(component_import_path, component_name).strip()}` near the top.",
                f"Render `<{component_name} />` once near the root component mount.",
            ],
        )

    if _ts_morph_available():
        return _run_ts_morph_mount(main_tsx_path, component_import_path, component_name)

    return _fallback_mount_br_logger(main_tsx_path, component_import_path, component_name)


def _ts_morph_available() -> bool:
    node_executable = _node_executable()
    if node_executable is None:
        return False

    try:
        result = subprocess.run(  # noqa: S603
            [node_executable, "-e", "require('ts-morph')"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False

    return result.returncode == 0


def _run_ts_morph_vite_plugin(
    vite_config_path: Path,
    import_specifier: str,
    plugin_name: str,
) -> CodemodResult:
    script = textwrap.dedent(
        """
        const { Project, SyntaxKind } = require("ts-morph");
        const fs = require("fs");

        const [, filePath, importSpecifier, pluginName] = process.argv;
        const project = new Project({ useInMemoryFileSystem: false, skipFileDependencyResolution: true });
        const source = project.addSourceFileAtPath(filePath);

        const existingImport = source.getImportDeclaration((decl) => decl.getModuleSpecifierValue() === importSpecifier);
        if (existingImport) {
          const named = existingImport.getNamedImports().map((item) => item.getName());
          if (!named.includes(pluginName)) {
            existingImport.addNamedImport(pluginName);
          }
        } else {
          source.addImportDeclaration({ namedImports: [pluginName], moduleSpecifier: importSpecifier });
        }

        const properties = source.getDescendantsOfKind(SyntaxKind.PropertyAssignment)
          .filter((prop) => prop.getName() === "plugins");
        if (properties.length !== 1) {
          console.log(JSON.stringify({
            applied: false,
            mode: "manual",
            notes: [
              `Add import { ${pluginName} } from '${importSpecifier}';`,
              `Add ${pluginName}() inside plugins: [...].`,
            ],
          }));
          process.exit(0);
        }

        const initializer = properties[0].getInitializerIfKind(SyntaxKind.ArrayLiteralExpression);
        if (!initializer) {
          console.log(JSON.stringify({
            applied: false,
            mode: "manual",
            notes: [
              `Add ${pluginName}() inside plugins: [...].`,
            ],
          }));
          process.exit(0);
        }

        const alreadyPresent = initializer.getElements().some((element) => element.getText().includes(pluginName));
        if (alreadyPresent) {
          source.saveSync();
          console.log(JSON.stringify({ applied: false, mode: "ts-morph", notes: ["Plugin already registered."] }));
          process.exit(0);
        }

        initializer.addElement(`${pluginName}()`);
        source.saveSync();
        console.log(JSON.stringify({ applied: true, mode: "ts-morph", notes: ["Registered Vite plugin."] }));
        """
    ).strip()

    return _run_ts_morph_script(
        vite_config_path,
        script,
        (str(vite_config_path), import_specifier, plugin_name),
        manual_notes=[
            f"Add `{_format_import(import_specifier, plugin_name).strip()}` near the top.",
            f"Add `{plugin_name}()` inside the `plugins: [...]` array.",
        ],
    )


def _run_ts_morph_mount(
    main_tsx_path: Path,
    component_import_path: str,
    component_name: str,
) -> CodemodResult:
    script = textwrap.dedent(
        """
        const { Project } = require("ts-morph");

        const [, filePath, importSpecifier, componentName] = process.argv;
        const project = new Project({ useInMemoryFileSystem: false, skipFileDependencyResolution: true });
        const source = project.addSourceFileAtPath(filePath);

        const existingImport = source.getImportDeclaration((decl) => decl.getModuleSpecifierValue() === importSpecifier);
        if (existingImport) {
          const named = existingImport.getNamedImports().map((item) => item.getName());
          if (!named.includes(componentName)) {
            existingImport.addNamedImport(componentName);
          }
        } else {
          source.addImportDeclaration({ namedImports: [componentName], moduleSpecifier: importSpecifier });
        }

        const originalText = source.getFullText();
        if (originalText.includes(`<${componentName}`)) {
          source.saveSync();
          console.log(JSON.stringify({ applied: false, mode: "ts-morph", notes: ["Logger already mounted."] }));
          process.exit(0);
        }

        function injectIntoJsx(jsxText, name) {
          if (jsxText.includes(`<${name}`)) {
            return { changed: false, text: jsxText, confidence: 1 };
          }

          if (jsxText.includes("{children}")) {
            return {
              changed: true,
              confidence: 0.95,
              text: jsxText.replace("{children}", `<${name} />\\n        {children}`),
            };
          }

          const strongTarget = jsxText.match(/<(App|Component)\\b[^>]*\\/?>/);
          if (strongTarget) {
            return {
              changed: true,
              confidence: 0.95,
              text: jsxText.replace(strongTarget[0], `<${name} />\\n        ${strongTarget[0]}`),
            };
          }

          const bodyTag = jsxText.match(/<body[^>]*>/);
          if (bodyTag) {
            return {
              changed: true,
              confidence: 0.9,
              text: jsxText.replace(bodyTag[0], `${bodyTag[0]}\\n        <${name} />`),
            };
          }

          const strictMode = jsxText.match(/<React\\.StrictMode[^>]*>/);
          if (strictMode) {
            return {
              changed: true,
              confidence: 0.9,
              text: jsxText.replace(strictMode[0], `${strictMode[0]}\\n      <${name} />`),
            };
          }

          const fragmentOpen = jsxText.match(/^\\s*<>/);
          if (fragmentOpen) {
            return {
              changed: true,
              confidence: 0.85,
              text: jsxText.replace(fragmentOpen[0], `${fragmentOpen[0]}\\n  <${name} />`),
            };
          }

          if (/^\\s*<[^>]+\\/>\\s*$/.test(jsxText.trim())) {
            return {
              changed: true,
              confidence: 0.82,
              text: `<>\\n  <${name} />\\n  ${jsxText.trim()}\\n</>`,
            };
          }

          return { changed: false, text: jsxText, confidence: 0.1 };
        }

        function injectIntoText(text, name) {
          const renderMatch = text.match(/\\.render\\(([^]*?)\\)\\s*;?/m);
          if (renderMatch) {
            const injected = injectIntoJsx(renderMatch[1], name);
            if (injected.changed && injected.confidence >= 0.74) {
              return {
                changed: true,
                confidence: injected.confidence,
                text: text.replace(renderMatch[1], injected.text),
              };
            }
          }

          const returnMatch = text.match(/return\\s*\\(([^]*?)\\)\\s*;?/m);
          if (returnMatch) {
            const injected = injectIntoJsx(returnMatch[1], name);
            if (injected.changed && injected.confidence >= 0.74) {
              return {
                changed: true,
                confidence: injected.confidence,
                text: text.replace(returnMatch[1], injected.text),
              };
            }
          }

          const bareReturnMatch = text.match(/return\\s*(<[^;]+\\/>)\\s*;?/m);
          if (bareReturnMatch) {
            const injected = injectIntoJsx(bareReturnMatch[1], name);
            if (injected.changed && injected.confidence >= 0.74) {
              return {
                changed: true,
                confidence: injected.confidence,
                text: text.replace(bareReturnMatch[1], injected.text),
              };
            }
          }

          return { changed: false, confidence: 0.1, text };
        }

        const injected = injectIntoText(source.getFullText(), componentName);
        if (!injected.changed) {
          console.log(JSON.stringify({
            applied: false,
            mode: "manual",
            notes: [
              `Add import { ${componentName} } from '${importSpecifier}';`,
              `Render <${componentName} /> once near the root component mount.`,
            ],
          }));
          process.exit(0);
        }

        source.replaceWithText(injected.text);
        source.saveSync();
        console.log(JSON.stringify({ applied: true, mode: "ts-morph", notes: ["Mounted logger component."] }));
        """
    ).strip()

    return _run_ts_morph_script(
        main_tsx_path,
        script,
        (str(main_tsx_path), component_import_path, component_name),
        manual_notes=[
            f"Add `{_format_import(component_import_path, component_name).strip()}` near the top.",
            f"Render `<{component_name} />` once near the root component mount.",
        ],
    )


def _run_ts_morph_script(  # noqa: PLR0911
    target_path: Path,
    script: str,
    args: tuple[str, ...],
    *,
    manual_notes: list[str],
) -> CodemodResult:
    node_executable = _node_executable()
    if node_executable is None:
        return _manual_result(target_path, manual_notes)

    try:
        result = subprocess.run(  # noqa: S603
            [node_executable, "-e", script, *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return _manual_result(target_path, manual_notes)

    if result.returncode != 0:
        notes = [line for line in result.stderr.strip().splitlines() if line]
        return _manual_result(
            target_path,
            [*manual_notes, *notes],
        )

    payload = result.stdout.strip()
    if not payload:
        return _manual_result(target_path, manual_notes)

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return _manual_result(target_path, [*manual_notes, payload])

    mode = parsed.get("mode", "manual")
    notes = [str(note) for note in parsed.get("notes", [])]
    applied = bool(parsed.get("applied", False))
    if mode == "manual":
        return _manual_result(target_path, notes or manual_notes)
    return CodemodResult(applied=applied, mode="ts-morph", notes=notes)


def _fallback_add_vite_plugin(
    vite_config_path: Path,
    import_specifier: str,
    plugin_name: str,
) -> CodemodResult:
    content = vite_config_path.read_text(encoding="utf-8")
    updated = content
    changed = False

    if not _has_named_import(content, import_specifier, plugin_name):
        updated = _ensure_named_import(updated, import_specifier, plugin_name)
        changed = True

    matches = list(re.finditer(r"plugins\s*:\s*\[(?P<body>[\s\S]*?)\]", updated))
    if len(matches) != 1:
        return _manual_result(
            vite_config_path,
            [
                f"Add `{_format_import(import_specifier, plugin_name).strip()}` near the top.",
                f"Add `{plugin_name}()` inside the `plugins: [...]` array.",
            ],
        )

    match = matches[0]
    body = match.group("body")
    if re.search(rf"\b{re.escape(plugin_name)}\s*(\(|\b)", body):
        if changed:
            vite_config_path.write_text(updated, encoding="utf-8")
        return CodemodResult(
            applied=changed,
            mode="fallback",
            notes=["Plugin already registered." if not changed else "Added missing import only."],
        )

    replacement = _insert_vite_plugin(match.group(0), body, plugin_name)
    confidence = 0.95
    if confidence < _MANUAL_CONFIDENCE_THRESHOLD:
        return _manual_result(
            vite_config_path,
            [f"Add `{plugin_name}()` inside the `plugins: [...]` array."],
        )

    updated = updated[: match.start()] + replacement + updated[match.end() :]
    vite_config_path.write_text(updated, encoding="utf-8")
    return CodemodResult(applied=True, mode="fallback", notes=["Registered Vite plugin."])


def _fallback_mount_br_logger(
    main_tsx_path: Path,
    component_import_path: str,
    component_name: str,
) -> CodemodResult:
    content = main_tsx_path.read_text(encoding="utf-8")
    if f"<{component_name}" in content and _has_named_import(
        content, component_import_path, component_name
    ):
        return CodemodResult(applied=False, mode="fallback", notes=["Logger already mounted."])

    updated = content
    changed = False
    if not _has_named_import(updated, component_import_path, component_name):
        updated = _ensure_named_import(updated, component_import_path, component_name)
        changed = True

    injected = _inject_component_into_text(updated, component_name)
    if not injected.changed or injected.confidence < _MANUAL_CONFIDENCE_THRESHOLD:
        if changed and updated != content:
            main_tsx_path.write_text(updated, encoding="utf-8")
        return _manual_result(
            main_tsx_path,
            [
                f"Add `{_format_import(component_import_path, component_name).strip()}` near the top.",
                f"Render `<{component_name} />` once near the root component mount.",
            ],
        )

    if injected.text != updated:
        updated = injected.text
        changed = True

    if changed:
        main_tsx_path.write_text(updated, encoding="utf-8")
    return CodemodResult(applied=changed, mode="fallback", notes=["Mounted logger component."])


def _has_named_import(content: str, import_specifier: str, symbol: str) -> bool:
    pattern = re.compile(
        rf"import\s*\{{[^}}]*\b{re.escape(symbol)}\b[^}}]*\}}\s*from\s*['\"]{re.escape(import_specifier)}['\"]"
    )
    return pattern.search(content) is not None


def _ensure_named_import(content: str, import_specifier: str, symbol: str) -> str:
    if _has_named_import(content, import_specifier, symbol):
        return content

    import_line = _format_import(import_specifier, symbol)
    import_matches = list(re.finditer(r"^import .*?;\n?", content, flags=re.MULTILINE))
    if import_matches:
        last_match = import_matches[-1]
        return content[: last_match.end()] + import_line + content[last_match.end() :]
    return import_line + content


def _format_import(import_specifier: str, symbol: str) -> str:
    return _IMPORT_TEMPLATE.format(symbol=symbol, specifier=import_specifier)


def _insert_vite_plugin(full_match: str, body: str, plugin_name: str) -> str:
    plugin_call = f"{plugin_name}()"
    stripped = body.strip()
    if not stripped:
        closing_index = full_match.rfind("]")
        if closing_index == -1:
            return full_match
        return f"{full_match[:closing_index]}{plugin_call}{full_match[closing_index:]}"

    if body.endswith("\n"):
        insertion = body.rstrip() + f",\n    {plugin_call}\n"
    else:
        insertion = body + f", {plugin_call}"
    return full_match.replace(body, insertion)


@dataclass(frozen=True, slots=True)
class _InjectionResult:
    changed: bool
    confidence: float
    text: str


def _inject_component_into_text(  # noqa: PLR0911
    content: str, component_name: str
) -> _InjectionResult:
    render_matches = list(re.finditer(r"\.render\(\s*(?P<jsx>[\s\S]*?)\s*\)\s*;?", content))
    if len(render_matches) == 1:
        return _replace_match_with_injection(content, render_matches[0], component_name)
    if len(render_matches) > 1:
        return _InjectionResult(changed=False, confidence=0.1, text=content)

    return_matches = list(re.finditer(r"return\s*\(\s*(?P<jsx>[\s\S]*?)\s*\)\s*;?", content))
    if len(return_matches) == 1:
        return _replace_match_with_injection(content, return_matches[0], component_name)
    if len(return_matches) > 1:
        return _InjectionResult(changed=False, confidence=0.1, text=content)

    bare_return_matches = list(re.finditer(r"return\s*(?P<jsx><[^;]+\/>)\s*;?", content))
    if len(bare_return_matches) == 1:
        return _replace_match_with_injection(content, bare_return_matches[0], component_name)
    if len(bare_return_matches) > 1:
        return _InjectionResult(changed=False, confidence=0.1, text=content)

    return _InjectionResult(changed=False, confidence=0.1, text=content)


def _replace_match_with_injection(
    content: str,
    match: re.Match[str],
    component_name: str,
) -> _InjectionResult:
    jsx = match.group("jsx")
    injected = _inject_component_into_jsx(jsx, component_name)
    if not injected.changed:
        return _InjectionResult(changed=False, confidence=injected.confidence, text=content)

    start, end = match.span("jsx")
    updated = content[:start] + injected.text + content[end:]
    return _InjectionResult(changed=True, confidence=injected.confidence, text=updated)


def _inject_component_into_jsx(jsx: str, component_name: str) -> _InjectionResult:  # noqa: PLR0911
    if f"<{component_name}" in jsx:
        return _InjectionResult(changed=False, confidence=1.0, text=jsx)

    if "{children}" in jsx:
        updated = jsx.replace("{children}", f"<{component_name} />\n        {{children}}", 1)
        return _InjectionResult(changed=True, confidence=0.95, text=updated)

    strong_target = re.search(r"<(App|Component)\b[^>]*\/>", jsx)
    if strong_target:
        target = strong_target.group(0)
        updated = jsx.replace(target, f"<{component_name} />\n        {target}", 1)
        return _InjectionResult(changed=True, confidence=0.95, text=updated)

    body_tag = re.search(r"<body[^>]*>", jsx)
    if body_tag:
        target = body_tag.group(0)
        updated = jsx.replace(target, f"{target}\n        <{component_name} />", 1)
        return _InjectionResult(changed=True, confidence=0.9, text=updated)

    strict_mode = re.search(r"<React\.StrictMode[^>]*>", jsx)
    if strict_mode:
        target = strict_mode.group(0)
        updated = jsx.replace(target, f"{target}\n      <{component_name} />", 1)
        return _InjectionResult(changed=True, confidence=0.9, text=updated)

    if re.match(r"^\s*<>\s*", jsx):
        updated = re.sub(r"^\s*<>", f"<>\n  <{component_name} />", jsx, count=1)
        return _InjectionResult(changed=True, confidence=0.85, text=updated)

    if re.fullmatch(r"\s*<[^>]+\/>\s*", jsx):
        wrapped = f"<>\n  <{component_name} />\n  {jsx.strip()}\n</>"
        return _InjectionResult(changed=True, confidence=0.82, text=wrapped)

    return _InjectionResult(changed=False, confidence=0.1, text=jsx)


def _manual_result(target_path: Path, notes: list[str]) -> CodemodResult:
    filtered_notes = [note for note in notes if note]
    sys.stdout.write(f"Manual update required for {target_path}:\n")
    for note in filtered_notes:
        sys.stdout.write(f"- {note}\n")
    return CodemodResult(applied=False, mode="manual", notes=filtered_notes)


def _node_executable() -> str | None:
    return shutil.which("node")
