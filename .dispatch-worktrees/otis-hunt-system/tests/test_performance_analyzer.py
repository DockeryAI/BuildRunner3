"""
Tests for Performance Analyzer
"""

import pytest
import ast
from pathlib import Path
from core.performance_analyzer import PerformanceAnalyzer, ComplexityIssue


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer class"""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create PerformanceAnalyzer instance"""
        return PerformanceAnalyzer(project_root=tmp_path)

    def test_init(self, tmp_path):
        """Test initialization"""
        analyzer = PerformanceAnalyzer(project_root=tmp_path)
        assert analyzer.project_root == tmp_path

    def test_analyze_complexity_simple_function(self, analyzer):
        """Test complexity analysis of simple function"""
        code = """
def simple_function(x):
    return x + 1
"""
        issues = analyzer.analyze_complexity(code, "test.py")

        # Simple function should have no issues
        assert len(issues) == 0

    def test_analyze_complexity_complex_function(self, analyzer):
        """Test complexity analysis of complex function"""
        code = """
def complex_function(x, y, z, a, b):
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(10):
                    if i % 2:
                        if a > 0:
                            print(i)
                        elif a < 0:
                            print(-i)
                    else:
                        if i % 3:
                            if b > 0:
                                print(i)
                            else:
                                print(-i)
                        else:
                            if b % 2:
                                print(i * 2)
                            else:
                                print(i * 3)
    return x + y + z
"""
        issues = analyzer.analyze_complexity(code, "test.py")

        # Complex function should have issues
        assert len(issues) > 0
        assert issues[0].issue_type == "high_complexity"
        assert issues[0].severity in ["medium", "high"]

    def test_detect_n_plus_one_query(self, analyzer):
        """Test N+1 query detection"""
        code = """
def get_user_posts(users):
    for user in users:
        posts = db.query(Post).filter(Post.user_id == user.id).all()
        print(posts)
"""
        tree = ast.parse(code)
        issues = analyzer.detect_n_plus_one_queries(tree)

        assert len(issues) == 1
        assert issues[0].issue_type == "n_plus_one_query"
        assert issues[0].severity == "high"
        assert "bulk" in issues[0].recommendation.lower()

    def test_detect_n_plus_one_no_query_in_loop(self, analyzer):
        """Test N+1 detection with no queries in loop"""
        code = """
def process_users(users):
    for user in users:
        print(user.name)
"""
        tree = ast.parse(code)
        issues = analyzer.detect_n_plus_one_queries(tree)

        assert len(issues) == 0

    def test_detect_memory_leak_unclosed_file(self, analyzer):
        """Test memory leak detection for unclosed file"""
        code = """
def read_file(path):
    f = open(path, 'r')
    data = f.read()
    return data
"""
        tree = ast.parse(code)
        issues = analyzer.detect_memory_leaks(tree, code)

        # Should detect unclosed resource
        unclosed_issues = [i for i in issues if i.issue_type == "unclosed_resource"]
        assert len(unclosed_issues) > 0
        assert unclosed_issues[0].severity == "high"

    def test_detect_memory_leak_with_context_manager(self, analyzer):
        """Test no memory leak with context manager"""
        code = """
def read_file(path):
    with open(path, 'r') as f:
        data = f.read()
    return data
"""
        tree = ast.parse(code)
        issues = analyzer.detect_memory_leaks(tree, code)

        # Context manager properly closes resource
        unclosed_issues = [i for i in issues if i.issue_type == "unclosed_resource"]
        assert len(unclosed_issues) == 0

    def test_analyze_big_o_nested_loops(self, analyzer):
        """Test Big-O analysis for nested loops"""
        code = """
def nested_loop(items):
    for i in items:
        for j in items:
            print(i, j)
"""
        tree = ast.parse(code)
        issues = analyzer.analyze_big_o(tree)

        # Outer loop has 1 nested loop inside
        assert len(issues) >= 1
        assert any(issue.issue_type == "high_time_complexity" for issue in issues)

    def test_analyze_big_o_triple_nested_loops(self, analyzer):
        """Test Big-O analysis for triple nested loops"""
        code = """
def triple_nested(items):
    for i in items:
        for j in items:
            for k in items:
                print(i, j, k)
"""
        tree = ast.parse(code)
        issues = analyzer.analyze_big_o(tree)

        # Should detect at least one high complexity issue
        assert len(issues) >= 1
        high_complexity_issues = [i for i in issues if i.severity == "high"]
        assert len(high_complexity_issues) > 0

    def test_analyze_big_o_single_loop(self, analyzer):
        """Test Big-O analysis for single loop (O(n))"""
        code = """
def single_loop(items):
    for item in items:
        print(item)
"""
        tree = ast.parse(code)
        issues = analyzer.analyze_big_o(tree)

        # Single loop is O(n), which is fine
        assert len(issues) == 0

    def test_calculate_performance_score_perfect(self, analyzer):
        """Test performance score calculation with no issues"""
        score = analyzer.calculate_performance_score([], [], [], [])
        assert score == 100

    def test_calculate_performance_score_with_issues(self, analyzer):
        """Test performance score with various issues"""
        complexity_issues = [
            ComplexityIssue("high_complexity", "test", "high", "Test", 50),
            ComplexityIssue("high_complexity", "test", "medium", "Test", 15),
        ]
        n_plus_one = [ComplexityIssue("n_plus_one", "test", "high", "Test")]
        memory_leaks = [ComplexityIssue("memory_leak", "test", "medium", "Test")]
        big_o_warnings = []

        score = analyzer.calculate_performance_score(
            complexity_issues, n_plus_one, memory_leaks, big_o_warnings
        )

        # Score should be reduced: 100 - 15 (high complexity) - 8 (medium complexity) - 20 (N+1) - 10 (memory leak) = 47
        assert score == 47

    def test_generate_recommendations_with_complexity(self, analyzer):
        """Test recommendation generation with complexity issues"""
        complexity_issues = [ComplexityIssue("high_complexity", "test", "high", "Test", 50)]

        recommendations = analyzer.generate_recommendations(complexity_issues, [], [], [])

        assert len(recommendations) > 0
        assert any("Refactor" in r and "complexity" in r for r in recommendations)

    def test_generate_recommendations_with_n_plus_one(self, analyzer):
        """Test recommendations for N+1 queries"""
        n_plus_one = [ComplexityIssue("n_plus_one", "test", "high", "Test")]

        recommendations = analyzer.generate_recommendations([], n_plus_one, [], [])

        assert any("N+1" in r or "bulk" in r for r in recommendations)

    def test_generate_recommendations_good_code(self, analyzer):
        """Test recommendations for good code"""
        recommendations = analyzer.generate_recommendations([], [], [], [])

        assert any("good performance" in r for r in recommendations)

    def test_analyze_file_success(self, analyzer, tmp_path):
        """Test full file analysis"""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def simple_function(x):
    return x + 1

