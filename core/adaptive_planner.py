"""
Adaptive Planner - Intelligent task regeneration based on PRD changes

Listens to PRD change events and:
- Performs differential task generation
- Preserves completed work
- Updates dependency graph incrementally
- Optimizes task queue
- Maintains sub-3s regeneration for 1-2 feature changes
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Optional
import logging
import time

from core.prd.prd_controller import PRDChangeEvent, ChangeType, get_prd_controller
from core.spec_parser import SpecParser
from core.task_decomposer import TaskDecomposer
from core.dependency_graph import DependencyGraph
from core.task_queue import TaskQueue, TaskStatus
from core.priority_scheduler import PriorityScheduler, SchedulingStrategy

logger = logging.getLogger(__name__)


@dataclass
class RegenerationResult:
    """Result of task regeneration"""

    duration_seconds: float
    tasks_generated: int
    tasks_preserved: int
    tasks_updated: int
    affected_features: List[str]
    ready_tasks: List[str]


class AdaptivePlanner:
    """
    Intelligent task planner that responds to PRD changes

    Features:
    - Event-driven regeneration
    - Differential task generation (only changed features)
    - Completed work protection
    - Incremental dependency graph updates
    - Performance-optimized for <3s regeneration
    """

    def __init__(self, project_root: Path, task_queue: TaskQueue):
        self.project_root = Path(project_root)
        self.task_queue = task_queue
        self.task_decomposer = TaskDecomposer()
        self.dependency_graph = DependencyGraph()
        self.scheduler = PriorityScheduler()

        # Track feature-to-tasks mapping for differential updates
        self._feature_task_map: Dict[str, Set[str]] = {}

        # Subscribe to PRD changes
        controller = get_prd_controller()
        controller.subscribe(self.on_prd_change)

        logger.info("Adaptive Planner initialized")

    def on_prd_change(self, event: PRDChangeEvent) -> None:
        """Handle PRD change event"""
        logger.info(f"PRD change detected: {event.event_type.value}")

        try:
            start_time = time.time()
            result = self.regenerate_tasks(event)

            logger.info(
                f"Regeneration complete in {result.duration_seconds:.2f}s: "
                f"{result.tasks_generated} generated, {result.tasks_preserved} preserved"
            )

            # Performance warning if >3s for 1-2 features
            if len(event.affected_features) <= 2 and result.duration_seconds > 3.0:
                logger.warning(
                    f"Regeneration took {result.duration_seconds:.2f}s for "
                    f"{len(event.affected_features)} features (target: <3s)"
                )

        except Exception as e:
            logger.error(f"Error during task regeneration: {e}", exc_info=True)

    def regenerate_tasks(self, event: PRDChangeEvent) -> RegenerationResult:
        """
        Regenerate tasks based on PRD changes

        Strategy:
        1. Identify affected features
        2. Mark old tasks from those features
        3. Generate new tasks for changed features
        4. Update dependency graph incrementally
        5. Re-prioritize task queue
        """
        start_time = time.time()

        # Step 1: Identify tasks to regenerate
        tasks_to_regenerate = self._identify_affected_tasks(event)

        # Step 2: Protect completed work
        tasks_to_preserve, tasks_to_regen = self._separate_by_status(tasks_to_regenerate)

        # Step 3: Remove pending/failed tasks for affected features
        for task_id in tasks_to_regen:
            self.task_queue.remove_task(task_id)
            self.dependency_graph.remove_task(task_id)

        # Step 4: Generate new tasks for affected features
        new_tasks = self._generate_tasks_for_features(event.affected_features, event.full_prd)

        # Step 5: Add new tasks to queue and graph
        tasks_added = 0
        for task in new_tasks:
            try:
                self.task_queue.add_task(
                    task.id, task.name, task.estimated_minutes, task.dependencies
                )
                self.dependency_graph.add_task(task.__dict__)
                tasks_added += 1
            except Exception as e:
                logger.error(f"Error adding task {task.id}: {e}")

        # Step 6: Update feature-task mapping
        for feature_id in event.affected_features:
            self._feature_task_map[feature_id] = {
                t.id for t in new_tasks if t.feature_id == feature_id
            }

        # Step 7: Re-calculate ready tasks
        ready_tasks = self.task_queue.get_ready_tasks()

        duration = time.time() - start_time

        return RegenerationResult(
            duration_seconds=duration,
            tasks_generated=tasks_added,
            tasks_preserved=len(tasks_to_preserve),
            tasks_updated=len(tasks_to_regen),
            affected_features=event.affected_features,
            ready_tasks=[t.id for t in ready_tasks],
        )

    def _identify_affected_tasks(self, event: PRDChangeEvent) -> Set[str]:
        """Identify which tasks are affected by PRD change"""
        affected_tasks = set()

        for feature_id in event.affected_features:
            if feature_id in self._feature_task_map:
                affected_tasks.update(self._feature_task_map[feature_id])

        # If feature was removed, mark all its tasks
        if event.event_type == ChangeType.FEATURE_REMOVED:
            for feature_id in event.affected_features:
                if feature_id in self._feature_task_map:
                    affected_tasks.update(self._feature_task_map[feature_id])
                    del self._feature_task_map[feature_id]

        return affected_tasks

    def _separate_by_status(self, task_ids: Set[str]) -> tuple:
        """Separate tasks into preserved (completed) vs regenerate (pending/failed)"""
        tasks_to_preserve = set()
        tasks_to_regen = set()

        for task_id in task_ids:
            task = self.task_queue.get_task(task_id)
            if task:
                # Preserve completed and in_progress tasks
                if task.status in [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS]:
                    tasks_to_preserve.add(task_id)
                else:
                    tasks_to_regen.add(task_id)
            else:
                # Task not in queue, regenerate
                tasks_to_regen.add(task_id)

        logger.debug(
            f"Task separation: {len(tasks_to_preserve)} preserved, "
            f"{len(tasks_to_regen)} to regenerate"
        )

        return tasks_to_preserve, tasks_to_regen

    def _generate_tasks_for_features(self, feature_ids: List[str], prd) -> List:
        """Generate tasks for specific features"""
        all_tasks = []

        for feature in prd.features:
            if feature.id in feature_ids:
                # Convert PRDFeature to spec_parser Feature format
                spec_feature = {
                    "id": feature.id,
                    "name": feature.name,
                    "description": feature.description,
                    "priority": feature.priority,
                    "requirements": feature.requirements,
                    "acceptance_criteria": feature.acceptance_criteria,
                    "technical_details": feature.technical_details,
                    "dependencies": feature.dependencies,
                }

                # Decompose feature into tasks
                tasks = self.task_decomposer.decompose_feature(spec_feature)
                all_tasks.extend(tasks)

        logger.debug(f"Generated {len(all_tasks)} tasks for {len(feature_ids)} features")

        return all_tasks

    def initial_plan_from_prd(self) -> RegenerationResult:
        """Generate initial task plan from current PRD"""
        start_time = time.time()

        controller = get_prd_controller()
        prd = controller.prd

        # Generate tasks for all features
        all_tasks = []
        for feature in prd.features:
            spec_feature = {
                "id": feature.id,
                "name": feature.name,
                "description": feature.description,
                "priority": feature.priority,
                "requirements": feature.requirements,
                "acceptance_criteria": feature.acceptance_criteria,
                "technical_details": feature.technical_details,
                "dependencies": feature.dependencies,
            }

            tasks = self.task_decomposer.decompose_feature(spec_feature)
            all_tasks.extend(tasks)

            # Update feature-task mapping
            self._feature_task_map[feature.id] = {t.id for t in tasks}

        # Add all tasks to queue and graph
        for task in all_tasks:
            self.task_queue.add_task(task.id, task.name, task.estimated_minutes, task.dependencies)
            self.dependency_graph.add_task(task.__dict__)

        # Get ready tasks
        ready_tasks = self.task_queue.get_ready_tasks()

        duration = time.time() - start_time

        logger.info(
            f"Initial plan generated in {duration:.2f}s: "
            f"{len(all_tasks)} tasks from {len(prd.features)} features"
        )

        return RegenerationResult(
            duration_seconds=duration,
            tasks_generated=len(all_tasks),
            tasks_preserved=0,
            tasks_updated=0,
            affected_features=[f.id for f in prd.features],
            ready_tasks=[t.id for t in ready_tasks],
        )

    def get_execution_plan(self) -> Dict:
        """Get current execution plan with levels and priorities"""
        # Get execution levels from dependency graph
        levels = self.dependency_graph.get_execution_levels()

        # Schedule tasks within levels
        scheduled_tasks = self.scheduler.schedule(
            [self.task_queue.get_task(tid) for level in levels for tid in level.tasks],
            strategy=SchedulingStrategy.CRITICAL_PATH,
        )

        return {
            "total_tasks": len(self.task_queue.tasks),
            "execution_levels": len(levels),
            "ready_tasks": len(self.task_queue.get_ready_tasks()),
            "levels": [
                {
                    "level": level.level,
                    "tasks": level.tasks,
                    "estimated_minutes": level.estimated_minutes,
                }
                for level in levels
            ],
            "scheduled_order": [t.id for t in scheduled_tasks],
        }


def get_adaptive_planner(
    project_root: Optional[Path] = None, task_queue: Optional[TaskQueue] = None
) -> AdaptivePlanner:
    """Get or create adaptive planner instance"""
    if project_root is None:
        project_root = Path.cwd()

    if task_queue is None:
        # Get existing task queue or create new one
        from cli.tasks_commands import get_task_queue

        task_queue = get_task_queue()

    return AdaptivePlanner(project_root, task_queue)
