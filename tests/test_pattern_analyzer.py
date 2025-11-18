"""
Tests for Pattern Analyzer
"""
import pytest
import ast
from pathlib import Path
from core.pattern_analyzer import PatternAnalyzer, PatternMatch, LayerViolation


class TestPatternAnalyzer:
    """Test PatternAnalyzer class"""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create PatternAnalyzer instance"""
        return PatternAnalyzer(project_root=tmp_path)

    def test_init(self, tmp_path):
        """Test initialization"""
        analyzer = PatternAnalyzer(project_root=tmp_path)
        assert analyzer.project_root == tmp_path

    def test_detect_mvc_model_pattern(self, analyzer):
        """Test detection of MVC Model pattern"""
        code = """
class UserModel:
    def __init__(self, name):
        self.name = name
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_mvc_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'MVC-Model'
        assert patterns[0].confidence == 0.8
        assert 'UserModel' in patterns[0].location

    def test_detect_mvc_view_pattern(self, analyzer):
        """Test detection of MVC View pattern"""
        code = """
class DashboardView:
    def render(self):
        pass
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_mvc_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'MVC-View'
        assert 'DashboardView' in patterns[0].location

    def test_detect_mvc_controller_pattern(self, analyzer):
        """Test detection of MVC Controller pattern"""
        code = """
class UserController:
    def handle_request(self):
        pass
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_mvc_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'MVC-Controller'
        assert patterns[0].confidence == 0.9

    def test_detect_repository_pattern(self, analyzer):
        """Test detection of Repository pattern"""
        code = """
class UserRepository:
    def find_by_id(self, user_id):
        pass

    def save(self, user):
        pass

    def delete(self, user_id):
        pass
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_repository_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'Repository'
        assert patterns[0].confidence == 0.9  # High confidence due to data access methods
        assert 'find_by_id' in patterns[0].evidence[1]

    def test_detect_repository_pattern_low_confidence(self, analyzer):
        """Test Repository pattern detection with low confidence"""
        code = """
class DataRepository:
    def process(self):
        pass
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_repository_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].confidence == 0.6  # Lower confidence, no data access methods

    def test_detect_factory_class_pattern(self, analyzer):
        """Test detection of Factory class pattern"""
        code = """
class UserFactory:
    def create_user(self, name):
        return User(name)

    def create_admin(self, name):
        return Admin(name)
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_factory_pattern(tree, code)

        # Should detect class + 2 factory methods = 3 patterns
        assert len(patterns) == 3
        class_patterns = [p for p in patterns if 'Class' in p.location]
        assert len(class_patterns) == 1
        assert class_patterns[0].pattern_type == 'Factory'
        assert class_patterns[0].confidence == 0.9

    def test_detect_factory_function_pattern(self, analyzer):
        """Test detection of Factory function pattern"""
        code = """
def create_user(name, role):
    if role == 'admin':
        return Admin(name)
    return User(name)
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_factory_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'Factory'
        assert patterns[0].confidence == 0.7
        assert 'create_user' in patterns[0].location

    def test_detect_singleton_pattern_with_new(self, analyzer):
        """Test detection of Singleton with __new__ override"""
        code = """
class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_singleton_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'Singleton'
        assert patterns[0].confidence == 0.9

    def test_detect_singleton_pattern_with_instance_var(self, analyzer):
        """Test detection of Singleton with _instance variable"""
        code = """
class Config:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
"""
        tree = ast.parse(code)
        patterns = analyzer._detect_singleton_pattern(tree, code)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == 'Singleton'
        assert patterns[0].confidence == 0.7

    def test_check_layer_violation_model_to_controller(self, analyzer, tmp_path):
        """Test detection of model importing from controller (violation)"""
        code = """
from app.controller import UserController

class User:
    pass
"""
        tree = ast.parse(code)
        file_path = tmp_path / "model" / "user.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        violations = analyzer.check_layer_violations(tree, file_path)

        assert len(violations) == 1
        assert violations[0].from_layer == 'model'
        assert violations[0].to_layer == 'controller'
        assert violations[0].severity in ['high', 'medium']

    def test_check_layer_violation_repository_to_view(self, analyzer, tmp_path):
        """Test detection of repository importing from view"""
        code = """
from app.view import DashboardView

class UserRepository:
    pass
"""
        tree = ast.parse(code)
        file_path = tmp_path / "repository" / "user_repository.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        violations = analyzer.check_layer_violations(tree, file_path)

        assert len(violations) == 1
        assert violations[0].from_layer == 'repository'
        assert violations[0].to_layer == 'presentation'
        assert violations[0].severity == 'high'  # Large gap in hierarchy

    def test_check_no_layer_violation_controller_to_service(self, analyzer, tmp_path):
        """Test valid import (controller to service)"""
        code = """
from app.service import UserService

class UserController:
    pass
