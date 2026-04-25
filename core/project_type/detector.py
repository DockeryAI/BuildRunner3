from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from core.project_type.composition import CompositionConflict, apply_composition_rules
from core.project_type.facets import Bundler, Capability, Framework, ProjectFacets


@dataclass(slots=True)
class DetectionReport:
    signals: dict[str, list[str]] = field(default_factory=dict)
    ambiguities: list[str] = field(default_factory=list)
    composition_conflicts: list[CompositionConflict] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _FrameworkMatch:
    rule_name: str
    framework: Framework
    bundler: Bundler
    priority: int


def detect_facets(project_path: Path) -> tuple[ProjectFacets, DetectionReport]:
    project_path = Path(project_path)
    package_json = _load_package_json(project_path / "package.json")
    dependencies, dependency_sources = _collect_dependencies(package_json)
    report = DetectionReport()

    capabilities: set[Capability] = set()
    framework_matches: list[_FrameworkMatch] = []

    pwa_signals = _detect_pwa(project_path, dependencies, dependency_sources)
    if pwa_signals:
        report.signals["pwa"] = pwa_signals
        capabilities.add(Capability.pwa)

    capacitor_signals = _detect_capacitor(project_path, dependencies, dependency_sources)
    if capacitor_signals:
        report.signals["capacitor"] = capacitor_signals
        capabilities.add(Capability.capacitor)

    expo_signals = _detect_expo(project_path)
    if expo_signals:
        report.signals["expo"] = expo_signals
        framework_matches.append(
            _FrameworkMatch(
                rule_name="expo",
                framework=Framework.expo,
                bundler=Bundler.metro,
                priority=300,
            )
        )

    godot_signals = _detect_godot(project_path)
    if godot_signals:
        report.signals["godot"] = godot_signals
        framework_matches.append(
            _FrameworkMatch(
                rule_name="godot",
                framework=Framework.godot,
                bundler=Bundler.godot_editor,
                priority=400,
            )
        )

    next_signals = _detect_next(project_path)
    if next_signals:
        report.signals["next"] = next_signals
        framework_matches.append(
            _FrameworkMatch(
                rule_name="next",
                framework=Framework.react,
                bundler=Bundler.next,
                priority=200,
            )
        )

    vite_react_signals = _detect_vite_react(project_path, dependencies, dependency_sources)
    if vite_react_signals:
        report.signals["vite-react"] = vite_react_signals
        framework_matches.append(
            _FrameworkMatch(
                rule_name="vite-react",
                framework=Framework.react,
                bundler=Bundler.vite,
                priority=100,
            )
        )

    supabase_signals = _detect_supabase(project_path, dependencies, dependency_sources)
    backend = None
    if supabase_signals:
        report.signals["supabase"] = supabase_signals
        capabilities.add(Capability.supabase_edge)
        backend = "supabase"

    selected_match = _select_framework_match(framework_matches, report)
    if selected_match is None:
        facets = ProjectFacets(
            framework=Framework.unknown,
            bundler=Bundler.none,
            backend=backend,
            capabilities=capabilities,
        )
    else:
        facets = ProjectFacets(
            framework=selected_match.framework,
            bundler=selected_match.bundler,
            backend=backend,
            capabilities=capabilities,
        )

    normalized_facets, conflicts = apply_composition_rules(facets)
    report.composition_conflicts.extend(conflicts)
    return normalized_facets, report


def _load_package_json(package_json_path: Path) -> dict[str, object]:
    if not package_json_path.exists():
        return {}

    try:
        raw_payload = package_json_path.read_text(encoding="utf-8")
        payload = json.loads(raw_payload)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}
    return payload


def _collect_dependencies(
    package_json: dict[str, object],
) -> tuple[dict[str, str], dict[str, str]]:
    dependencies: dict[str, str] = {}
    dependency_sources: dict[str, str] = {}

    for section_name in ("dependencies", "devDependencies"):
        section = package_json.get(section_name)
        if not isinstance(section, dict):
            continue
        for package_name, package_version in section.items():
            if not isinstance(package_name, str):
                continue
            dependencies[package_name] = str(package_version)
            dependency_sources[package_name] = f"package.json:{section_name}.{package_name}"

    return dependencies, dependency_sources


