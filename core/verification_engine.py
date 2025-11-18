"""
Verification Engine for Task Orchestration

Verifies task completion quality through file checks, test execution,
and acceptance criteria validation.
"""

from typing import List, Dict, Optional
from pathlib import Path
import subprocess


class VerificationResult:
    """Result of verification check"""

    def __init__(self, passed: bool, message: str, details: Optional[Dict] = None):
        self.passed = passed
        self.message = message
        self.details = details or {}

    def __bool__(self):
        return self.passed


class VerificationEngine:
    """
    Verifies task completion and quality.

    Responsibilities:
    - Verify files created
    - Run tests
    - Check acceptance criteria
    - Validate code quality
    - Report issues
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()

        # Statistics
        self.verifications_run = 0
        self.verifications_passed = 0
        self.verifications_failed = 0

    def verify_files_exist(self, file_paths: List[str]) -> VerificationResult:
        """
        Verify that all required files exist.

        Args:
            file_paths: List of file paths to check

        Returns:
            VerificationResult
        """
        self.verifications_run += 1

        missing = []
        for file_path in file_paths:
            path = self.project_root / file_path
            if not path.exists():
                missing.append(file_path)

        if missing:
            self.verifications_failed += 1
            return VerificationResult(
                passed=False,
                message=f"Missing {len(missing)} files",
                details={"missing_files": missing},
            )

        self.verifications_passed += 1
        return VerificationResult(
            passed=True,
            message=f"All {len(file_paths)} files exist",
            details={"verified_files": file_paths},
        )

    def verify_tests_pass(
        self,
        test_paths: Optional[List[str]] = None,
        test_command: str = "pytest",
    ) -> VerificationResult:
        """
        Verify that tests pass.

        Args:
            test_paths: Optional specific test paths
            test_command: Test command to run

        Returns:
            VerificationResult
        """
        self.verifications_run += 1

        try:
            # Build command
            cmd = [test_command]
            if test_paths:
                cmd.extend(test_paths)
            cmd.extend(["-v", "--tb=short"])

            # Run tests
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                self.verifications_passed += 1
                return VerificationResult(
                    passed=True,
                    message="All tests passed",
                    details={"output": result.stdout},
                )
            else:
                self.verifications_failed += 1
                return VerificationResult(
                    passed=False,
                    message="Tests failed",
                    details={
                        "return_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                    },
                )

        except subprocess.TimeoutExpired:
            self.verifications_failed += 1
            return VerificationResult(
                passed=False,
                message="Tests timed out",
            )
        except Exception as e:
            self.verifications_failed += 1
            return VerificationResult(
                passed=False,
                message=f"Test execution error: {str(e)}",
            )

    def verify_no_import_errors(self, file_paths: List[str]) -> VerificationResult:
        """
        Verify that files have no import errors.

        Args:
            file_paths: List of Python files to check

        Returns:
            VerificationResult
        """
        self.verifications_run += 1

        errors = []
        for file_path in file_paths:
            path = self.project_root / file_path

            if not path.exists():
                errors.append(f"{file_path}: File not found")
                continue

            try:
                # Try importing (basic syntax check)
                result = subprocess.run(
                    ["python", "-m", "py_compile", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    errors.append(f"{file_path}: {result.stderr}")

            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")

        if errors:
            self.verifications_failed += 1
            return VerificationResult(
                passed=False,
                message=f"Import errors in {len(errors)} files",
                details={"errors": errors},
            )

        self.verifications_passed += 1
        return VerificationResult(
            passed=True,
            message=f"No import errors in {len(file_paths)} files",
        )

    def verify_acceptance_criteria(
        self,
        criteria: List[str],
        checklist: Dict[str, bool],
    ) -> VerificationResult:
        """
        Verify acceptance criteria met.

        Args:
            criteria: List of acceptance criteria
            checklist: Dict of criteria -> bool (met or not)

        Returns:
            VerificationResult
        """
        self.verifications_run += 1

        unmet = []
        for criterion in criteria:
            if not checklist.get(criterion, False):
                unmet.append(criterion)

        if unmet:
            self.verifications_failed += 1
            return VerificationResult(
                passed=False,
                message=f"{len(unmet)} criteria not met",
                details={"unmet_criteria": unmet},
            )

        self.verifications_passed += 1
        return VerificationResult(
            passed=True,
            message=f"All {len(criteria)} criteria met",
        )

    def verify_batch_completion(
        self,
        batch,
        run_tests: bool = True,
        check_imports: bool = True,
    ) -> VerificationResult:
        """
        Comprehensive verification of batch completion.

        Args:
            batch: Batch to verify
            run_tests: Whether to run tests
            check_imports: Whether to check imports

        Returns:
            VerificationResult
        """
        self.verifications_run += 1

        failures = []

        # Get file paths from batch
        file_paths = []
        test_paths = []

        batch_tasks = batch.tasks if hasattr(batch, "tasks") else []
        for task in batch_tasks:
            if hasattr(task, "file_path"):
                file_paths.append(task.file_path)

                # Infer test path
                path = Path(task.file_path)
                if path.parent.name in ["core", "cli", "api"]:
                    test_path = f"tests/test_{path.stem}.py"
                    test_paths.append(test_path)

        # Verify files exist
        files_result = self.verify_files_exist(file_paths)
        if not files_result:
            failures.append(files_result.message)

        # Verify test files exist
        if test_paths:
            test_files_result = self.verify_files_exist(test_paths)
            if not test_files_result:
                failures.append(f"Test files: {test_files_result.message}")

        # Check imports
        if check_imports and file_paths:
            import_result = self.verify_no_import_errors(file_paths)
            if not import_result:
                failures.append(import_result.message)

        # Run tests
        if run_tests and test_paths:
            test_result = self.verify_tests_pass(test_paths)
            if not test_result:
                failures.append(test_result.message)

        if failures:
            self.verifications_failed += 1
            return VerificationResult(
                passed=False,
                message=f"Batch verification failed: {len(failures)} issues",
                details={"failures": failures},
            )

        self.verifications_passed += 1
        return VerificationResult(
            passed=True,
            message="Batch verification passed",
            details={"verified_files": len(file_paths)},
        )

    def get_stats(self) -> Dict:
        """Get verification statistics"""
        total = self.verifications_run
        if total == 0:
            success_rate = 0
        else:
            success_rate = (self.verifications_passed / total) * 100

        return {
            "verifications_run": self.verifications_run,
            "verifications_passed": self.verifications_passed,
            "verifications_failed": self.verifications_failed,
            "success_rate": success_rate,
        }
