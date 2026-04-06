"""
Tests for Walter's test_file_map feature (Phase 3: Test Map).
Tests the source→test mapping, API endpoints, and auto-rebuild.
"""

import pytest
import sqlite3
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

# Patch DB_PATH before importing to use temp DB
_tmp_db = tempfile.mktemp(suffix=".db")
os.environ["TEST_DB"] = _tmp_db

from core.cluster.node_tests import (
    _get_db,
    _ensure_tables,
    build_test_map,
    get_test_map,
)
from fastapi.testclient import TestClient
from core.cluster.node_tests import app


@pytest.fixture(autouse=True)
def fresh_db():
    """Use a fresh temp DB for each test."""
    global _tmp_db
    _tmp_db = tempfile.mktemp(suffix=".db")
    os.environ["TEST_DB"] = _tmp_db
    # Reimport won't work, so we patch DB_PATH
    import core.cluster.node_tests as mod
    mod.DB_PATH = _tmp_db
    yield
    try:
        os.unlink(_tmp_db)
    except FileNotFoundError:
        pass


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def sample_repo(tmp_path):
    """Create a sample repo structure with source and test files."""
    # Source files
    src = tmp_path / "src" / "auth"
    src.mkdir(parents=True)
    (src / "middleware.ts").write_text("export function authMiddleware() {}")
    (src / "utils.ts").write_text("export function hashPassword() {}")

    # Test files that import source
    tests = tmp_path / "src" / "auth" / "__tests__"
    tests.mkdir(parents=True)
    (tests / "middleware.test.ts").write_text(
        'import { authMiddleware } from "../middleware"\n'
        'describe("auth middleware", () => { it("works", () => {}) })'
    )

    # Convention-based test (foo.test.ts next to foo.ts)
    (src / "utils.test.ts").write_text(
        'describe("utils", () => { it("hashes", () => {}) })'
    )

    return tmp_path


class TestTestFileMapTable:
    """Test that the test_file_map table is created correctly."""

    def test_table_exists(self):
        conn = _get_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_file_map'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_table_columns(self):
        conn = _get_db()
        cursor = conn.execute("PRAGMA table_info(test_file_map)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "project" in columns
        assert "test_file" in columns
        assert "source_file" in columns
        assert "confidence" in columns
        assert "last_verified" in columns
        conn.close()

    def test_index_exists(self):
        conn = _get_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_testmap_project_source'"
        )
        assert cursor.fetchone() is not None
        conn.close()


class TestBuildTestMap:
    """Test the build_test_map function."""

    def test_maps_imports(self, sample_repo):
        build_test_map("test-project", str(sample_repo))
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM test_file_map WHERE project = 'test-project' AND confidence = 'import'"
        ).fetchall()
        assert len(rows) > 0
        conn.close()

    def test_maps_conventions(self, sample_repo):
        build_test_map("test-project", str(sample_repo))
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM test_file_map WHERE project = 'test-project' AND confidence = 'convention'"
        ).fetchall()
        assert len(rows) > 0
        conn.close()

    def test_clears_old_entries(self, sample_repo):
        """Rebuilding should replace old entries."""
        build_test_map("test-project", str(sample_repo))
        build_test_map("test-project", str(sample_repo))
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM test_file_map WHERE project = 'test-project'"
        ).fetchall()
        # Should not have duplicates
        pairs = [(r["test_file"], r["source_file"]) for r in rows]
        assert len(pairs) == len(set(pairs))
        conn.close()


class TestGetTestMap:
    """Test the get_test_map function."""

    def test_returns_mapped_tests(self, sample_repo):
        build_test_map("test-project", str(sample_repo))
        result = get_test_map(["src/auth/middleware.ts"], "test-project")
        assert "src/auth/middleware.ts" in result
        assert len(result["src/auth/middleware.ts"]) > 0

    def test_returns_empty_for_unmapped(self, sample_repo):
        build_test_map("test-project", str(sample_repo))
        result = get_test_map(["nonexistent.ts"], "test-project")
        assert result.get("nonexistent.ts", []) == []

    def test_includes_confidence(self, sample_repo):
        build_test_map("test-project", str(sample_repo))
        result = get_test_map(["src/auth/middleware.ts"], "test-project")
        for entry in result.get("src/auth/middleware.ts", []):
            assert "confidence" in entry
            assert entry["confidence"] in ("import", "convention", "manual")


class TestTestMapAPI:
    """Test the API endpoints."""

    def test_get_testmap(self, client, sample_repo):
        # First build the map
        build_test_map("test-project", str(sample_repo))
        resp = client.get("/api/testmap", params={"files": "src/auth/middleware.ts", "project": "test-project"})
        assert resp.status_code == 200
        data = resp.json()
        assert "src/auth/middleware.ts" in data

    def test_post_baseline(self, client, sample_repo):
        build_test_map("test-project", str(sample_repo))
        resp = client.post(
            "/api/testmap/baseline",
            params={"project": "test-project", "files": "src/auth/middleware.ts"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