def another_function(y):
    result = y * 2
    return result
"""
        )

        result = analyzer.analyze_file(str(test_file))

        assert "complexity_issues" in result
        assert "n_plus_one_queries" in result
        assert "memory_leaks" in result
        assert "big_o_warnings" in result
        assert "performance_score" in result
        assert "recommendations" in result
        assert 0 <= result["performance_score"] <= 100

    def test_analyze_file_not_found(self, analyzer):
        """Test analysis of non-existent file"""
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_file("/nonexistent/file.py")

    def test_analyze_file_syntax_error(self, analyzer, tmp_path):
        """Test analysis of file with syntax errors"""
        test_file = tmp_path / "bad.py"
        test_file.write_text("def invalid syntax here")

        result = analyzer.analyze_file(str(test_file))

        # Should return error result
        assert result["performance_score"] == 0
        assert "Syntax error" in result["recommendations"][0]

    def test_is_database_query_query_method(self, analyzer):
        """Test database query detection"""
        code = "db.query(User)"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert analyzer._is_database_query(call_node) is True

    def test_is_database_query_filter_method(self, analyzer):
        """Test database query detection with filter"""
        code = "session.filter(items)"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert analyzer._is_database_query(call_node) is True

    def test_is_database_query_regular_method(self, analyzer):
        """Test non-query method"""
        code = "user.save()"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert analyzer._is_database_query(call_node) is False

    def test_is_resource_open_file(self, analyzer):
        """Test resource open detection for file"""
        code = "open('file.txt')"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert analyzer._is_resource_open(call_node) is True

    def test_is_resource_open_connect(self, analyzer):
        """Test resource open detection for connection"""
        code = "db.connect()"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert analyzer._is_resource_open(call_node) is True

    def test_is_resource_open_regular_call(self, analyzer):
        """Test non-resource call"""
        code = "print('hello')"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        assert analyzer._is_resource_open(call_node) is False

    def test_count_nested_loops_single(self, analyzer):
        """Test nested loop counting for single loop"""
        code = """
for i in range(10):
    print(i)
"""
        tree = ast.parse(code)
        loop_node = tree.body[0]

        depth = analyzer._count_nested_loops(loop_node)
        assert depth == 0  # Depth 0 for single loop

    def test_count_nested_loops_double(self, analyzer):
        """Test nested loop counting for double loop"""
        code = """
for i in range(10):
    for j in range(10):
        print(i, j)
"""
        tree = ast.parse(code)
        loop_node = tree.body[0]

        depth = analyzer._count_nested_loops(loop_node)
        assert depth == 1  # Depth 1 for nested loop

    def test_count_nested_loops_triple(self, analyzer):
        """Test nested loop counting for triple loop"""
        code = """
for i in range(10):
    for j in range(10):
        for k in range(10):
            print(i, j, k)
"""
        tree = ast.parse(code)
        loop_node = tree.body[0]

        depth = analyzer._count_nested_loops(loop_node)
        assert depth == 2  # Depth 2 for triple nested

    def test_get_complexity_recommendation_rank_f(self, analyzer):
        """Test complexity recommendation for rank F"""
        rec = analyzer._get_complexity_recommendation("F", 50)
        assert "Extremely complex" in rec
        assert "immediately" in rec.lower()

    def test_get_complexity_recommendation_rank_d(self, analyzer):
        """Test complexity recommendation for rank D"""
        rec = analyzer._get_complexity_recommendation("D", 25)
        assert "Too complex" in rec

    def test_get_complexity_recommendation_rank_c(self, analyzer):
        """Test complexity recommendation for rank C"""
        rec = analyzer._get_complexity_recommendation("C", 15)
        assert "Complex" in rec
