"""Tests for VerificationEngine"""

import pytest
from core.verification_engine import VerificationEngine, VerificationResult
from pathlib import Path
import tempfile
import shutil


class TestVerificationResult:
    def test_init(self):
        result = VerificationResult(True, "Success")
        assert result.passed is True
        assert result.message == "Success"

    def test_bool(self):
        assert VerificationResult(True, "Pass")
        result = VerificationResult(False, "Fail")
        assert not result


class TestVerificationEngine:
    @pytest.fixture
    def temp_project_root(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def engine(self, temp_project_root):
        return VerificationEngine(project_root=temp_project_root)

    def test_init(self, engine):
        assert engine.verifications_run == 0

    def test_verify_files_exist_all_present(self, engine, temp_project_root):
        # Create files
        (temp_project_root / "test1.py").write_text("# test")
        (temp_project_root / "test2.py").write_text("# test")

        result = engine.verify_files_exist(["test1.py", "test2.py"])
        assert result.passed is True

    def test_verify_files_exist_missing(self, engine):
        result = engine.verify_files_exist(["missing.py"])
        assert result.passed is False
        assert "missing.py" in result.details["missing_files"]

    def test_verify_acceptance_criteria_all_met(self, engine):
        criteria = ["Criterion 1", "Criterion 2"]
        checklist = {"Criterion 1": True, "Criterion 2": True}

        result = engine.verify_acceptance_criteria(criteria, checklist)
        assert result.passed is True

    def test_verify_acceptance_criteria_unmet(self, engine):
        criteria = ["Criterion 1", "Criterion 2"]
        checklist = {"Criterion 1": True, "Criterion 2": False}

        result = engine.verify_acceptance_criteria(criteria, checklist)
        assert result.passed is False
        assert "Criterion 2" in result.details["unmet_criteria"]

    def test_get_stats(self, engine):
        stats = engine.get_stats()
        assert "verifications_run" in stats
        assert "success_rate" in stats