def _detect_pwa(
    project_path: Path, dependencies: dict[str, str], dependency_sources: dict[str, str]
) -> list[str]:
    if "vite-plugin-pwa" not in dependencies:
        return []

    service_worker_paths = _find_service_workers(project_path)
    if not service_worker_paths:
        return []

    dependency_source = dependency_sources["vite-plugin-pwa"]
    return [dependency_source, *service_worker_paths]


def _detect_capacitor(
    project_path: Path, dependencies: dict[str, str], dependency_sources: dict[str, str]
) -> list[str]:
    config_paths = _find_root_matches(
        project_path,
        ("capacitor.config.ts", "capacitor.config.js", "capacitor.config.json"),
    )
    if not config_paths or "@capacitor/core" not in dependencies:
        return []

    dependency_source = dependency_sources["@capacitor/core"]
    return [*config_paths, dependency_source]


def _detect_expo(project_path: Path) -> list[str]:
    signals: list[str] = []

    app_json_path = project_path / "app.json"
    if app_json_path.exists():
        try:
            app_payload = json.loads(app_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            app_payload = {}
        if isinstance(app_payload, dict) and "expo" in app_payload:
            signals.append("app.json:expo")

    if (project_path / "eas.json").exists():
        signals.append("eas.json")

    signals.extend(_find_root_glob_matches(project_path, "metro.config.*"))
    return sorted(set(signals))


def _detect_godot(project_path: Path) -> list[str]:
    godot_project = project_path / "project.godot"
    if godot_project.exists():
        return ["project.godot"]
    return []


def _detect_next(project_path: Path) -> list[str]:
    return _find_root_glob_matches(project_path, "next.config.*")


def _detect_vite_react(
    project_path: Path, dependencies: dict[str, str], dependency_sources: dict[str, str]
) -> list[str]:
    vite_configs = _find_root_glob_matches(project_path, "vite.config.*")
    if not vite_configs or "react" not in dependencies:
        return []

    dependency_source = dependency_sources["react"]
    return [*vite_configs, dependency_source]


def _detect_supabase(
    project_path: Path, dependencies: dict[str, str], dependency_sources: dict[str, str]
) -> list[str]:
    signals: list[str] = []

    if (project_path / "supabase" / "functions").is_dir():
        signals.append("supabase/functions")

    if "@supabase/supabase-js" in dependencies:
        signals.append(dependency_sources["@supabase/supabase-js"])

    return sorted(set(signals))


def _find_service_workers(project_path: Path) -> list[str]:
    matches: list[str] = []

    for filename in ("sw.ts", "sw.js"):
        root_candidate = project_path / filename
        if root_candidate.exists():
            matches.append(filename)

    src_dir = project_path / "src"
    if src_dir.exists():
        for filename in ("sw.ts", "sw.js"):
            matches.extend(
                path.relative_to(project_path).as_posix()
                for path in sorted(src_dir.rglob(filename))
            )

    return sorted(set(matches))


def _find_root_matches(project_path: Path, filenames: tuple[str, ...]) -> list[str]:
    matches = [filename for filename in filenames if (project_path / filename).exists()]
    return sorted(matches)


def _find_root_glob_matches(project_path: Path, pattern: str) -> list[str]:
    return sorted(path.name for path in project_path.glob(pattern) if path.is_file())


def _select_framework_match(
    framework_matches: list[_FrameworkMatch], report: DetectionReport
) -> _FrameworkMatch | None:
    if not framework_matches:
        return None

    has_expo = any(match.framework is Framework.expo for match in framework_matches)
    has_react = any(match.framework is Framework.react for match in framework_matches)
    if has_expo and has_react:
        report.ambiguities.append("react+expo both matched; defaulting to expo")

    if len(framework_matches) > 1 and not (has_expo and has_react):
        ordered_names = ", ".join(
            match.rule_name for match in sorted(framework_matches, key=lambda match: -match.priority)
        )
        winner = max(framework_matches, key=lambda match: match.priority)
        report.ambiguities.append(
            f"multiple framework rules matched ({ordered_names}); defaulting to {winner.rule_name}"
        )

    return max(framework_matches, key=lambda match: match.priority)
