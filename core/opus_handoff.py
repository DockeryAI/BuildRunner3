"""
Opus Handoff Protocol - Strategic to Tactical Model Switching

Optimizes handoff from Opus (strategic planning) to Sonnet (tactical execution)
by creating compact, well-structured context for build execution.
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

from .prd_parser import PRDParser, ParsedSpec


@dataclass
class HandoffPackage:
    """Complete handoff package from Opus to Sonnet"""
    project_summary: str
    technical_decisions: List[str]
    build_instructions: List[Dict]
    atomic_tasks: List[Dict]
    context_files: List[str]
    success_criteria: List[str]


class OpusHandoff:
    """
    Optimize Opus → Sonnet handoff for build execution.

    Features:
    - Create compact context from PROJECT_SPEC
    - Generate atomic task lists
    - Identify key decision points
    - Build execution-ready instructions
    - Minimize context while preserving critical info
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.spec_path = self.project_root / ".buildrunner" / "PROJECT_SPEC.md"

    def create_handoff_package(self, spec: Optional[ParsedSpec] = None) -> HandoffPackage:
        """
        Create complete handoff package from PROJECT_SPEC.

        If spec not provided, parses from disk.
        """
        if not spec:
            parser = PRDParser(str(self.spec_path))
            spec = parser.parse()

        # Generate project summary
        project_summary = self._generate_project_summary(spec)

        # Extract technical decisions
        technical_decisions = self._extract_technical_decisions(spec)

        # Generate build instructions
        build_instructions = self._generate_build_instructions(spec)

        # Generate atomic tasks
        atomic_tasks = self._generate_atomic_tasks(spec)

        # Identify context files
        context_files = self._identify_context_files()

        # Define success criteria
        success_criteria = self._define_success_criteria(spec)

        return HandoffPackage(
            project_summary=project_summary,
            technical_decisions=technical_decisions,
            build_instructions=build_instructions,
            atomic_tasks=atomic_tasks,
            context_files=context_files,
            success_criteria=success_criteria
        )

    def _generate_project_summary(self, spec: ParsedSpec) -> str:
        """Generate concise project summary"""
        summary = f"""Project: {spec.industry} {spec.use_case} Application

Tech Stack: {spec.tech_stack}
Features: {len(spec.features)}
Phases: {len(spec.phases)}

This project builds a {spec.use_case} for the {spec.industry} industry.
"""

        if spec.features:
            summary += f"\nKey Features:\n"
            for feature in spec.features[:5]:  # Top 5
                summary += f"- {feature.description}\n"

        return summary

    def _extract_technical_decisions(self, spec: ParsedSpec) -> List[str]:
        """Extract key technical decisions"""
        decisions = []

        if spec.tech_stack:
            decisions.append(f"Tech Stack: {spec.tech_stack}")

        if spec.dependencies:
            decisions.append(f"Dependencies: {', '.join(list(spec.dependencies)[:10])}")

        if spec.industry:
            decisions.append(f"Industry Requirements: {spec.industry}-specific compliance")

        return decisions

    def _generate_build_instructions(self, spec: ParsedSpec) -> List[Dict]:
        """Generate step-by-step build instructions"""
        instructions = []

        # Phase-based instructions
        for phase in spec.phases:
            instruction = {
                "phase": phase.number,
                "name": phase.name,
                "duration": phase.duration,
                "features": phase.features,
                "steps": [
                    "Setup environment",
                    "Implement features",
                    "Write tests",
                    "Integration testing",
                    "Deploy"
                ]
            }
            instructions.append(instruction)

        # If no phases, create default instruction
        if not instructions:
            instructions.append({
                "phase": 1,
                "name": "Initial Implementation",
                "steps": [
                    "Setup project structure",
                    "Implement core features",
                    "Write comprehensive tests",
                    "Document code"
                ]
            })

        return instructions

    def _generate_atomic_tasks(self, spec: ParsedSpec) -> List[Dict]:
        """Generate atomic, executable tasks"""
        tasks = []

        for i, feature in enumerate(spec.features):
            # Break down each feature into atomic tasks
            task_id = f"task_{i+1}"

            tasks.append({
                "id": f"{task_id}_design",
                "description": f"Design {feature.name}",
                "estimated_time": "30 minutes",
                "dependencies": []
            })

            tasks.append({
                "id": f"{task_id}_implement",
                "description": f"Implement {feature.name}",
                "estimated_time": "2 hours",
                "dependencies": [f"{task_id}_design"]
            })

            tasks.append({
                "id": f"{task_id}_test",
                "description": f"Test {feature.name}",
                "estimated_time": "1 hour",
                "dependencies": [f"{task_id}_implement"]
            })

        return tasks

    def _identify_context_files(self) -> List[str]:
        """Identify relevant context files for Sonnet"""
        context_files = []

        # Check for existing context files
        context_dir = self.project_root / ".buildrunner" / "context"

        if context_dir.exists():
            for file in context_dir.glob("*.md"):
                context_files.append(str(file.relative_to(self.project_root)))

        # Add spec file
        if self.spec_path.exists():
            context_files.append(str(self.spec_path.relative_to(self.project_root)))

        return context_files

    def _define_success_criteria(self, spec: ParsedSpec) -> List[str]:
        """Define success criteria for build"""
        criteria = [
            "All features implemented",
            "All tests pass (85%+ coverage)",
            "Code passes quality gates",
            "Documentation complete",
            "No security vulnerabilities"
        ]

        if spec.industry == 'healthcare':
            criteria.append("HIPAA compliance verified")
        elif spec.industry == 'fintech':
            criteria.append("Security audit passed")

        return criteria

    def export_handoff(self, package: HandoffPackage, output_path: str):
        """Export handoff package to file"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "project_summary": package.project_summary,
            "technical_decisions": package.technical_decisions,
            "build_instructions": package.build_instructions,
            "atomic_tasks": package.atomic_tasks,
            "context_files": package.context_files,
            "success_criteria": package.success_criteria
        }

        with open(output, 'w') as f:
            json.dump(data, f, indent=2)

    def generate_sonnet_prompt(self, package: HandoffPackage) -> str:
        """Generate optimized prompt for Sonnet"""
        prompt = f"""# Build Execution Instructions

