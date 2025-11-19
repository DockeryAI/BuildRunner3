"""
Build Management Commands - CLI commands for build orchestration, checkpoints, and rollback

Commands:
- br build checkpoint <name> - Create a named checkpoint
- br build rollback <checkpoint-id> - Rollback to a specific checkpoint
- br build resume [checkpoint-id] - Resume from checkpoint (latest if not specified)
- br build list-checkpoints - List all checkpoints
- br build status - Show current build state
- br build analyze - Analyze build dependencies and execution plan
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Optional
from datetime import datetime
from dataclasses import asdict

from core.build_orchestrator import BuildOrchestrator, BuildPhase
from core.checkpoint_manager import CheckpointManager
from core.task_queue import TaskQueue
from cli.tasks_commands import get_task_queue, save_task_queue

build_app = typer.Typer(help="Build orchestration and checkpoint management")
console = Console()


def convert_to_batch_task(decomp_task):
    """Convert task_decomposer.Task to batch_optimizer.Task"""
    from core.batch_optimizer import Task as BatchTask, TaskDomain, TaskComplexity as BatchComplexity

    # Map category to domain
    category_to_domain = {
        "implementation": TaskDomain.BACKEND,
        "testing": TaskDomain.TESTING,
        "documentation": TaskDomain.DOCUMENTATION,
    }
    domain = category_to_domain.get(decomp_task.category, TaskDomain.UNKNOWN)

    # Map complexity string to BatchComplexity enum
    complexity_map = {
        "simple": BatchComplexity.SIMPLE,
        "medium": BatchComplexity.MEDIUM,
        "complex": BatchComplexity.COMPLEX,
    }
    complexity_str = decomp_task.complexity.value if hasattr(decomp_task.complexity, 'value') else str(decomp_task.complexity)
    complexity = complexity_map.get(complexity_str, BatchComplexity.MEDIUM)

    # Infer file_path from technical details or use placeholder
    file_path = f"core/{decomp_task.feature_id}/{decomp_task.id}.py"

    return BatchTask(
        id=decomp_task.id,
        name=decomp_task.name,
        description=decomp_task.description,
        file_path=file_path,
        estimated_minutes=decomp_task.estimated_minutes,
        complexity=complexity,
        domain=domain,
        dependencies=decomp_task.dependencies,
        acceptance_criteria=decomp_task.acceptance_criteria,
    )


def get_orchestrator() -> BuildOrchestrator:
    """Get or create build orchestrator"""
    project_root = Path.cwd()
    queue = get_task_queue()
    return BuildOrchestrator(project_root, queue)


@build_app.command("checkpoint")
def create_checkpoint(
    name: str = typer.Argument(..., help="Checkpoint name"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Checkpoint description")
):
    """
    Create a named checkpoint of current build state

    Example:
        br build checkpoint batch1_complete -m "Completed Batch 1 implementation"
    """
    try:
        console.print(f"\n[bold blue]Creating checkpoint: {name}[/bold blue]\n")

        orchestrator = get_orchestrator()

        # Create metadata
        metadata = {
            "name": name,
            "description": message or f"Checkpoint: {name}",
            "created_by": "cli",
            "timestamp": datetime.now().isoformat()
        }

        # Create checkpoint
        checkpoint_id = orchestrator.create_checkpoint(
            phase=name,
            metadata=metadata
        )

        # Get progress info
        progress = orchestrator.get_build_progress()

        console.print(f"[green]✓ Checkpoint created: {checkpoint_id}[/green]\n")
        console.print(f"  Phase: {name}")
        console.print(f"  Tasks completed: {progress['tasks_completed']}/{progress['tasks_total']}")
        console.print(f"  Files created: {progress['files_created']}")
        console.print(f"  Progress: {progress['progress_percent']:.1f}%\n")

        if message:
            console.print(f"  Message: {message}\n")

    except Exception as e:
        console.print(f"[red]❌ Error creating checkpoint: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("rollback")
def rollback_checkpoint(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID to rollback to")
):
    """
    Rollback build to a specific checkpoint

    Example:
        br build rollback checkpoint_20251117_142530_123456
    """
    try:
        console.print(f"\n[bold yellow]⚠️  Rolling back to checkpoint: {checkpoint_id}[/bold yellow]\n")

        orchestrator = get_orchestrator()
        checkpoint_manager = CheckpointManager(Path.cwd())

        # Get checkpoint info
        checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
        if not checkpoint:
            console.print(f"[red]❌ Checkpoint not found: {checkpoint_id}[/red]")
            raise typer.Exit(1)

        # Show what will be affected
        files_to_remove = checkpoint_manager.get_files_to_rollback(checkpoint_id)

        console.print(f"[bold]Checkpoint details:[/bold]")
        console.print(f"  Phase: {checkpoint.phase}")
        console.print(f"  Created: {checkpoint.timestamp}")
        console.print(f"  Tasks completed: {len(checkpoint.tasks_completed)}")
        console.print(f"  Files at checkpoint: {len(checkpoint.files_created)}\n")

        if files_to_remove:
            console.print(f"[yellow]⚠️  Files created after this checkpoint (will need manual cleanup):[/yellow]")
            for file in files_to_remove[:5]:
                console.print(f"    • {file}")
            if len(files_to_remove) > 5:
                console.print(f"    ... and {len(files_to_remove) - 5} more")
            console.print()

        # Confirm
        if not typer.confirm("Continue with rollback?", default=False):
            console.print("[yellow]Rollback cancelled[/yellow]")
            raise typer.Exit(0)

        # Perform rollback
        success = orchestrator.rollback_to_checkpoint(checkpoint_id)

        if success:
            # Update task queue
            queue = get_task_queue()
            save_task_queue(queue)

            console.print(f"\n[green]✓ Rolled back to checkpoint: {checkpoint_id}[/green]")
            console.print(f"  Phase restored: {checkpoint.phase}")
            console.print(f"  Tasks restored: {len(checkpoint.tasks_completed)}\n")

            if files_to_remove:
                console.print("[yellow]⚠️  Note: Files created after checkpoint still exist on disk[/yellow]")
                console.print("[dim]You may need to manually remove them[/dim]\n")
        else:
            console.print(f"[red]❌ Rollback failed[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error during rollback: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("resume")
def resume_from_checkpoint(
    checkpoint_id: Optional[str] = typer.Argument(None, help="Checkpoint ID to resume from (latest if not specified)")
):
    """
    Resume build from a checkpoint

    Example:
        br build resume                                    # Resume from latest
        br build resume checkpoint_20251117_142530_123456  # Resume from specific
    """
    try:
        console.print(f"\n[bold blue]Resuming build from checkpoint...[/bold blue]\n")

        orchestrator = get_orchestrator()
        checkpoint_manager = CheckpointManager(Path.cwd())

        # Get checkpoint
        if checkpoint_id:
            checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
            if not checkpoint:
                console.print(f"[red]❌ Checkpoint not found: {checkpoint_id}[/red]")
                raise typer.Exit(1)
        else:
            checkpoint = checkpoint_manager.get_latest_checkpoint()
            if not checkpoint:
                console.print("[yellow]No checkpoints found. Nothing to resume.[/yellow]")
                raise typer.Exit(1)
            checkpoint_id = checkpoint.id

        # Resume
        success = orchestrator.resume_from_checkpoint(checkpoint_id)

        if success:
            console.print(f"[green]✓ Resumed from checkpoint: {checkpoint_id}[/green]\n")
            console.print(f"  Phase: {checkpoint.phase}")
            console.print(f"  Created: {checkpoint.timestamp}")
            console.print(f"  Tasks completed: {len(checkpoint.tasks_completed)}")
            console.print(f"  Files tracked: {len(checkpoint.files_created)}\n")

            # Show next steps
            queue = get_task_queue()
            ready_tasks = queue.get_ready_tasks()

            if ready_tasks:
                console.print(f"[bold]Next steps:[/bold]")
                console.print(f"  {len(ready_tasks)} tasks ready to execute")
                console.print(f"[dim]Run 'br run auto' to continue[/dim]\n")
            else:
                console.print(f"[yellow]No ready tasks. Build may be complete or blocked.[/yellow]\n")
        else:
            console.print(f"[red]❌ Resume failed[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error resuming: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("list-checkpoints")
def list_checkpoints():
    """
    List all checkpoints

    Example:
        br build list-checkpoints
    """
    try:
        console.print("\n[bold blue]📋 Build Checkpoints[/bold blue]\n")

        checkpoint_manager = CheckpointManager(Path.cwd())
        checkpoints = checkpoint_manager.list_checkpoints()

        if not checkpoints:
            console.print("[yellow]No checkpoints found[/yellow]\n")
            return

        # Create table
        table = Table(title=f"Checkpoints ({len(checkpoints)} total)")
        table.add_column("ID", style="cyan")
        table.add_column("Phase", style="blue")
        table.add_column("Created", style="green")
        table.add_column("Tasks", justify="right")
        table.add_column("Files", justify="right")
        table.add_column("Status", style="yellow")

        for cp in checkpoints:
            # Format timestamp
            try:
                dt = datetime.fromisoformat(cp.timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = cp.timestamp

            table.add_row(
                cp.id[-20:],  # Show last 20 chars of ID
                cp.phase,
                time_str,
                str(len(cp.tasks_completed)),
                str(len(cp.files_created)),
                cp.status.value
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]❌ Error listing checkpoints: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("start")
def build_start(
    continuous: bool = typer.Option(True, "--continuous/--no-continuous", help="Enable continuous phase execution"),
):
    """
    Start automated build from PROJECT_SPEC.md

    Reads PROJECT_SPEC, generates tasks, creates execution plan, and launches Claude Code.

    With --continuous (default), loops through all phases without pausing.
    Use --no-continuous for traditional phase-by-phase execution.

    Example:
        br build start                  # Continuous mode (default)
        br build start --no-continuous  # Phase-by-phase mode
    """
    try:
        console.print("\n[bold blue]🚀 Starting Build Orchestration[/bold blue]\n")

        project_root = Path.cwd()
        spec_path = project_root / ".buildrunner" / "PROJECT_SPEC.md"

        # Check if spec exists
        if not spec_path.exists():
            console.print("[red]❌ PROJECT_SPEC.md not found[/red]")
            console.print("[dim]Run 'br spec wizard' to create it first[/dim]\n")
            raise typer.Exit(1)

        # Parse spec
        console.print("[cyan]📋 Parsing PROJECT_SPEC.md...[/cyan]")
        from core.spec_parser import SpecParser
        parser = SpecParser()
        spec_result = parser.parse_spec(str(spec_path))
        features = spec_result['features']
        console.print(f"[green]✓ Found {len(features)} features[/green]\n")

        # Decompose into tasks
        console.print("[cyan]🔨 Decomposing features into tasks...[/cyan]")
        from core.task_decomposer import TaskDecomposer
        decomposer = TaskDecomposer()

        all_tasks = []
        for feature in features:
            tasks = decomposer.decompose_feature(feature)
            all_tasks.extend(tasks)

        console.print(f"[green]✓ Generated {len(all_tasks)} atomic tasks[/green]\n")

        # Create task lookup dict (id -> Task object)
        task_lookup = {task.id: task for task in all_tasks}

        # Build dependency graph
        console.print("[cyan]🔗 Building dependency graph...[/cyan]")
        from core.dependency_graph import DependencyGraph
        graph = DependencyGraph()
        for task in all_tasks:
            graph.add_task(asdict(task))

        # Get execution levels
        levels = graph.get_execution_levels()
        console.print(f"[green]✓ {len(levels)} execution levels identified[/green]\n")

        # Create batches
        console.print("[cyan]📦 Creating task batches...[/cyan]")
        from core.batch_optimizer import BatchOptimizer
        optimizer = BatchOptimizer()

        batches = []
        for level in levels:
            level_tasks_decomp = [task_lookup[task_id] for task_id in level.tasks]
            level_tasks_batch = [convert_to_batch_task(t) for t in level_tasks_decomp]
            level_batches = optimizer.optimize_batches(level_tasks_batch)
            batches.extend(level_batches)

        console.print(f"[green]✓ Created {len(batches)} task batches[/green]\n")

        # Create EXECUTION.md for Claude Code
        execution_path = project_root / ".buildrunner" / "EXECUTION.md"

        # Build execution content
        execution_content = f"""# 🚀 EXECUTION MODE ACTIVE

