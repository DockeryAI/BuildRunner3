"""
Tests for Phase 5: Lockwood Test Reporting.
Tests the test_health table, save/get functions, and _push_to_lockwood().
"""

import pytest
import sqlite3
import os
import tempfile
import json
from unittest.mock import patch, MagicMock, Mock
from http.client import HTTPResponse
from io import BytesIO

# Patch DB paths before importing
_tmp_memory_db = tempfile.mktemp(suffix=".db")
os.environ["MEMORY_DB"] = _tmp_memory_db

_tmp_test_db = tempfile.mktemp(suffix=".db")
os.environ["TEST_DB"] = _tmp_test_db


@pytest.fixture(autouse=True)
def fresh_memory_db(tmp_path):
    """Use a fresh temp DB for each test."""
    db_path = str(tmp_path / "memory.db")
    with patch("core.cluster.memory_store.DB_PATH", db_path):
        from core.cluster.memory_store import _get_db
        conn = _get_db()
        conn.close()
        yield db_path
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


class TestSaveTestHealth:
    def test_save_and_retrieve(self, fresh_memory_db):
        with patch("core.cluster.memory_store.DB_PATH", fresh_memory_db):
            from core.cluster.memory_store import save_test_health, get_test_health

            result = save_test_health(
                project="testproject",
                sha="abc123",
                branch="main",
                pass_rate=95.0,
                total=20,
                passed=19,
                failed=1,
                skipped=0,
                failures=["test_foo"],
                duration_ms=5000,
                runner="vitest",
                trigger="watch",
            )

            assert result["status"] == "saved"
            assert result["project"] == "testproject"
            assert result["sha"] == "abc123"
            assert result["pass_rate"] == 95.0

            # Retrieve
            records = get_test_health("testproject", limit=10)
            assert len(records) == 1
            rec = records[0]
            assert rec["project"] == "testproject"
            assert rec["sha"] == "abc123"
            assert rec["branch"] == "main"
            assert rec["pass_rate"] == 95.0
            assert rec["total"] == 20
            assert rec["passed"] == 19
            assert rec["failed"] == 1
            assert rec["runner"] == "vitest"
            assert rec["trigger"] == "watch"
            assert rec["failures"] == ["test_foo"]

    def test_multiple_records_ordering(self, fresh_memory_db):
        with patch("core.cluster.memory_store.DB_PATH", fresh_memory_db):
            from core.cluster.memory_store import save_test_health, get_test_health

            for i in range(5):
                save_test_health(
                    project="proj",
                    sha=f"sha{i}",
                    pass_rate=float(90 + i),
                    total=10,
                    passed=9 + (1 if i > 2 else 0),
                    failed=1 - (1 if i > 2 else 0),
                    runner="vitest",
                    trigger="watch",
                )

            records = get_test_health("proj", limit=3)
            assert len(records) == 3
            # Should be newest first
            assert records[0]["sha"] == "sha4"
            assert records[2]["sha"] == "sha2"

    def test_legacy_compat(self, fresh_memory_db):
        """save_test_health should also write to legacy test_results."""
        with patch("core.cluster.memory_store.DB_PATH", fresh_memory_db):
            from core.cluster.memory_store import save_test_health, get_latest_test_results

            save_test_health(
                project="legacyproj",
                passed=10,
                failed=2,
                skipped=1,
                duration_ms=3000,
                runner="vitest",
            )

            legacy = get_latest_test_results("legacyproj")
            assert len(legacy) == 1
            assert legacy[0]["passed"] == 10
            assert legacy[0]["failed"] == 2

    def test_get_all_projects(self, fresh_memory_db):
        with patch("core.cluster.memory_store.DB_PATH", fresh_memory_db):
            from core.cluster.memory_store import save_test_health, get_test_health

            save_test_health(project="proj1", total=5, passed=5, runner="vitest")
            save_test_health(project="proj2", total=3, passed=2, failed=1, runner="vitest")

            all_records = get_test_health(limit=10)
            assert len(all_records) == 2


class TestPushToLockwood:
    def test_push_success(self):
        from core.cluster.node_tests import _push_to_lockwood

        results = {
            "project": "testproj",
            "git_sha": "abc123",
            "git_branch": "main",
            "total": 10,
            "passed": 9,
            "failed": 1,
            "skipped": 0,
            "duration_ms": 5000,
            "runner": "vitest",
            "tests": [
                {"full_name": "test_fail", "status": "failed"},
                {"full_name": "test_pass", "status": "passed"},
            ],
        }

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status":"saved"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("core.cluster.node_tests.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            result = _push_to_lockwood(results, trigger="watch")

            assert result is True
            mock_urlopen.assert_called_once()
            # Verify the payload
            call_args = mock_urlopen.call_args
            req_obj = call_args[0][0]
            payload = json.loads(req_obj.data.decode("utf-8"))
            assert payload["project"] == "testproj"
            assert payload["sha"] == "abc123"
            assert payload["pass_rate"] == 90.0
            assert payload["trigger"] == "watch"
            assert payload["failures"] == ["test_fail"]

    def test_push_retry_on_failure(self):
        from core.cluster.node_tests import _push_to_lockwood
        import urllib.error

        results = {"project": "proj", "total": 1, "passed": 1, "runner": "vitest", "tests": []}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status":"saved"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch("core.cluster.node_tests.urllib.request.urlopen") as mock_urlopen:
            with patch("core.cluster.node_tests.time.sleep"):
                # First call fails, second succeeds
                mock_urlopen.side_effect = [
                    urllib.error.URLError("connection refused"),
                    mock_response,
                ]
                result = _push_to_lockwood(results, trigger="manual")

                assert result is True
                assert mock_urlopen.call_count == 2

    def test_push_both_attempts_fail(self):
        from core.cluster.node_tests import _push_to_lockwood
        import urllib.error

        results = {"project": "proj", "total": 1, "passed": 0, "failed": 1, "runner": "vitest", "tests": []}

        with patch("core.cluster.node_tests.urllib.request.urlopen") as mock_urlopen:
            with patch("core.cluster.node_tests.time.sleep"):
                mock_urlopen.side_effect = urllib.error.URLError("connection refused")
                result = _push_to_lockwood(results, trigger="hook")

                assert result is False
                assert mock_urlopen.call_count == 2

    def test_push_empty_results(self):
        from core.cluster.node_tests import _push_to_lockwood

        result = _push_to_lockwood(None)
        assert result is None

        result = _push_to_lockwood({})
        assert result is None
