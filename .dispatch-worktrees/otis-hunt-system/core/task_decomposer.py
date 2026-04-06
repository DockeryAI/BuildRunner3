"""
Task Decomposer - Break features into atomic 1-2 hour tasks

Decomposes features from PROJECT_SPEC.md into:
- Atomic tasks (1-2 hours each)
- Complexity scores (simple/medium/complex)
- Duration estimates (60/90/120 minutes)
- Specific acceptance criteria

Supports common patterns:
- Database models
- API endpoints
- Business logic
- UI components
- Tests
- Documentation
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TaskComplexity(str, Enum):
    """Task complexity levels"""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class Task:
    """Represents an atomic task"""

    id: str
    name: str
    description: str
    feature_id: str
    complexity: TaskComplexity
    estimated_minutes: int
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    category: str = "implementation"  # implementation, testing, documentation
    technical_details: List[str] = field(default_factory=list)


class TaskDecomposer:
    """
    Break features into atomic 1-2 hour tasks

    Features:
    - Decompose features into implementation steps
    - Estimate complexity and duration
    - Generate specific acceptance criteria
    - Identify task dependencies
    """

    # Duration mapping (in minutes)
    DURATION_MAP = {
        TaskComplexity.SIMPLE: 60,
        TaskComplexity.MEDIUM: 90,
        TaskComplexity.COMPLEX: 120,
    }

    # Task patterns by complexity keywords
    COMPLEXITY_INDICATORS = {
        "simple": ["crud", "basic", "simple", "straightforward", "minimal"],
        "complex": [
            "algorithm",
            "optimization",
            "security",
            "authentication",
            "authorization",
            "payment",
            "real-time",
            "sync",
            "migration",
            "integration",
            "workflow",
            "state machine",
        ],
        "medium": [],  # Default fallback
    }

    def __init__(self):
        """Initialize TaskDecomposer"""
        self.task_counter = 0

    def decompose_feature(self, feature: Dict[str, Any]) -> List[Task]:
        """
        Break feature into atomic 1-2 hour tasks

        Args:
            feature: Feature dict from SpecParser with:
                - id, name, description
                - requirements, dependencies
                - acceptance_criteria, technical_details

        Returns:
            List of Task objects
        """
        tasks = []

        feature_id = feature["id"]
        feature_name = feature["name"]
        requirements = feature.get("requirements", [])
        technical_details = feature.get("technical_details", [])
        acceptance_criteria = feature.get("acceptance_criteria", [])

        # Determine task breakdown pattern
        task_breakdown = self._determine_task_breakdown(feature, requirements, technical_details)

        # Create tasks for each component
        for task_type, task_details in task_breakdown.items():
            task = self._create_task(
                feature_id=feature_id,
                feature_name=feature_name,
                task_type=task_type,
                task_details=task_details,
                requirements=requirements,
            )

            if task:
                tasks.append(task)

        # Add testing task if feature has significant implementation
        if len(tasks) >= 2:
            test_task = self._create_test_task(feature_id, feature_name, tasks)
            tasks.append(test_task)

        # Add documentation task if complex
        if self._needs_documentation(feature):
            doc_task = self._create_documentation_task(feature_id, feature_name)
            tasks.append(doc_task)

        return tasks

    def estimate_complexity(self, task: Task) -> TaskComplexity:
        """
        Estimate task complexity

        Args:
            task: Task object

        Returns:
            TaskComplexity enum value
        """
        # Already has complexity from creation
        if task.complexity:
            return task.complexity

        # Analyze task description and details
        text = f"{task.name} {task.description}".lower()

        # Check for complex indicators
        for indicator in self.COMPLEXITY_INDICATORS["complex"]:
            if indicator in text:
                return TaskComplexity.COMPLEX

        # Check for simple indicators
        for indicator in self.COMPLEXITY_INDICATORS["simple"]:
            if indicator in text:
                return TaskComplexity.SIMPLE

        # Default to medium
        return TaskComplexity.MEDIUM

    def calculate_duration(self, task: Task) -> int:
        """
        Calculate task duration in minutes

        Args:
            task: Task object

        Returns:
            Estimated minutes (60, 90, or 120)
        """
        complexity = (
            task.complexity
            if isinstance(task.complexity, TaskComplexity)
            else TaskComplexity(task.complexity)
        )
        return self.DURATION_MAP[complexity]

    def add_acceptance_criteria(self, task: Task) -> Task:
        """
        Add specific, measurable acceptance criteria

        Args:
            task: Task object

        Returns:
            Task with populated acceptance_criteria
        """
        if task.acceptance_criteria:
            return task

        # Generate criteria based on task category
        criteria = []

        if task.category == "implementation":
            criteria.extend(self._generate_implementation_criteria(task))
        elif task.category == "testing":
            criteria.extend(self._generate_testing_criteria(task))
        elif task.category == "documentation":
            criteria.extend(self._generate_documentation_criteria(task))

        task.acceptance_criteria = criteria
        return task

    def _determine_task_breakdown(
        self, feature: Dict, requirements: List[str], technical_details: List[str]
    ) -> Dict[str, Dict]:
        """Determine how to break down feature into tasks"""
        breakdown = {}

        # Check for database/model needs
        if self._needs_database_models(requirements, technical_details):
            breakdown["database_models"] = {
                "description": "Create database models and migrations",
                "complexity": TaskComplexity.SIMPLE,
            }

        # Check for API needs
        if self._needs_api_endpoints(requirements, technical_details):
            breakdown["api_endpoints"] = {
                "description": "Implement API endpoints",
                "complexity": TaskComplexity.MEDIUM,
            }

        # Check for business logic
        if self._needs_business_logic(feature):
            complexity = self._assess_business_logic_complexity(feature)
            breakdown["business_logic"] = {
                "description": "Implement core business logic",
                "complexity": complexity,
            }

        # Check for UI components
        if self._needs_ui_components(requirements, technical_details):
            breakdown["ui_components"] = {
                "description": "Create UI components",
                "complexity": TaskComplexity.MEDIUM,
            }

        # If no specific pattern matched, create generic implementation task
        if not breakdown:
            complexity = self._assess_feature_complexity(feature)
            breakdown["implementation"] = {
                "description": f'Implement {feature["name"]}',
                "complexity": complexity,
            }

        return breakdown

    def _create_task(
        self,
        feature_id: str,
        feature_name: str,
        task_type: str,
        task_details: Dict,
        requirements: List[str],
    ) -> Optional[Task]:
        """Create a Task object"""
        self.task_counter += 1

        task_id = f"{feature_id}_task_{self.task_counter}"
        task_name = f"{feature_name}: {task_type.replace('_', ' ').title()}"

        complexity = task_details["complexity"]
        estimated_minutes = self.DURATION_MAP[complexity]

        task = Task(
            id=task_id,
            name=task_name,
            description=task_details["description"],
            feature_id=feature_id,
            complexity=complexity,
            estimated_minutes=estimated_minutes,
            category="implementation",
        )

        # Add acceptance criteria
        task = self.add_acceptance_criteria(task)

        return task

    def _create_test_task(
        self, feature_id: str, feature_name: str, implementation_tasks: List[Task]
    ) -> Task:
        """Create testing task"""
        self.task_counter += 1

        task_id = f"{feature_id}_task_{self.task_counter}"
        task_name = f"{feature_name}: Tests"

        # Tests are typically medium complexity
        task = Task(
            id=task_id,
            name=task_name,
            description=f"Write comprehensive tests for {feature_name}",
            feature_id=feature_id,
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
            category="testing",
            dependencies=[t.id for t in implementation_tasks],
        )

        task = self.add_acceptance_criteria(task)
        return task

    def _create_documentation_task(self, feature_id: str, feature_name: str) -> Task:
        """Create documentation task"""
        self.task_counter += 1

        task_id = f"{feature_id}_task_{self.task_counter}"
        task_name = f"{feature_name}: Documentation"

        task = Task(
            id=task_id,
            name=task_name,
            description=f"Write documentation for {feature_name}",
            feature_id=feature_id,
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=60,
            category="documentation",
        )

        task = self.add_acceptance_criteria(task)
        return task

    def _needs_database_models(self, requirements: List[str], technical_details: List[str]) -> bool:
        """Check if feature needs database models"""
        text = " ".join(requirements + technical_details).lower()
        keywords = [
            "database",
            "model",
            "table",
            "schema",
            "migration",
            "postgres",
            "mysql",
            "store",
        ]
        return any(keyword in text for keyword in keywords)

    def _needs_api_endpoints(self, requirements: List[str], technical_details: List[str]) -> bool:
        """Check if feature needs API endpoints"""
        text = " ".join(requirements + technical_details).lower()
        keywords = [
            "api",
            "endpoint",
            "rest",
            "graphql",
            "route",
            "controller",
            "request",
            "response",
        ]
        return any(keyword in text for keyword in keywords)

    def _needs_business_logic(self, feature: Dict) -> bool:
        """Check if feature needs business logic"""
        # Most features have some business logic
        requirements = feature.get("requirements", [])
        return len(requirements) > 0

    def _needs_ui_components(self, requirements: List[str], technical_details: List[str]) -> bool:
        """Check if feature needs UI components"""
        text = " ".join(requirements + technical_details).lower()
        keywords = [
            "ui",
            "interface",
            "component",
            "view",
            "page",
            "form",
            "frontend",
            "display",
            "render",
        ]
        return any(keyword in text for keyword in keywords)

    def _needs_documentation(self, feature: Dict) -> bool:
        """Check if feature needs documentation task"""
        # Complex features or features with many requirements need docs
        complexity = feature.get("complexity", "medium")
        requirements = feature.get("requirements", [])
        return complexity == "complex" or len(requirements) > 5

    def _assess_business_logic_complexity(self, feature: Dict) -> TaskComplexity:
        """Assess complexity of business logic"""
        text = (
            f"{feature.get('description', '')} {' '.join(feature.get('requirements', []))}".lower()
        )

        # Check for complex indicators
        for indicator in self.COMPLEXITY_INDICATORS["complex"]:
            if indicator in text:
                return TaskComplexity.COMPLEX

        # Check for simple indicators
        for indicator in self.COMPLEXITY_INDICATORS["simple"]:
            if indicator in text:
                return TaskComplexity.SIMPLE

        return TaskComplexity.MEDIUM

    def _assess_feature_complexity(self, feature: Dict) -> TaskComplexity:
        """Assess overall feature complexity"""
        # Use existing complexity if available
        if "complexity" in feature:
            complexity_str = feature["complexity"]
            try:
                return TaskComplexity(complexity_str)
            except ValueError:
                pass

        # Assess based on requirements count
        requirements = feature.get("requirements", [])
        if len(requirements) <= 2:
            return TaskComplexity.SIMPLE
        elif len(requirements) >= 6:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.MEDIUM

    def _generate_implementation_criteria(self, task: Task) -> List[str]:
        """Generate acceptance criteria for implementation tasks"""
        criteria = []

        if "database" in task.name.lower() or "model" in task.name.lower():
            criteria.extend(
                [
                    "Database models created with proper fields and relationships",
                    "Migrations generated and tested",
                    "Models have appropriate indexes and constraints",
                ]
            )

        elif "api" in task.name.lower() or "endpoint" in task.name.lower():
            criteria.extend(
                [
                    "API endpoints implemented with proper HTTP methods",
                    "Request/response validation in place",
                    "Error handling implemented",
                    "API documented (docstrings or OpenAPI)",
                ]
            )

        elif "ui" in task.name.lower() or "component" in task.name.lower():
            criteria.extend(
                [
                    "UI components render correctly",
                    "Component is responsive and accessible",
                    "User interactions work as expected",
                ]
            )

        elif "business" in task.name.lower() or "logic" in task.name.lower():
            criteria.extend(
                ["Core functionality implemented", "Business rules enforced", "Edge cases handled"]
            )

        else:
            # Generic implementation criteria
            criteria.extend(
                [
                    "Feature functionality implemented as specified",
                    "Code follows project conventions",
                    "Error handling implemented",
                ]
            )

        return criteria

    def _generate_testing_criteria(self, task: Task) -> List[str]:
        """Generate acceptance criteria for testing tasks"""
        return [
            "Unit tests written for all public methods",
            "Edge cases and error conditions tested",
            "Test coverage >= 90%",
            "All tests passing",
        ]

    def _generate_documentation_criteria(self, task: Task) -> List[str]:
        """Generate acceptance criteria for documentation tasks"""
        return [
            "API/public methods documented with docstrings",
            "Usage examples provided",
            "README updated if needed",
            "Documentation is clear and accurate",
        ]


def main():
    """CLI entry point for testing"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python task_decomposer.py <feature_json>")
        sys.exit(1)

    feature_json = sys.argv[1]
    feature = json.loads(feature_json)

    decomposer = TaskDecomposer()
    tasks = decomposer.decompose_feature(feature)

    print(f"\n=== Task Decomposition ===")
    print(f"Feature: {feature['name']}")
    print(f"Tasks generated: {len(tasks)}\n")

    total_minutes = 0
    for task in tasks:
        print(f"Task: {task.name}")
        print(f"  Complexity: {task.complexity.value}")
        print(f"  Duration: {task.estimated_minutes} minutes")
        print(f"  Category: {task.category}")
        print(f"  Criteria: {len(task.acceptance_criteria)} items")
        total_minutes += task.estimated_minutes
        print()

    print(f"Total estimated time: {total_minutes} minutes ({total_minutes/60:.1f} hours)")


if __name__ == "__main__":
    main()
