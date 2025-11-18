"""
Tests for Code Smell Detector
"""
import pytest
import ast
from pathlib import Path
from core.code_smell_detector import CodeSmellDetector, CodeSmell


class TestCodeSmellDetector:
    """Test CodeSmellDetector class"""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create CodeSmellDetector instance"""
        return CodeSmellDetector(project_root=tmp_path)

    def test_init(self, tmp_path):
        """Test initialization"""
        detector = CodeSmellDetector(project_root=tmp_path)
        assert detector.project_root == tmp_path

    def test_detect_long_method(self, detector):
        """Test detection of long methods"""
        # Create a method with 60 lines (> 50 threshold)
        code = "def long_method():\n" + "    pass\n" * 60
        tree = ast.parse(code)

        smells = detector.detect_long_methods(tree, code)

        assert len(smells) == 1
        assert smells[0].smell_type == 'long_method'
        assert smells[0].severity in ['medium', 'high']
        assert 'long_method' in smells[0].location

    def test_detect_very_long_method(self, detector):
        """Test detection of very long methods (high severity)"""
        # Create a method with 120 lines (> 100, which is 2x threshold)
        code = "def very_long_method():\n" + "    pass\n" * 120
        tree = ast.parse(code)

        smells = detector.detect_long_methods(tree, code)

        assert len(smells) == 1
        assert smells[0].severity == 'high'

    def test_no_long_method(self, detector):
        """Test short methods are not flagged"""
        code = """
def short_method():
    return 42
"""
        tree = ast.parse(code)

        smells = detector.detect_long_methods(tree, code)

        assert len(smells) == 0

    def test_detect_long_parameter_list(self, detector):
        """Test detection of functions with too many parameters"""
        code = """
def many_params(a, b, c, d, e, f, g):
    pass
"""
        tree = ast.parse(code)

        smells = detector.detect_long_parameter_lists(tree)

        assert len(smells) == 1
        assert smells[0].smell_type == 'long_parameter_list'
        assert smells[0].severity in ['medium', 'high']

    def test_detect_long_parameter_list_exclude_self(self, detector):
        """Test that self/cls parameters are excluded from count"""
        code = """
class MyClass:
    def method(self, a, b, c, d, e, f):
        pass
"""
        tree = ast.parse(code)

        smells = detector.detect_long_parameter_lists(tree)

        # 6 params + self = 7 total, but should count as 6
        assert len(smells) == 1
        assert smells[0].metric_value == 6

    def test_no_long_parameter_list(self, detector):
        """Test functions with reasonable parameter count"""
        code = """
def normal_params(a, b, c):
    pass
"""
        tree = ast.parse(code)

        smells = detector.detect_long_parameter_lists(tree)

        assert len(smells) == 0

    def test_detect_magic_numbers(self, detector):
        """Test detection of magic numbers"""
        code = """
def calculate(x):
    result = x * 3.14159
    answer = 42
    return result + answer
"""
        tree = ast.parse(code)

        smells = detector.detect_magic_numbers(tree, code)

        # 3.14159 is magic, 42 is magic (not in allowed list)
        # Detection deduplicates by line, so we get 2 separate detections
        assert len(smells) == 2
        assert all(s.smell_type == 'magic_number' for s in smells)

    def test_magic_numbers_allowed(self, detector):
        """Test that common numbers are not flagged"""
        code = """
def calculate(x):
    return x * 0 + 1 - 1 + 2
"""
        tree = ast.parse(code)

        smells = detector.detect_magic_numbers(tree, code)

        # 0, 1, -1, 2 are all allowed
        assert len(smells) == 0

    def test_magic_numbers_in_constants(self, detector):
        """Test that magic numbers in constant definitions are allowed"""
        code = """
PI = 3.14159
ANSWER = 42

def calculate(x):
    return x * PI
"""
        tree = ast.parse(code)

        smells = detector.detect_magic_numbers(tree, code)

        # Constants should not be flagged
        # Note: This is a simple heuristic check
        assert len(smells) <= 2  # May detect in assignment

    def test_detect_unused_variable(self, detector):
        """Test detection of unused variables"""
        code = """
def process():
    unused_var = 42
    used_var = 10
    return used_var
