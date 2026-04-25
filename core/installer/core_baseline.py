"""Install the universal BR3 baseline into a target repository."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.asset_resolver import resolve_asset_path

if TYPE_CHECKING:
    from core.project_type.facets import ProjectFacets

_BASELINE_TEMPLATE_ROOT = Path("templates") / "core-baseline"
_STRUCTURED_FILES = (
    "agents.json",
    "skill-state.json",
    "orchestration_state.json",
)
_SKIP_IF_EXISTS_FILES = ("behavior.yaml",)
_WORKFLOW_DIRECTORIES = (
    "plans",
    "codex-briefs",
    "fixit-briefs",
    "adversarial-reviews",
    "validation",
    "verification",
    "reviews",
    "prompts-golden",
    "mockups",
    "specs",
    "design",
    "decisions",
)
_BYPASS_JUSTIFICATION_CONTENT = "# Bypass Justification\n"
_LOG_ROTATION_STUB = "#!/bin/sh\nexit 0\n"
BASELINE_EXPECTED_FILES = (
    Path(".buildrunner/agents.json"),
    Path(".buildrunner/skill-state.json"),
    Path(".buildrunner/behavior.yaml"),
    Path(".buildrunner/orchestration_state.json"),
    Path(".buildrunner/bypass-justification.md"),
    Path(".buildrunner/scripts/log-rotation.sh"),
    Path("CLAUDE.md"),
)


@dataclass(frozen=True)
class CoreBaselineResult:
    """Summarize a baseline installation run."""

    written: list[Path]
    merged: list[Path]
    skipped: list[Path]
    created_dirs: list[Path]

    def summary(self) -> str:
        return (
            f"written={len(self.written)} merged={len(self.merged)} "
            f"skipped={len(self.skipped)} dirs={len(self.created_dirs)}"
        )


class CoreBaselineInstaller:
    """Install the universal BuildRunner baseline into a repository."""

    @classmethod
    def expected_files(cls) -> tuple[Path, ...]:
        """Return the relative file paths this installer is responsible for."""
        return BASELINE_EXPECTED_FILES

    def install(
        self,
        target_repo: Path,
        *,
        declared_facets: ProjectFacets | None = None,
    ) -> CoreBaselineResult:
        repo_root = Path(target_repo).resolve()
        buildrunner_dir = repo_root / ".buildrunner"

        written: list[Path] = []
        merged: list[Path] = []
        skipped: list[Path] = []
        created_dirs: list[Path] = []

        self._mkdir_if_missing(buildrunner_dir, created_dirs)

        for directory_name in _WORKFLOW_DIRECTORIES:
            self._mkdir_if_missing(buildrunner_dir / directory_name, created_dirs)

        scripts_dir = buildrunner_dir / "scripts"
        self._mkdir_if_missing(scripts_dir, created_dirs)

        self._install_structured_files(buildrunner_dir, written, merged, skipped)

        for filename in _SKIP_IF_EXISTS_FILES:
            self._install_skip_if_exists_file(
                buildrunner_dir / filename,
                self._load_template_text(filename),
                written,
                skipped,
            )

        self._install_claude_file(repo_root, written, skipped)
        self._install_skip_if_exists_file(
            buildrunner_dir / "bypass-justification.md",
            _BYPASS_JUSTIFICATION_CONTENT,
            written,
            skipped,
        )
        self._install_skip_if_exists_file(
            scripts_dir / "log-rotation.sh",
            _LOG_ROTATION_STUB,
            written,
            skipped,
            executable=True,
        )

        # Reserved for later phase-specific tailoring.
        _ = declared_facets

        return CoreBaselineResult(
            written=written,
            merged=merged,
            skipped=skipped,
            created_dirs=created_dirs,
        )

    def _mkdir_if_missing(self, path: Path, created_dirs: list[Path]) -> None:
        if not path.exists():
            created_dirs.append(path)
        path.mkdir(parents=True, exist_ok=True)

    def _install_structured_files(
        self,
        buildrunner_dir: Path,
        written: list[Path],
        merged: list[Path],
        skipped: list[Path],
    ) -> None:
        for filename in _STRUCTURED_FILES:
            target_path = buildrunner_dir / filename
            template_data = self._load_template_json(filename)
            if target_path.exists():
                if self._merge_structured_file(target_path, template_data):
                    merged.append(target_path)
                else:
                    skipped.append(target_path)
                continue

            self._write_json(target_path, template_data)
            written.append(target_path)

    def _install_skip_if_exists_file(
        self,
        path: Path,
        content: str,
        written: list[Path],
        skipped: list[Path],
        *,
        executable: bool = False,
    ) -> None:
        if path.exists():
            skipped.append(path)
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if executable:
            path.chmod(0o755)
        written.append(path)

    def _install_claude_file(
        self,
        repo_root: Path,
        written: list[Path],
        skipped: list[Path],
    ) -> None:
        claude_content = self._load_template_text("CLAUDE.md.universal")
        claude_path = repo_root / "CLAUDE.md"
        suggested_claude_path = repo_root / "CLAUDE.md.br3-suggested"
        if not claude_path.exists():
            claude_path.write_text(claude_content, encoding="utf-8")
            written.append(claude_path)
            return

        if claude_path.read_text(encoding="utf-8") == claude_content:
            skipped.append(claude_path)
            return

        if suggested_claude_path.exists():
            skipped.append(suggested_claude_path)
            return

        suggested_claude_path.write_text(claude_content, encoding="utf-8")
        written.append(suggested_claude_path)

    def _merge_structured_file(self, path: Path, template_data: dict[str, Any]) -> bool:
        existing_data = self._load_json_file(path)
        if not isinstance(existing_data, dict):
            raise TypeError(f"Expected top-level JSON object in {path}")

        merged_data = dict(existing_data)
        changed = False
        for key, value in template_data.items():
            if key not in merged_data:
                merged_data[key] = value
                changed = True

        if changed:
            self._write_json(path, merged_data)

        return changed

    def _load_template_json(self, filename: str) -> dict[str, Any]:
        template_path = resolve_asset_path(_BASELINE_TEMPLATE_ROOT / filename)
        data = json.loads(template_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError(f"Expected top-level JSON object in template {template_path}")
        return data

    def _load_template_text(self, filename: str) -> str:
        template_path = resolve_asset_path(_BASELINE_TEMPLATE_ROOT / filename)
        return template_path.read_text(encoding="utf-8")

    def _load_json_file(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