{package.project_summary}

## Technical Decisions
{chr(10).join(f'- {d}' for d in package.technical_decisions)}

## Build Plan
{len(package.build_instructions)} phases

Phase 1: {package.build_instructions[0]['name'] if package.build_instructions else 'Implementation'}

## Atomic Tasks
{len(package.atomic_tasks)} tasks to complete

First 3 tasks:
"""

        for task in package.atomic_tasks[:3]:
            prompt += f"- {task['description']} ({task['estimated_time']})\n"

        prompt += f"""

## Context Files
{chr(10).join(f'- {f}' for f in package.context_files)}

## Success Criteria
{chr(10).join(f'- {c}' for c in package.success_criteria)}

Execute this build plan following the atomic tasks in sequence.
"""

        return prompt


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python opus_handoff.py <project_root>")
        sys.exit(1)

    project_root = sys.argv[1]

    handoff = OpusHandoff(project_root)

    print("\nCreating Opus → Sonnet handoff package...")
    package = handoff.create_handoff_package()

    print(f"\nHandoff Package Created:")
    print(f"  Technical Decisions: {len(package.technical_decisions)}")
    print(f"  Build Instructions: {len(package.build_instructions)} phases")
    print(f"  Atomic Tasks: {len(package.atomic_tasks)}")
    print(f"  Context Files: {len(package.context_files)}")
    print(f"  Success Criteria: {len(package.success_criteria)}")

    # Generate Sonnet prompt
    prompt = handoff.generate_sonnet_prompt(package)
    print(f"\nGenerated Sonnet Prompt: {len(prompt)} characters")


if __name__ == "__main__":
    main()
