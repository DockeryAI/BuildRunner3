"""
Tests for Task Decomposer
"""

import pytest
from core.task_decomposer import TaskDecomposer, Task, TaskComplexity


class TestTaskDecomposer:
    """Test TaskDecomposer class"""

    @pytest.fixture
    def decomposer(self):
        """Create TaskDecomposer instance"""
        return TaskDecomposer()

    @pytest.fixture
    def simple_feature(self):
        """Simple feature with minimal requirements"""
        return {
            "id": "simple_feature",
            "name": "Simple CRUD API",
            "description": "Basic CRUD operations for users",
            "requirements": ["Create user endpoint", "Read user endpoint"],
            "technical_details": ["REST API", "Database model"],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "simple",
        }

    @pytest.fixture
    def complex_feature(self):
        """Complex feature with many requirements"""
        return {
            "id": "auth_system",
            "name": "Authentication System",
            "description": "Complete authentication with OAuth, JWT, and session management",
            "requirements": [
                "Email/password authentication",
                "OAuth integration (Google, GitHub)",
                "JWT token generation",
                "Session management",
                "Password reset flow",
                "2FA support",
                "Rate limiting",
                "Security audit logging",
            ],
            "technical_details": [
                "JWT tokens",
                "PostgreSQL for user storage",
                "Redis for sessions",
                "OAuth2 protocol",
                "bcrypt for password hashing",
            ],
            "acceptance_criteria": [
                "Users can register and login",
                "OAuth providers work correctly",
                "Sessions are properly managed",
            ],
            "dependencies": [],
            "complexity": "complex",
        }

    @pytest.fixture
    def ui_feature(self):
        """Feature with UI components"""
        return {
            "id": "dashboard",
            "name": "User Dashboard",
            "description": "Interactive dashboard with charts and data visualization",
            "requirements": ["Display user metrics", "Interactive charts", "Responsive design"],
            "technical_details": ["React components", "Chart.js library", "API integration"],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "medium",
        }

    def test_init(self, decomposer):
        """Test initialization"""
        assert decomposer is not None
        assert decomposer.task_counter == 0

    def test_decompose_simple_feature(self, decomposer, simple_feature):
        """Test decomposing a simple feature"""
        tasks = decomposer.decompose_feature(simple_feature)

        assert len(tasks) >= 1
        assert all(isinstance(task, Task) for task in tasks)

        # Verify all tasks have required fields
        for task in tasks:
            assert task.id
            assert task.name
            assert task.description
            assert task.feature_id == "simple_feature"
            assert isinstance(task.complexity, TaskComplexity)
            assert task.estimated_minutes in [60, 90, 120]

    def test_decompose_complex_feature(self, decomposer, complex_feature):
        """Test decomposing a complex feature creates multiple tasks"""
        tasks = decomposer.decompose_feature(complex_feature)

        # Complex features should generate multiple tasks
        assert len(tasks) >= 2

        # Should include testing task for features with multiple implementation tasks
        task_categories = [task.category for task in tasks]
        if len([t for t in tasks if t.category == "implementation"]) >= 2:
            assert "testing" in task_categories

    def test_decompose_ui_feature(self, decomposer, ui_feature):
        """Test decomposing feature with UI components"""
        tasks = decomposer.decompose_feature(ui_feature)

        # Should create UI-related task
        task_names = [task.name.lower() for task in tasks]
        assert any("ui" in name or "component" in name for name in task_names)

    def test_estimate_complexity_simple(self, decomposer):
        """Test complexity estimation for simple tasks"""
        task = Task(
            id="test_1",
            name="Simple CRUD operation",
            description="Basic create operation",
            feature_id="feature_1",
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=60,
        )

        complexity = decomposer.estimate_complexity(task)
        assert complexity == TaskComplexity.SIMPLE

    def test_estimate_complexity_complex(self, decomposer):
        """Test complexity estimation for complex tasks"""
        task = Task(
            id="test_2",
            name="OAuth Authentication Integration",
            description="Implement OAuth2 authentication with multiple providers",
            feature_id="feature_2",
            complexity=TaskComplexity.MEDIUM,  # Will be re-estimated
            estimated_minutes=90,
        )

        # Re-estimate based on content
        task.complexity = None
        complexity = decomposer.estimate_complexity(task)
        assert complexity == TaskComplexity.COMPLEX

    def test_estimate_complexity_by_keywords(self, decomposer):
        """Test complexity estimation using indicator keywords"""
        # Test complex indicator
        complex_task = Task(
            id="test_3",
            name="Payment Processing",
            description="Implement payment gateway integration",
            feature_id="feature_3",
            complexity=None,
            estimated_minutes=90,
        )
        assert decomposer.estimate_complexity(complex_task) == TaskComplexity.COMPLEX

        # Test simple indicator
        simple_task = Task(
            id="test_4",
            name="Basic CRUD operations",
            description="Simple database operations",
            feature_id="feature_4",
            complexity=None,
            estimated_minutes=60,
        )
        assert decomposer.estimate_complexity(simple_task) == TaskComplexity.SIMPLE

    def test_calculate_duration_simple(self, decomposer):
        """Test duration calculation for simple tasks"""
        task = Task(
            id="test_5",
            name="Simple Task",
            description="Description",
            feature_id="feature_5",
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=60,
        )

        duration = decomposer.calculate_duration(task)
        assert duration == 60

    def test_calculate_duration_medium(self, decomposer):
        """Test duration calculation for medium tasks"""
        task = Task(
            id="test_6",
            name="Medium Task",
            description="Description",
            feature_id="feature_6",
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
        )

        duration = decomposer.calculate_duration(task)
        assert duration == 90

    def test_calculate_duration_complex(self, decomposer):
        """Test duration calculation for complex tasks"""
        task = Task(
            id="test_7",
            name="Complex Task",
            description="Description",
            feature_id="feature_7",
            complexity=TaskComplexity.COMPLEX,
            estimated_minutes=120,
        )

        duration = decomposer.calculate_duration(task)
        assert duration == 120

    def test_add_acceptance_criteria_implementation(self, decomposer):
        """Test adding acceptance criteria for implementation tasks"""
        task = Task(
            id="test_8",
            name="API Endpoint Implementation",
            description="Create REST API endpoints",
            feature_id="feature_8",
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
            category="implementation",
        )

        task = decomposer.add_acceptance_criteria(task)

        assert len(task.acceptance_criteria) > 0
        assert all(isinstance(criterion, str) for criterion in task.acceptance_criteria)

    def test_add_acceptance_criteria_testing(self, decomposer):
        """Test adding acceptance criteria for testing tasks"""
        task = Task(
            id="test_9",
            name="Test Suite",
            description="Write comprehensive tests",
            feature_id="feature_9",
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
            category="testing",
        )

        task = decomposer.add_acceptance_criteria(task)

        assert len(task.acceptance_criteria) > 0
        # Testing criteria should include coverage requirements
        criteria_text = " ".join(task.acceptance_criteria).lower()
        assert "test" in criteria_text

    def test_add_acceptance_criteria_documentation(self, decomposer):
        """Test adding acceptance criteria for documentation tasks"""
        task = Task(
            id="test_10",
            name="API Documentation",
            description="Write API documentation",
            feature_id="feature_10",
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=60,
            category="documentation",
        )

        task = decomposer.add_acceptance_criteria(task)

        assert len(task.acceptance_criteria) > 0
        # Documentation criteria should mention docs/examples
        criteria_text = " ".join(task.acceptance_criteria).lower()
        assert "document" in criteria_text or "example" in criteria_text

    def test_add_acceptance_criteria_already_exists(self, decomposer):
        """Test that existing criteria are not overwritten"""
        existing_criteria = ["Existing criterion 1", "Existing criterion 2"]

        task = Task(
            id="test_11",
            name="Task with criteria",
            description="Description",
            feature_id="feature_11",
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=60,
            acceptance_criteria=existing_criteria.copy(),
        )

        task = decomposer.add_acceptance_criteria(task)

        assert task.acceptance_criteria == existing_criteria

    def test_needs_database_models(self, decomposer):
        """Test detection of database model needs"""
        requirements = ["Store user data", "Database schema required"]
        technical_details = ["PostgreSQL", "User model"]

        result = decomposer._needs_database_models(requirements, technical_details)
        assert result is True

    def test_needs_database_models_false(self, decomposer):
        """Test when database models not needed"""
        requirements = ["Display UI", "User interaction"]
        technical_details = ["Frontend only"]

        result = decomposer._needs_database_models(requirements, technical_details)
        assert result is False

    def test_needs_api_endpoints(self, decomposer):
        """Test detection of API endpoint needs"""
        requirements = ["REST API for users"]
        technical_details = ["HTTP endpoints", "Request/response handling"]

        result = decomposer._needs_api_endpoints(requirements, technical_details)
        assert result is True

    def test_needs_api_endpoints_false(self, decomposer):
        """Test when API endpoints not needed"""
        requirements = ["Calculate data locally"]
        technical_details = ["Pure function"]

        result = decomposer._needs_api_endpoints(requirements, technical_details)
        assert result is False

    def test_needs_ui_components(self, decomposer):
        """Test detection of UI component needs"""
        requirements = ["User interface for dashboard"]
        technical_details = ["React components", "Frontend display"]

        result = decomposer._needs_ui_components(requirements, technical_details)
        assert result is True

    def test_needs_ui_components_false(self, decomposer):
        """Test when UI components not needed"""
        requirements = ["Background job processing"]
        technical_details = ["Cron task"]

        result = decomposer._needs_ui_components(requirements, technical_details)
        assert result is False

    def test_needs_documentation(self, decomposer):
        """Test detection of documentation needs"""
        # Complex feature should need documentation
        complex_feature = {"complexity": "complex", "requirements": ["Req 1", "Req 2"]}
        assert decomposer._needs_documentation(complex_feature) is True

        # Feature with many requirements should need documentation
        many_req_feature = {
            "complexity": "medium",
            "requirements": ["R1", "R2", "R3", "R4", "R5", "R6"],
        }
        assert decomposer._needs_documentation(many_req_feature) is True

    def test_needs_documentation_false(self, decomposer):
        """Test when documentation not needed"""
        simple_feature = {"complexity": "simple", "requirements": ["Req 1", "Req 2"]}
        assert decomposer._needs_documentation(simple_feature) is False

    def test_assess_business_logic_complexity(self, decomposer):
        """Test business logic complexity assessment"""
        # Complex business logic
        complex_feature = {
            "description": "Payment processing with fraud detection",
            "requirements": ["Payment gateway integration", "Security validation"],
        }
        complexity = decomposer._assess_business_logic_complexity(complex_feature)
        assert complexity == TaskComplexity.COMPLEX

        # Simple business logic
        simple_feature = {
            "description": "Basic CRUD operations",
            "requirements": ["Simple data handling"],
        }
        complexity = decomposer._assess_business_logic_complexity(simple_feature)
        assert complexity == TaskComplexity.SIMPLE

    def test_assess_feature_complexity_by_requirements_count(self, decomposer):
        """Test feature complexity assessment based on requirements count"""
        # Simple (≤2 requirements)
        simple_feature = {"requirements": ["Req 1", "Req 2"]}
        assert decomposer._assess_feature_complexity(simple_feature) == TaskComplexity.SIMPLE

        # Complex (≥6 requirements)
        complex_feature = {"requirements": ["R1", "R2", "R3", "R4", "R5", "R6"]}
        assert decomposer._assess_feature_complexity(complex_feature) == TaskComplexity.COMPLEX

        # Medium (3-5 requirements)
        medium_feature = {"requirements": ["R1", "R2", "R3", "R4"]}
        assert decomposer._assess_feature_complexity(medium_feature) == TaskComplexity.MEDIUM

    def test_assess_feature_complexity_from_complexity_field(self, decomposer):
        """Test using existing complexity field"""
        feature = {"complexity": "complex", "requirements": ["R1"]}  # Would normally be simple

        complexity = decomposer._assess_feature_complexity(feature)
        assert complexity == TaskComplexity.COMPLEX

    def test_generate_implementation_criteria_database(self, decomposer):
        """Test criteria generation for database tasks"""
        task = Task(
            id="test_12",
            name="Database Models",
            description="Create database models",
            feature_id="feature_12",
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=60,
            category="implementation",
        )

        criteria = decomposer._generate_implementation_criteria(task)

        assert len(criteria) > 0
        criteria_text = " ".join(criteria).lower()
        assert "model" in criteria_text or "database" in criteria_text

    def test_generate_implementation_criteria_api(self, decomposer):
        """Test criteria generation for API tasks"""
        task = Task(
            id="test_13",
            name="API Endpoints",
            description="Create REST API",
            feature_id="feature_13",
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
            category="implementation",
        )

        criteria = decomposer._generate_implementation_criteria(task)

        assert len(criteria) > 0
        criteria_text = " ".join(criteria).lower()
        assert "api" in criteria_text or "endpoint" in criteria_text

    def test_generate_implementation_criteria_ui(self, decomposer):
        """Test criteria generation for UI tasks"""
        task = Task(
            id="test_14",
            name="UI Components",
            description="Create user interface",
            feature_id="feature_14",
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
            category="implementation",
        )

        criteria = decomposer._generate_implementation_criteria(task)

        assert len(criteria) > 0
        criteria_text = " ".join(criteria).lower()
        assert "ui" in criteria_text or "component" in criteria_text

    def test_generate_implementation_criteria_business_logic(self, decomposer):
        """Test criteria generation for business logic tasks"""
        task = Task(
            id="test_15",
            name="Business Logic",
            description="Implement core business logic",
            feature_id="feature_15",
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
            category="implementation",
        )

        criteria = decomposer._generate_implementation_criteria(task)

        assert len(criteria) > 0
        criteria_text = " ".join(criteria).lower()
        assert (
            "business" in criteria_text
            or "logic" in criteria_text
            or "functionality" in criteria_text
        )

    def test_generate_testing_criteria(self, decomposer):
        """Test criteria generation for testing tasks"""
        task = Task(
            id="test_16",
            name="Test Suite",
            description="Write tests",
            feature_id="feature_16",
            complexity=TaskComplexity.MEDIUM,
            estimated_minutes=90,
            category="testing",
        )

        criteria = decomposer._generate_testing_criteria(task)

        assert len(criteria) == 4
        criteria_text = " ".join(criteria).lower()
        assert "test" in criteria_text
        assert "coverage" in criteria_text

    def test_generate_documentation_criteria(self, decomposer):
        """Test criteria generation for documentation tasks"""
        task = Task(
            id="test_17",
            name="Documentation",
            description="Write documentation",
            feature_id="feature_17",
            complexity=TaskComplexity.SIMPLE,
            estimated_minutes=60,
            category="documentation",
        )

        criteria = decomposer._generate_documentation_criteria(task)

        assert len(criteria) == 4
        criteria_text = " ".join(criteria).lower()
        assert "document" in criteria_text
        assert "example" in criteria_text

    def test_task_counter_increments(self, decomposer):
        """Test that task counter increments correctly"""
        initial_count = decomposer.task_counter

        feature = {
            "id": "feature_x",
            "name": "Test Feature",
            "description": "Description",
            "requirements": ["Req 1"],
            "technical_details": [],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "simple",
        }

        tasks = decomposer.decompose_feature(feature)

        assert decomposer.task_counter > initial_count
        assert decomposer.task_counter == initial_count + len(tasks)

    def test_task_ids_unique(self, decomposer):
        """Test that generated task IDs are unique"""
        feature = {
            "id": "feature_y",
            "name": "Multi-task Feature",
            "description": "Feature with multiple tasks",
            "requirements": ["Database storage", "API endpoints", "UI components"],
            "technical_details": ["PostgreSQL", "REST API", "React"],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "complex",
        }

        tasks = decomposer.decompose_feature(feature)

        task_ids = [task.id for task in tasks]
        assert len(task_ids) == len(set(task_ids))  # All IDs unique

    def test_task_dependencies(self, decomposer):
        """Test that testing tasks depend on implementation tasks"""
        feature = {
            "id": "feature_z",
            "name": "Feature with Dependencies",
            "description": "Feature that generates testing tasks",
            "requirements": ["Database model", "API endpoint", "Business logic"],
            "technical_details": ["PostgreSQL", "REST API"],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "medium",
        }

        tasks = decomposer.decompose_feature(feature)

        # Find testing task
        testing_tasks = [t for t in tasks if t.category == "testing"]
        if testing_tasks:
            test_task = testing_tasks[0]
            # Testing task should depend on implementation tasks
            impl_tasks = [t for t in tasks if t.category == "implementation"]
            if impl_tasks:
                assert len(test_task.dependencies) > 0

    def test_empty_feature(self, decomposer):
        """Test handling of feature with no requirements"""
        feature = {
            "id": "empty_feature",
            "name": "Empty Feature",
            "description": "Minimal feature",
            "requirements": [],
            "technical_details": [],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "simple",
        }

        tasks = decomposer.decompose_feature(feature)

        # Should still generate at least one task
        assert len(tasks) >= 1

    def test_feature_with_all_components(self, decomposer):
        """Test feature requiring all component types"""
        feature = {
            "id": "full_stack_feature",
            "name": "Full Stack Feature",
            "description": "Complete feature with all components",
            "requirements": [
                "Database storage required",
                "REST API endpoints needed",
                "User interface components",
                "Complex business logic",
            ],
            "technical_details": [
                "PostgreSQL database",
                "FastAPI framework",
                "React frontend",
                "Authentication workflow",
            ],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "complex",
        }

        tasks = decomposer.decompose_feature(feature)

        # Should generate multiple tasks for different components
        assert len(tasks) >= 3

        # Should include testing
        categories = [t.category for t in tasks]
        assert "testing" in categories

    def test_duration_map_completeness(self, decomposer):
        """Test that DURATION_MAP covers all complexity levels"""
        assert TaskComplexity.SIMPLE in decomposer.DURATION_MAP
        assert TaskComplexity.MEDIUM in decomposer.DURATION_MAP
        assert TaskComplexity.COMPLEX in decomposer.DURATION_MAP

        assert decomposer.DURATION_MAP[TaskComplexity.SIMPLE] == 60
        assert decomposer.DURATION_MAP[TaskComplexity.MEDIUM] == 90
        assert decomposer.DURATION_MAP[TaskComplexity.COMPLEX] == 120

    def test_complexity_indicators_structure(self, decomposer):
        """Test that complexity indicators are properly structured"""
        assert "simple" in decomposer.COMPLEXITY_INDICATORS
        assert "complex" in decomposer.COMPLEXITY_INDICATORS
        assert "medium" in decomposer.COMPLEXITY_INDICATORS

        assert isinstance(decomposer.COMPLEXITY_INDICATORS["simple"], list)
        assert isinstance(decomposer.COMPLEXITY_INDICATORS["complex"], list)
        assert len(decomposer.COMPLEXITY_INDICATORS["simple"]) > 0
        assert len(decomposer.COMPLEXITY_INDICATORS["complex"]) > 0

    def test_estimate_complexity_default_medium(self, decomposer):
        """Test complexity defaults to medium when no keywords match"""
        task = Task(
            id="test_18",
            name="Generic Task Name",
            description="Generic task description without keywords",
            feature_id="feature_18",
            complexity=None,
            estimated_minutes=90,
        )

        # Should default to medium when no keywords match
        complexity = decomposer.estimate_complexity(task)
        assert complexity == TaskComplexity.MEDIUM

    def test_assess_feature_complexity_invalid_complexity_string(self, decomposer):
        """Test handling of invalid complexity string"""
        feature = {"complexity": "invalid_complexity_level", "requirements": ["R1", "R2", "R3"]}

        # Should fall back to requirements-based assessment
        complexity = decomposer._assess_feature_complexity(feature)
        assert complexity == TaskComplexity.MEDIUM

    def test_needs_business_logic_true(self, decomposer):
        """Test business logic detection when requirements exist"""
        feature = {"requirements": ["Business rule 1", "Validation logic"]}

        result = decomposer._needs_business_logic(feature)
        assert result is True

    def test_needs_business_logic_false(self, decomposer):
        """Test business logic detection when no requirements"""
        feature = {"requirements": []}

        result = decomposer._needs_business_logic(feature)
        assert result is False

    def test_main_cli_function(self, decomposer, capsys):
        """Test CLI main function"""
        import sys
        import json
        from core.task_decomposer import main

        # Create test feature
        feature = {
            "id": "test_feature",
            "name": "Test Feature",
            "description": "Test description",
            "requirements": ["Req 1", "Req 2"],
            "technical_details": ["Detail 1"],
            "acceptance_criteria": [],
            "dependencies": [],
            "complexity": "medium",
        }

        # Mock sys.argv
        original_argv = sys.argv
        try:
            sys.argv = ["task_decomposer.py", json.dumps(feature)]
            main()

            # Capture output
            captured = capsys.readouterr()
            assert "Task Decomposition" in captured.out
            assert "Test Feature" in captured.out
            assert "Tasks generated:" in captured.out
        finally:
            sys.argv = original_argv

    def test_main_cli_no_args(self, capsys):
        """Test CLI main function with no arguments"""
        import sys
        from core.task_decomposer import main

        original_argv = sys.argv
        try:
            sys.argv = ["task_decomposer.py"]

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Usage:" in captured.out
        finally:
            sys.argv = original_argv