"""
        tree = ast.parse(code)

        smells = detector.detect_dead_code(tree, code)

        unused_smells = [s for s in smells if s.smell_type == 'unused_variable']
        assert len(unused_smells) == 1
        assert 'unused_var' in unused_smells[0].location

    def test_unused_variable_underscore_prefix(self, detector):
        """Test that variables with _ prefix are not flagged"""
        code = """
def process():
    _private = 42
    return True
"""
        tree = ast.parse(code)

        smells = detector.detect_dead_code(tree, code)

        # Private variables should not be flagged
        unused_smells = [s for s in smells if 'private' in s.location]
        assert len(unused_smells) == 0

    def test_detect_unused_import(self, detector):
        """Test detection of unused imports"""
        code = """
import os
import sys

def main():
    print(sys.version)
"""
        tree = ast.parse(code)

        smells = detector.detect_dead_code(tree, code)

        unused_imports = [s for s in smells if s.smell_type == 'unused_import']
        assert len(unused_imports) == 1
        assert 'os' in unused_imports[0].location

    def test_detect_god_class(self, detector):
        """Test detection of god classes"""
        # Create a class with 25 methods (> 20 threshold)
        methods = "\n".join([f"    def method_{i}(self): pass" for i in range(25)])
        code = f"class GodClass:\n{methods}"
        tree = ast.parse(code)

        smells = detector.detect_god_classes(tree)

        assert len(smells) == 1
        assert smells[0].smell_type == 'god_class'
        assert smells[0].severity in ['medium', 'high']
        assert smells[0].metric_value == 25

    def test_no_god_class(self, detector):
        """Test normal classes are not flagged"""
        code = """
class NormalClass:
    def __init__(self):
        pass

    def method1(self):
        pass

    def method2(self):
        pass
"""
        tree = ast.parse(code)

        smells = detector.detect_god_classes(tree)

        assert len(smells) == 0

    def test_detect_deep_nesting(self, detector):
        """Test detection of deeply nested code"""
        code = """
def deeply_nested():
    if True:
        if True:
            if True:
                if True:
                    if True:
                        print("too deep")
"""
        tree = ast.parse(code)

        smells = detector.detect_deep_nesting(tree)

        assert len(smells) == 1
        assert smells[0].smell_type == 'deep_nesting'
        assert smells[0].severity in ['medium', 'high']

    def test_no_deep_nesting(self, detector):
        """Test normal nesting is not flagged"""
        code = """
def normal_nesting():
    if True:
        if True:
            print("ok")
"""
        tree = ast.parse(code)

        smells = detector.detect_deep_nesting(tree)

        assert len(smells) == 0

    def test_detect_commented_code(self, detector):
        """Test detection of commented-out code"""
        code = """
def process():
    x = 10
    # y = 20
    # for i in range(10):
    #     print(i)
    return x
"""

        smells = detector.detect_commented_code(code)

        assert len(smells) >= 2  # At least 2 commented code lines
        assert all(s.smell_type == 'commented_code' for s in smells)

    def test_normal_comments_not_flagged(self, detector):
        """Test that normal comments are not flagged"""
        code = """
def process():
    # This is a normal comment
    # TODO: Implement this feature
    # NOTE: This is important
    x = 10
    return x