**Project:** {project_root.name}
**Status:** Build in progress
**Tasks:** {len(all_tasks)} total

---

## Your Task

You are Claude Code in **EXECUTION MODE**. Execute the tasks below in order, following the batch structure.

### Current Batch: Batch 1 of {len(batches)}

{_format_batch(batches[0], graph)}

### Instructions

1. **Read** each task description carefully
2. **Implement** the code exactly as specified
3. **Write** tests for each component
4. **Verify** acceptance criteria are met
5. **Use** BuildRunner MCP tools to update status:
   - `feature_update` - Mark features in_progress/complete
   - `status_generate` - Generate STATUS.md after each feature
6. **Report** when batch is complete

### After Completion

When this batch is complete, tell the user:
"Batch 1 complete. Run `br build next` to continue."

---

## All Batches Overview

{_format_all_batches_summary(batches)}

---

## Quality Standards

- Write tests for all code
- Follow existing code patterns
- Update documentation
- No hardcoded secrets
- Pass all quality gates

"""

        execution_path.write_text(execution_content)
        console.print(f"[green]✓ Created {execution_path}[/green]\n")

        # Save orchestration state
        orch_state = {
            "batches": [{"id": i, "tasks": [t.id for t in b.tasks]} for i, b in enumerate(batches)],
            "current_batch": 0,
            "total_tasks": len(all_tasks),
            "completed_tasks": 0,
            "continuous_mode": continuous
        }

        state_path = project_root / ".buildrunner" / "orchestration_state.json"
        import json
        state_path.write_text(json.dumps(orch_state, indent=2))

        # Show mode info
        if continuous:
            console.print("[cyan]📡 Continuous mode enabled - will loop through all phases[/cyan]")
            console.print("[dim]Build will only pause for blockers (credentials, test failures, etc.)[/dim]\n")
        else:
            console.print("[cyan]📋 Phase-by-phase mode - will pause between phases[/cyan]\n")

        # Launch Claude Code
        console.print("[green]✅ Build orchestration initialized![/green]")
        console.print("[green]✅ Starting Claude Code in execution mode...[/green]\n")

        # Replace this process with claude CLI
        import os
        os.execvp('claude', ['claude', '--dangerously-skip-permissions', str(project_root)])

    except Exception as e:
        console.print(f"[red]❌ Error starting build: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


def _format_batch(batch, graph):
    """Format a batch for EXECUTION.md"""
    content = []
    for i, task in enumerate(batch.tasks, 1):
        content.append(f"#### Task {i}: {task.name}")
        content.append(f"**Description:** {task.description}")
        content.append(f"**Estimated Time:** {task.estimated_minutes} minutes")
        content.append(f"**File:** {task.file_path}")
        if task.dependencies:
            deps = []
            for dep_id in task.dependencies:
                if dep_id in graph.tasks:
                    deps.append(graph.tasks[dep_id].get('name', dep_id))
            if deps:
                content.append(f"**Dependencies:** {', '.join(deps)}")
        if task.acceptance_criteria:
            content.append(f"**Acceptance Criteria:**")
            for criterion in task.acceptance_criteria:
                content.append(f"  - {criterion}")
        content.append("")

    return "\n".join(content)


def _format_all_batches_summary(batches):
    """Format summary of all batches"""
    lines = []
    for i, batch in enumerate(batches, 1):
        task_count = len(batch.tasks)
        total_time = sum(t.estimated_minutes for t in batch.tasks)
        lines.append(f"- **Batch {i}:** {task_count} tasks (~{total_time} min)")
    return "\n".join(lines)


@build_app.command("next")
def build_next():
    """
    Continue to next batch

    Example:
        br build next
    """
    try:
        project_root = Path.cwd()
        state_path = project_root / ".buildrunner" / "orchestration_state.json"

        if not state_path.exists():
            console.print("[red]❌ No active build. Run 'br build start' first.[/red]")
            raise typer.Exit(1)

        import json
        state = json.loads(state_path.read_text())

        state["current_batch"] += 1

        if state["current_batch"] >= len(state["batches"]):
            console.print("\n[green]🎉 All batches complete![/green]\n")
            console.print("[bold]Next steps:[/bold]")
            console.print("  1. Run 'br quality check' to verify")
            console.print("  2. Run 'br status generate' for final report")
            raise typer.Exit(0)

        # Update EXECUTION.md for next batch
        console.print(f"\n[bold blue]📦 Loading Batch {state['current_batch'] + 1}...[/bold blue]\n")

        # Save state
        state_path.write_text(json.dumps(state, indent=2))

        # Launch Claude Code again
        import os
        os.execvp('claude', ['claude', '--dangerously-skip-permissions', str(project_root)])

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("status")
def build_status():
    """
    Show current build state

    Example:
        br build status
    """
    try:
        console.print("\n[bold blue]🔨 Build Status[/bold blue]\n")

        orchestrator = get_orchestrator()
        progress = orchestrator.get_build_progress()

        # Build state panel
        if progress['phase'] == 'not_started':
            console.print("[yellow]Build not started[/yellow]\n")
            console.print("[dim]Run 'br run auto' to start orchestrated build[/dim]\n")
            return

        # Status table
        table = Table(title="Build Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Phase", progress['phase'])
        table.add_row("Status", progress['status'])
        table.add_row("Progress", f"{progress['progress_percent']:.1f}%")
        table.add_row("Tasks Completed", f"{progress['tasks_completed']}/{progress['tasks_total']}")
        table.add_row("Tasks In Progress", str(progress['tasks_in_progress']))
        table.add_row("Tasks Pending", str(progress['tasks_pending']))
        table.add_row("Files Created", str(progress['files_created']))

        if progress.get('checkpoint_id'):
            table.add_row("Latest Checkpoint", progress['checkpoint_id'][-20:])

        console.print(table)
        console.print()

        # Recommendations
        if progress['progress_percent'] < 100:
            console.print("[bold]Next actions:[/bold]")
            console.print("  • Run 'br run auto' to continue orchestration")
            console.print("  • Run 'br build checkpoint <name>' to save current state")
            console.print()
        else:
            console.print("[green]✓ Build complete![/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error getting build status: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("phase-status")
def phase_status():
    """
    Show continuous build phase status

    Example:
        br build phase-status
    """
    try:
        console.print("\n[bold blue]🔄 Continuous Build Phase Status[/bold blue]\n")

        project_root = Path.cwd()
        from core.phase_manager import PhaseManager

        phase_manager = PhaseManager(project_root)
        progress = phase_manager.get_progress()

        # Phase status table
        table = Table(title="Phase Execution Progress")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Duration", justify="right")

        for phase_name, phase_info in progress["phases"].items():
            status = phase_info["status"]
            duration = phase_info.get("duration_seconds")

            # Format status with color
            status_display = status
            if status == "completed":
                status_display = f"[green]✓ {status}[/green]"
            elif status == "in_progress":
                status_display = f"[yellow]⏳ {status}[/yellow]"
            elif status == "blocked":
                status_display = f"[red]🚫 {status}[/red]"
            elif status == "failed":
                status_display = f"[red]❌ {status}[/red]"

            duration_str = f"{duration:.1f}s" if duration else "-"

            table.add_row(phase_name, status_display, duration_str)

        console.print(table)
        console.print()

        # Overall progress
        console.print(f"[bold]Overall Progress:[/bold]")
        console.print(f"  Current Phase: {progress['current_phase']}")
        console.print(f"  Completed: {progress['completed_phases']}/{progress['total_phases']}")
        console.print(f"  Progress: {progress['progress_percent']:.1f}%")
        console.print(f"  Continuous Mode: {'✓ Enabled' if progress['continuous_mode'] else '✗ Disabled'}\n")

        # Blockers
        if progress["is_blocked"]:
            console.print(f"[red]⚠️  {progress['active_blockers']} active blocker(s)[/red]")
            blockers = phase_manager.get_active_blockers()
            for blocker in blockers:
                console.print(f"  • {blocker.blocker_type.value}: {blocker.description}")
            console.print()
            console.print("[dim]Clear blockers with 'br build clear-blocker'[/dim]\n")
        else:
            console.print("[green]✓ No active blockers[/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error getting phase status: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("clear-blocker")
def clear_blocker(
    blocker_type: str = typer.Argument(..., help="Blocker type to clear (e.g., missing_credentials)")
):
    """
    Clear a blocker to resume execution

    Example:
        br build clear-blocker missing_credentials
    """
    try:
        console.print(f"\n[bold blue]Clearing blocker: {blocker_type}[/bold blue]\n")

        project_root = Path.cwd()
        from core.phase_manager import PhaseManager, BlockerType

        phase_manager = PhaseManager(project_root)

        # Convert string to BlockerType
        try:
            blocker_enum = BlockerType(blocker_type)
        except ValueError:
            console.print(f"[red]❌ Invalid blocker type: {blocker_type}[/red]")
            console.print(f"[dim]Valid types: {', '.join([b.value for b in BlockerType if b != BlockerType.NONE])}[/dim]\n")
            raise typer.Exit(1)

        # Clear blocker
        if phase_manager.clear_blocker(blocker_enum):
            console.print(f"[green]✓ Blocker cleared: {blocker_type}[/green]\n")

            # Show next steps
            if not phase_manager.is_blocked():
                console.print("[bold]Next steps:[/bold]")
                console.print("  Run 'br build resume' to continue execution\n")
        else:
            console.print(f"[yellow]No active blocker of type: {blocker_type}[/yellow]\n")

    except Exception as e:
        console.print(f"[red]❌ Error clearing blocker: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("analyze")
def analyze_dependencies():
    """
    Analyze build dependencies and execution plan

    Shows DAG analysis, parallel execution opportunities, and critical path.

    Example:
        br build analyze
    """
    try:
        console.print("\n[bold blue]📊 Build Dependency Analysis[/bold blue]\n")

        orchestrator = get_orchestrator()

        # Get dependency analysis
        analysis = orchestrator.analyze_dependencies()

        # Summary stats
        console.print("[bold]Execution Plan:[/bold]")
        console.print(f"  Total execution levels: {analysis['total_levels']}")
        console.print(f"  Critical path duration: ~{analysis['critical_path_duration']} minutes")
        console.print(f"  Critical path tasks: {len(analysis['critical_path'])}\n")

        # Parallel opportunities
        if analysis['parallelizable_tasks']:
            console.print("[bold]Parallel Execution Opportunities:[/bold]")
            for opp in analysis['parallelizable_tasks']:
                console.print(f"  Level {opp['level']}: {opp['count']} tasks can run in parallel")
            console.print()
        else:
            console.print("[yellow]No parallel execution opportunities found[/yellow]\n")

        # Critical path
        if analysis['critical_path']:
            console.print("[bold]Critical Path:[/bold]")
            for task_id in analysis['critical_path'][:10]:
                console.print(f"  → {task_id}")
            if len(analysis['critical_path']) > 10:
                console.print(f"  ... and {len(analysis['critical_path']) - 10} more")
            console.print()

        # Execution levels detail
        if typer.confirm("\nShow detailed execution levels?", default=False):
            console.print("\n[bold]Execution Levels:[/bold]")
            for level in analysis['execution_levels']:
                console.print(f"\n  Level {level.level} ({level.estimated_minutes} min):")
                for task_id in level.tasks:
                    console.print(f"    • {task_id}")

    except Exception as e:
        console.print(f"[red]❌ Error analyzing dependencies: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    build_app()