"""
        tree = ast.parse(code)
        file_path = tmp_path / "controller" / "user_controller.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        violations = analyzer.check_layer_violations(tree, file_path)

        # Controller (level 3) can import from Service (level 2) - no violation
        assert len(violations) == 0

    def test_calculate_separation_score_perfect(self, analyzer):
        """Test separation score calculation with perfect code"""
        code = "class SimpleModel:\n    pass"
        tree = ast.parse(code)

        patterns = []
        violations = []

        score = analyzer.calculate_separation_score(tree, patterns, violations)

        assert score == 100

    def test_calculate_separation_score_with_violations(self, analyzer):
        """Test separation score with violations"""
        code = "class Model:\n    pass"
        tree = ast.parse(code)

        patterns = []
        violations = [
            LayerViolation('model', 'controller', 'test.py', 'Test violation', 'high'),
            LayerViolation('model', 'view', 'test.py', 'Test violation', 'medium')
        ]

        score = analyzer.calculate_separation_score(tree, patterns, violations)

        # Should lose 20 points for high severity + 10 for medium = 70
        assert score == 70

    def test_calculate_separation_score_with_good_patterns(self, analyzer):
        """Test separation score bonus for good patterns"""
        code = "class Model:\n    pass"
        tree = ast.parse(code)

        patterns = [
            PatternMatch('Repository', 0.9, 'Class UserRepo', 'Repository pattern', []),
            PatternMatch('Factory', 0.85, 'Class Factory', 'Factory pattern', [])
        ]
        violations = []

        score = analyzer.calculate_separation_score(tree, patterns, violations)

        # Should get bonus for 2 high-confidence patterns (100 + 5 + 5 = 110, capped at 100)
        assert score == 100

    def test_calculate_separation_score_too_many_classes(self, analyzer):
        """Test penalty for too many classes"""
        # Create code with 8 classes (penalty for > 5)
        code = "\n".join([f"class Class{i}:\n    pass" for i in range(8)])
        tree = ast.parse(code)

        score = analyzer.calculate_separation_score(tree, [], [])

        # Penalty: (8 - 5) * 3 = 9 points
        assert score == 91

    def test_generate_recommendations_with_violations(self, analyzer):
        """Test recommendation generation with violations"""
        patterns = []
        violations = [
            LayerViolation('model', 'controller', 'test.py', 'Test', 'high'),
            LayerViolation('model', 'view', 'test.py', 'Test', 'medium')
        ]
        score = 70

        recommendations = analyzer.generate_recommendations(patterns, violations, score)

        assert len(recommendations) >= 2
        assert any('Fix 2 layer violation' in r for r in recommendations)
        assert any('high-severity' in r for r in recommendations)

    def test_generate_recommendations_low_score(self, analyzer):
        """Test recommendations for low score"""
        patterns = []
        violations = []
        score = 45

        recommendations = analyzer.generate_recommendations(patterns, violations, score)

        assert any('significant separation of concerns issues' in r for r in recommendations)

    def test_generate_recommendations_good_code(self, analyzer):
        """Test recommendations for good code"""
        patterns = [PatternMatch('Repository', 0.9, 'Test', 'Test', [])]
        violations = []
        score = 95

        recommendations = analyzer.generate_recommendations(patterns, violations, score)

        assert any('good architectural practices' in r for r in recommendations)

    def test_analyze_file_success(self, analyzer, tmp_path):
        """Test full file analysis"""
        test_file = tmp_path / "user_repository.py"
        test_file.write_text("""
class UserRepository:
    def find_by_id(self, user_id):
        pass

    def save(self, user):
        pass
""")

        result = analyzer.analyze_file(str(test_file))

        assert 'patterns' in result
        assert 'violations' in result
        assert 'separation_score' in result
        assert 'recommendations' in result
        assert result['separation_score'] >= 0
        assert result['separation_score'] <= 100

    def test_analyze_file_not_found(self, analyzer):
        """Test analysis of non-existent file"""
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file("/nonexistent/file.py")

    def test_analyze_file_parse_error(self, analyzer, tmp_path):
        """Test analysis of file with syntax errors"""
        test_file = tmp_path / "bad.py"
        test_file.write_text("def invalid syntax here")

        result = analyzer.analyze_file(str(test_file))

        # Should return results with error in recommendations
        assert 'Failed to parse file' in result['recommendations'][0]
        assert result['separation_score'] == 0

    def test_determine_layer_from_path(self, analyzer, tmp_path):
        """Test layer determination from file path"""
        assert analyzer._determine_layer(tmp_path / "view" / "user.py") == 'presentation'
        assert analyzer._determine_layer(tmp_path / "controller" / "user.py") == 'controller'
        assert analyzer._determine_layer(tmp_path / "service" / "user.py") == 'service'
        assert analyzer._determine_layer(tmp_path / "repository" / "user.py") == 'repository'
        assert analyzer._determine_layer(tmp_path / "model" / "user.py") == 'model'
        assert analyzer._determine_layer(tmp_path / "utils" / "helper.py") is None

    def test_determine_layer_from_import(self, analyzer):
        """Test layer determination from import"""
        assert analyzer._determine_layer_from_import('app.view.user_view') == 'presentation'
        assert analyzer._determine_layer_from_import('app.controller.user') == 'controller'
        assert analyzer._determine_layer_from_import('app.service.user_service') == 'service'
        assert analyzer._determine_layer_from_import('app.repository.user_repo') == 'repository'
        assert analyzer._determine_layer_from_import('app.model.user') == 'model'
        assert analyzer._determine_layer_from_import('app.utils.helper') is None

    def test_is_layer_violation(self, analyzer):
        """Test layer violation detection logic"""
        # Lower layer importing from higher layer is violation
        assert analyzer._is_layer_violation('model', 'controller') is True
        assert analyzer._is_layer_violation('repository', 'service') is True

        # Higher layer importing from lower layer is OK
        assert analyzer._is_layer_violation('controller', 'service') is False
        assert analyzer._is_layer_violation('service', 'repository') is False

    def test_calculate_violation_severity(self, analyzer):
        """Test violation severity calculation"""
        # Model (0) to Presentation (4) = 4 levels = high
        assert analyzer._calculate_violation_severity('model', 'presentation') == 'high'

        # Repository (1) to Controller (3) = 2 levels = medium
        assert analyzer._calculate_violation_severity('repository', 'controller') == 'medium'

        # Model (0) to Repository (1) = 1 level = low
        assert analyzer._calculate_violation_severity('model', 'repository') == 'low'
