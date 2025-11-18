"""Tests for StatePersistence"""

import pytest
from core.state_persistence import StatePersistence
from pathlib import Path
import tempfile
import shutil


class TestStatePersistence:
    @pytest.fixture
    def temp_project_root(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def persistence(self, temp_project_root):
        return StatePersistence(project_root=temp_project_root)

    def test_init(self, persistence, temp_project_root):
        assert persistence.project_root == temp_project_root
        assert persistence.state_dir.exists()

    def test_save_state(self, persistence):
        tasks = {"task1": {"id": "task1", "status": "completed"}}
        execution_order = ["task1"]
        progress = {"completed": 1}

        result = persistence.save_state(tasks, execution_order, progress)
        assert result is True

    def test_load_state(self, persistence):
        tasks = {"task1": {"id": "task1", "status": "completed"}}
        execution_order = ["task1"]
        progress = {"completed": 1}

        persistence.save_state(tasks, execution_order, progress)
        loaded = persistence.load_state()

        assert loaded is not None
        assert loaded["tasks"] == tasks
        assert loaded["execution_order"] == execution_order

    def test_load_nonexistent_state(self, persistence):
        result = persistence.load_state("nonexistent.json")
        assert result is None

    def test_delete_state(self, persistence):
        tasks = {"task1": {}}
        persistence.save_state(tasks, [], {})
        result = persistence.delete_state()
        assert result is True

    def test_list_state_files(self, persistence):
        persistence.save_state({"task1": {}}, [], {})
        files = persistence.list_state_files()
        assert len(files) > 0

    def test_save_checkpoint(self, persistence):
        tasks = {"task1": {}}
        result = persistence.save_checkpoint(
            tasks, [], {}, "test_checkpoint"
        )
        assert result is True

    def test_load_checkpoint(self, persistence):
        tasks = {"task1": {"status": "done"}}
        persistence.save_checkpoint(tasks, [], {}, "test")
        loaded = persistence.load_checkpoint("test")
        assert loaded is not None
        assert loaded["metadata"]["checkpoint"] == "test"

    def test_clear_all_state(self, persistence):
        persistence.save_state({"task1": {}}, [], {})
        persistence.save_state({"task2": {}}, [], {}, "state2.json")
        deleted = persistence.clear_all_state()
        assert deleted >= 1

    def test_get_stats(self, persistence):
        stats = persistence.get_stats()
        assert "state_files_count" in stats
        assert "total_size_bytes" in stats
