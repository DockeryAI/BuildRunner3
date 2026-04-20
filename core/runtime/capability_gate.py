"""Explicit BR3-visible capability admission for bounded Codex `/begin` phases."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


PHASE_HEADER_PATTERN = re.compile(r"^### Phase (\d+):\s*(.+?)\s*$", re.MULTILINE)
STATUS_PATTERN = re.compile(r"\*\*Status:\*\*\s*([^\n]+)")
FILES_SECTION_PATTERN = re.compile(
    r"\*\*Files to (?:CREATE|MODIFY|CREATE OR INSTALL):\*\*\s*(.*?)(?=\n\*\*|\n---|\Z)",
    re.DOTALL,
)
PATH_PATTERN = re.compile(r"- `([^`]+)`")

SUBAGENT_PATTERN = re.compile(r"\b(subagent|sub-agent|delegate|parallel|worktree|autopilot)\b", re.IGNORECASE)
BROWSER_PATTERN = re.compile(
    r"\b(browser|browse|web research|perplexity|playwright|mockups?|research)\b",
    re.IGNORECASE,
)
INTERACTIVE_PATTERN = re.compile(
    r"\b(wait for user|ask user|reply with|pick one|choose one|interactive|approval gate|design gate)\b",
    re.IGNORECASE,
)
REMOTE_PATTERN = re.compile(r"\b(cluster|remote node|dispatch|sidecar|ssh|rsync)\b", re.IGNORECASE)

MAX_BOUNDED_FILES = 8


@dataclass
class PhaseCapabilityRecord:
    """Normalized phase metadata extracted from a BUILD document."""

    number: int
    name: str
    status: str
    body: str
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityGateResult:
    """BR3-visible admission decision for one `/begin` phase."""

    phase_number: int
    phase_name: str
    decision: str
    requires: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    fallback_runtime: str | None = None
    bounded: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_build_phases(build_text: str) -> list[PhaseCapabilityRecord]:
    """Parse BUILD phase sections into normalized records."""
    matches = list(PHASE_HEADER_PATTERN.finditer(build_text))
    phases: list[PhaseCapabilityRecord] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(build_text)
        body = build_text[start:end].strip()
        status_match = STATUS_PATTERN.search(body)
        status = status_match.group(1).strip() if status_match else "unknown"
        files = []
        for section in FILES_SECTION_PATTERN.findall(body):
            files.extend(PATH_PATTERN.findall(section))
        deduped_files: list[str] = []
        for item in files:
            if item not in deduped_files:
                deduped_files.append(item)
        phases.append(
            PhaseCapabilityRecord(
                number=int(match.group(1)),
                name=match.group(2).strip(),
                status=status,
                body=body,
                files=deduped_files,
            )
        )
    return phases


def _is_pending_status(status: str) -> bool:
    normalized = str(status).strip().lower()
    return any(token in normalized for token in ("pending", "not_started", "not started", "in_progress", "in progress"))


def pending_build_phases(build_text: str) -> list[PhaseCapabilityRecord]:
    """Return only BUILD phases that are still eligible for `/begin` execution."""
    return [phase for phase in parse_build_phases(build_text) if _is_pending_status(phase.status)]


def evaluate_phase_capabilities(
    phase: PhaseCapabilityRecord,
    *,
    runtime_name: str,
    runtime_capabilities: dict[str, object],
) -> CapabilityGateResult:
    """Decide whether a phase can run in bounded Codex `/begin` mode."""
    requires: list[str] = []
    unsupported: list[str] = []
    notes: list[str] = []
    body = phase.body

    if SUBAGENT_PATTERN.search(body):
        requires.append("subagents")
        if not runtime_capabilities.get("subagents", False):
            unsupported.append("subagents")
            notes.append("Phase text requires subagents/parallel delegation, which Codex Phase 11 does not allow.")

    if BROWSER_PATTERN.search(body):
        requires.append("browser")
        if not runtime_capabilities.get("browser", False):
            unsupported.append("browser")
            notes.append("Phase text requires browser-style research/design behavior, which is still Claude-first.")

    if INTERACTIVE_PATTERN.search(body):
        requires.append("rich_interactivity")
        unsupported.append("rich_interactivity")
        notes.append("Phase text requires rich interactive prompts beyond BR3-owned lock and approval gates.")

    if REMOTE_PATTERN.search(body):
        requires.append("remote_dispatch")
        unsupported.append("remote_dispatch")
        notes.append("Phase text depends on remote/cluster dispatch, which is outside Phase 11 local `/begin` scope.")

    bounded = len(phase.files) <= MAX_BOUNDED_FILES
    if not bounded:
        notes.append(
            f"Phase touches {len(phase.files)} files, which exceeds the bounded Phase 11 threshold of {MAX_BOUNDED_FILES}."
        )

    if runtime_name != "codex":
        return CapabilityGateResult(
            phase_number=phase.number,
            phase_name=phase.name,
            decision="allow",
            requires=requires,
            bounded=bounded,
            notes=notes,
        )

    if unsupported:
        return CapabilityGateResult(
            phase_number=phase.number,
            phase_name=phase.name,
            decision="handoff_to_claude",
            requires=requires,
            unsupported=sorted(set(unsupported)),
            fallback_runtime="claude",
            bounded=bounded,
            notes=notes,
        )

    if not bounded:
        return CapabilityGateResult(
            phase_number=phase.number,
            phase_name=phase.name,
            decision="refuse",
            requires=requires,
            unsupported=[],
            fallback_runtime=None,
            bounded=False,
            notes=notes,
        )

    if not runtime_capabilities.get("execution", False):
        return CapabilityGateResult(
            phase_number=phase.number,
            phase_name=phase.name,
            decision="refuse",
            requires=requires,
            unsupported=["execution"],
            fallback_runtime=None,
            bounded=bounded,
            notes=["Runtime does not advertise execution support for `/begin`."],
        )

    return CapabilityGateResult(
        phase_number=phase.number,
        phase_name=phase.name,
        decision="allow",
        requires=requires,
        unsupported=[],
        bounded=bounded,
        notes=notes or ["Phase passed the bounded Codex `/begin` admission gate."],
    )