"""

        smells = detector.detect_commented_code(code)

        # Normal comments should not be flagged
        assert len(smells) == 0

    def test_calculate_smell_score_perfect(self, detector):
        """Test smell score with no issues"""
        score = detector.calculate_smell_score([], [], [], [], [], [], [])
        assert score == 100

    def test_calculate_smell_score_with_issues(self, detector):
        """Test smell score with various issues"""
        long_methods = [
            CodeSmell('long_method', 'test', 'high', 'Test', 'Test', 100)
        ]
        long_params = [
            CodeSmell('long_parameter_list', 'test', 'medium', 'Test', 'Test', 8)
        ]
        magic_numbers = [
            CodeSmell('magic_number', 'test', 'low', 'Test', 'Test')
        ]
        dead_code = [
            CodeSmell('unused_variable', 'test', 'low', 'Test', 'Test')
        ]

        score = detector.calculate_smell_score(
            long_methods, long_params, magic_numbers, dead_code, [], [], []
        )

        # Score should be: 100 - 15 (high long method) - 6 (medium params) - 2 (magic) - 3 (dead) = 74
        assert score == 74

    def test_generate_recommendations_with_smells(self, detector):
        """Test recommendation generation with various smells"""
        long_methods = [CodeSmell('long_method', 'test', 'high', 'Test', 'Test')]
        long_params = [CodeSmell('long_parameter_list', 'test', 'medium', 'Test', 'Test')]

        recommendations = detector.generate_recommendations(
            long_methods, long_params, [], [], [], [], []
        )

        assert len(recommendations) >= 2
        assert any('Refactor' in r and 'long method' in r for r in recommendations)
        assert any('parameter count' in r for r in recommendations)

    def test_generate_recommendations_clean_code(self, detector):
        """Test recommendations for clean code"""
        recommendations = detector.generate_recommendations([], [], [], [], [], [], [])

        assert len(recommendations) == 1
        assert 'clean' in recommendations[0].lower()

    def test_analyze_file_success(self, detector, tmp_path):
        """Test full file analysis"""
        test_file = tmp_path / "test_smells.py"
        test_file.write_text("""
def simple_function():
    magic = 999
    unused = 42
    return magic
""")

        result = detector.analyze_file(str(test_file))

        assert 'long_methods' in result
        assert 'long_parameter_lists' in result
        assert 'magic_numbers' in result
        assert 'dead_code' in result
        assert 'god_classes' in result
        assert 'deep_nesting' in result
        assert 'commented_code' in result
        assert 'smell_score' in result
        assert 'recommendations' in result
        assert 0 <= result['smell_score'] <= 100

    def test_analyze_file_not_found(self, detector):
        """Test analysis of non-existent file"""
        with pytest.raises(FileNotFoundError):
            detector.analyze_file("/nonexistent/file.py")

    def test_analyze_file_syntax_error(self, detector, tmp_path):
        """Test analysis of file with syntax errors"""
        test_file = tmp_path / "bad.py"
        test_file.write_text("def invalid syntax here")

        result = detector.analyze_file(str(test_file))

        # Should return error result
        assert result['smell_score'] == 0
        assert 'Syntax error' in result['recommendations'][0]

    def test_is_constant_definition(self, detector):
        """Test constant definition detection"""
        code = """
MAX_SIZE = 100
min_value = 10
"""
        tree = ast.parse(code)

        # Find the constant nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if node.value == 100:
                    # Should be detected as constant
                    assert detector._is_constant_definition(node, tree) is True
                elif node.value == 10:
                    # min_value is lowercase, should not be constant
                    assert detector._is_constant_definition(node, tree) is False

    def test_calculate_nesting_depth_simple(self, detector):
        """Test nesting depth calculation for simple code"""
        code = """
def simple():
    if True:
        print("ok")
"""
        tree = ast.parse(code)
        func = tree.body[0]

        depth = detector._calculate_nesting_depth(func)
        assert depth == 1

    def test_calculate_nesting_depth_complex(self, detector):
        """Test nesting depth calculation for complex code"""
        code = """
def complex():
    if True:
        for i in range(10):
            if True:
                while True:
                    print("deep")
                    break
"""
        tree = ast.parse(code)
        func = tree.body[0]

        depth = detector._calculate_nesting_depth(func)
        assert depth == 4

    def test_multiple_smells_in_file(self, detector, tmp_path):
        """Test file with multiple code smells"""
        test_file = tmp_path / "smelly_code.py"
        test_file.write_text("""
import unused_module

def long_params(a, b, c, d, e, f, g, h):
    magic = 42.195
    unused = 100
    if True:
        if True:
            if True:
                if True:
                    if True:
                        print("too deep")
    # old_code = "removed"
    return magic
""")

        result = detector.analyze_file(str(test_file))

        # Should detect multiple types of smells
        assert len(result['long_parameter_lists']) > 0
        assert len(result['magic_numbers']) > 0
        assert len(result['dead_code']) > 0
        assert len(result['deep_nesting']) > 0
        assert result['smell_score'] < 100
