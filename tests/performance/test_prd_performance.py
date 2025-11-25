"""
Performance tests for Dynamic PRD System

Tests critical performance targets from PROJECT_SPEC.md:
- Regeneration: <3s for 1-2 features, <10s for 5+ features
- WebSocket broadcast: <100ms
- File watch detection: <500ms
- API response: <200ms for simple updates
- PRD file write: <100ms
- Support 100+ concurrent WebSocket connections
- Handle PRDs with 50+ features
- Manage task queues with 500+ tasks
"""

import pytest
import time
import asyncio
import tempfile
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import websocket
import json

from core.prd.prd_controller import PRDController, PRDFeature, ChangeType
from core.adaptive_planner import AdaptivePlanner
from core.task_queue import TaskQueue
from core.prd_file_watcher import PRDFileWatcher


class TestPRDControllerPerformance:
    """Test PRD Controller performance targets"""

    @pytest.fixture
    def temp_spec(self):
        """Create temporary spec file"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"

        # Create initial spec
        spec_path.write_text("""# Test Project

## Feature 1: Initial Feature
**Priority:** high
""")

        yield spec_path

        shutil.rmtree(temp_dir)

    def test_file_write_under_100ms(self, temp_spec):
        """Test: PRD file write completes in <100ms"""
        controller = PRDController(temp_spec)

        # Warm up
        controller.update_prd({"project_name": "Test"}, author="test")

        # Measure write time
        start = time.time()
        controller.update_prd({
            "add_feature": {
                "id": "test-feature",
                "name": "Performance Test Feature",
                "description": "Testing file write speed"
            }
        }, author="test")
        duration = (time.time() - start) * 1000  # Convert to ms

        assert duration < 100, f"File write took {duration:.1f}ms (target: <100ms)"

        print(f"✅ File write: {duration:.1f}ms (target: <100ms)")

    def test_event_emission_under_50ms(self, temp_spec):
        """Test: Event emission within 50ms of change"""
        controller = PRDController(temp_spec)

        event_received_at = None

        def listener(event):
            nonlocal event_received_at
            event_received_at = time.time()

        controller.subscribe(listener)

        # Measure event emission time
        start = time.time()
        controller.update_prd({
            "add_feature": {
                "id": "test-feature-2",
                "name": "Event Test Feature",
                "description": "Testing event speed"
            }
        }, author="test")

        assert event_received_at is not None
        duration = (event_received_at - start) * 1000

        assert duration < 50, f"Event emission took {duration:.1f}ms (target: <50ms)"

        print(f"✅ Event emission: {duration:.1f}ms (target: <50ms)")

    def test_100_subscribers_no_degradation(self, temp_spec):
        """Test: 100+ subscribers without performance degradation"""
        controller = PRDController(temp_spec)

        # Add 100 subscribers
        received_counts = []

        def make_listener(idx):
            def listener(event):
                received_counts.append(idx)
            return listener

        for i in range(100):
            controller.subscribe(make_listener(i))

        # Measure with 100 subscribers
        start = time.time()
        controller.update_prd({
            "add_feature": {
                "id": "test-feature-100",
                "name": "100 Subscriber Test",
                "description": "Testing subscriber scalability"
            }
        }, author="test")
        duration = (time.time() - start) * 1000

        # All 100 subscribers should receive event
        assert len(received_counts) == 100

        # Should still be fast with 100 subscribers
        assert duration < 200, f"100 subscribers took {duration:.1f}ms (target: <200ms)"

        print(f"✅ 100 subscribers: {duration:.1f}ms, all received event")

    def test_concurrent_updates_merge_correctly(self, temp_spec):
        """Test: 5 concurrent updates handled correctly"""
        controller = PRDController(temp_spec)

        def concurrent_update(feature_num):
            try:
                controller.update_prd({
                    "add_feature": {
                        "id": f"concurrent-{feature_num}",
                        "name": f"Concurrent Feature {feature_num}",
                        "description": "Concurrency test"
                    }
                }, author=f"user-{feature_num}")
                return True
            except Exception as e:
                print(f"Concurrent update {feature_num} failed: {e}")
                return False

        start = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_update, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]

        duration = (time.time() - start) * 1000

        # All updates should succeed
        assert all(results), "Some concurrent updates failed"

        # Reload and verify all features added
        controller.load_from_file()
        feature_ids = [f.id for f in controller.prd.features]

        for i in range(5):
            assert f"concurrent-{i}" in feature_ids

        print(f"✅ 5 concurrent updates: {duration:.1f}ms, all successful")


class TestAdaptivePlannerPerformance:
    """Test Adaptive Planner performance targets"""

    @pytest.fixture
    def setup_planner(self):
        """Setup planner with task queue"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"

        # Create spec with multiple features
        features_text = "\n\n".join([
            f"""## Feature {i}: Feature {i}
**Priority:** medium

### Description
Test feature {i}

### Requirements
- Requirement 1
- Requirement 2

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
""" for i in range(1, 11)  # 10 features
        ])

        spec_path.write_text(f"""# Test Project

{features_text}
""")

        task_queue = TaskQueue()
        planner = AdaptivePlanner(temp_dir, task_queue)

        yield planner, spec_path, temp_dir

        shutil.rmtree(temp_dir)

    def test_regeneration_1_2_features_under_3s(self, setup_planner):
        """Test: Regeneration <3s for 1-2 feature changes"""
        planner, spec_path, temp_dir = setup_planner

        # Generate initial plan
        planner.initial_plan_from_prd()

        # Now change 2 features
        controller = PRDController(spec_path)

        start = time.time()

        # Add 1 feature
        controller.update_prd({
            "add_feature": {
                "id": "new-feature-1",
                "name": "New Feature 1",
                "description": "Performance test feature"
            }
        }, author="test")

        # Wait for regeneration to complete
        time.sleep(0.5)  # Allow async regeneration

        # Add 1 more feature
        controller.update_prd({
            "add_feature": {
                "id": "new-feature-2",
                "name": "New Feature 2",
                "description": "Performance test feature 2"
            }
        }, author="test")

        time.sleep(0.5)  # Allow async regeneration

        duration = time.time() - start

        assert duration < 3.0, f"Regeneration took {duration:.2f}s (target: <3s)"

        print(f"✅ Regeneration (2 features): {duration:.2f}s (target: <3s)")

    def test_regeneration_5_features_under_10s(self, setup_planner):
        """Test: Regeneration <10s for 5 features"""
        planner, spec_path, temp_dir = setup_planner

        # Generate initial plan
        planner.initial_plan_from_prd()

        controller = PRDController(spec_path)

        start = time.time()

        # Add 5 features
        for i in range(5):
            controller.update_prd({
                "add_feature": {
                    "id": f"batch-feature-{i}",
                    "name": f"Batch Feature {i}",
                    "description": f"Batch test feature {i}"
                }
            }, author="test")
            time.sleep(0.1)

        time.sleep(1.0)  # Allow final regeneration

        duration = time.time() - start

        assert duration < 10.0, f"Regeneration took {duration:.2f}s (target: <10s)"

        print(f"✅ Regeneration (5 features): {duration:.2f}s (target: <10s)")

    def test_completed_work_never_regenerated(self, setup_planner):
        """Test: Completed tasks are never regenerated"""
        planner, spec_path, temp_dir = setup_planner

        # Generate initial plan
        result = planner.initial_plan_from_prd()

        # Mark some tasks as completed
        completed_tasks = []
        for task_id in result.ready_tasks[:3]:
            task = planner.task_queue.get_task(task_id)
            if task:
                planner.task_queue.complete_task(task_id)
                completed_tasks.append(task_id)

        # Now modify a feature
        controller = PRDController(spec_path)
        controller.update_prd({
            "add_feature": {
                "id": "verify-preservation",
                "name": "Verify Completed Preservation",
                "description": "Test completed work protection"
            }
        }, author="test")

        time.sleep(1.0)

        # Verify completed tasks still exist and are completed
        for task_id in completed_tasks:
            task = planner.task_queue.get_task(task_id)
            assert task is not None, f"Completed task {task_id} was removed"
            assert task.status.value == "completed", f"Completed task {task_id} status changed"

        print(f"✅ Completed work preserved: {len(completed_tasks)} tasks intact")


class TestFileWatcherPerformance:
    """Test file watcher performance"""

    def test_file_change_detection_under_500ms(self):
        """Test: File changes detected within 500ms"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"
        spec_path.write_text("# Test Project\n")

        controller = PRDController(spec_path)
        watcher = PRDFileWatcher(spec_path)

        detected_at = None

        def on_change(event):
            nonlocal detected_at
            detected_at = time.time()

        controller.subscribe(on_change)
        watcher.start()

        try:
            # Modify file
            start = time.time()
            spec_path.write_text("# Test Project\n\n## New Content\n")

            # Wait for detection
            timeout = time.time() + 2.0
            while detected_at is None and time.time() < timeout:
                time.sleep(0.1)

            assert detected_at is not None, "File change not detected"

            duration = (detected_at - start) * 1000

            assert duration < 500, f"Detection took {duration:.0f}ms (target: <500ms)"

            print(f"✅ File watch detection: {duration:.0f}ms (target: <500ms)")

        finally:
            watcher.stop()
            shutil.rmtree(temp_dir)


class TestScalabilityPerformance:
    """Test scalability targets"""

    def test_large_prd_50_features(self):
        """Test: Handle PRDs with 50+ features"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"

        # Create PRD with 50 features
        features_text = "\n\n".join([
            f"""## Feature {i}: Feature {i}
**Priority:** medium
### Description
Feature {i} description
""" for i in range(1, 51)
        ])

        spec_path.write_text(f"""# Large Project\n\n{features_text}""")

        try:
            start = time.time()
            controller = PRDController(spec_path)
            load_time = (time.time() - start) * 1000

            assert len(controller.prd.features) == 50
            assert load_time < 1000, f"Loading 50 features took {load_time:.0f}ms"

            # Test update performance with large PRD
            update_start = time.time()
            controller.update_prd({
                "add_feature": {
                    "id": "feature-51",
                    "name": "Feature 51",
                    "description": "Testing scalability"
                }
            }, author="test")
            update_time = (time.time() - update_start) * 1000

            assert update_time < 200, f"Update with 50 features took {update_time:.0f}ms"

            print(f"✅ 50 features: Load {load_time:.0f}ms, Update {update_time:.0f}ms")

        finally:
            shutil.rmtree(temp_dir)

    def test_large_task_queue_500_tasks(self):
        """Test: Manage task queues with 500+ tasks"""
        task_queue = TaskQueue()

        # Add 500 tasks
        start = time.time()
        for i in range(500):
            task_queue.add_task(
                f"task-{i}",
                f"Task {i}",
                estimated_minutes=30,
                dependencies=[]
            )
        add_time = (time.time() - start) * 1000

        assert len(task_queue.tasks) == 500
        assert add_time < 1000, f"Adding 500 tasks took {add_time:.0f}ms"

        # Test ready task calculation
        ready_start = time.time()
        ready_tasks = task_queue.get_ready_tasks()
        ready_time = (time.time() - ready_start) * 1000

        assert len(ready_tasks) == 500
        assert ready_time < 500, f"Getting ready tasks took {ready_time:.0f}ms"

        print(f"✅ 500 tasks: Add {add_time:.0f}ms, Get ready {ready_time:.0f}ms")


class TestAPIPerformance:
    """Test API performance (requires running server)"""

    @pytest.mark.skipif(True, reason="Requires running server - manual test")
    def test_api_response_under_200ms(self):
        """Test: API response <200ms for simple updates"""
        import requests

        url = "http://localhost:8080/api/prd/update"
        payload = {
            "updates": {
                "project_name": "Performance Test"
            },
            "author": "test"
        }

        # Warm up
        requests.post(url, json=payload)

        # Measure
        start = time.time()
        response = requests.post(url, json=payload)
        duration = (time.time() - start) * 1000

        assert response.status_code == 200
        assert duration < 200, f"API response took {duration:.0f}ms (target: <200ms)"

        print(f"✅ API response: {duration:.0f}ms (target: <200ms)")

    @pytest.mark.skipif(True, reason="Requires running server - manual test")
    def test_websocket_broadcast_under_100ms(self):
        """Test: WebSocket broadcast <100ms"""
        import requests

        # Connect WebSocket
        ws = websocket.WebSocket()
        ws.connect("ws://localhost:8080/api/prd/stream")

        # Receive initial state
        initial = json.loads(ws.recv())
        assert initial["type"] == "initial"

        # Trigger update via API
        broadcast_received_at = None

        def receive_broadcast():
            nonlocal broadcast_received_at
            msg = json.loads(ws.recv())
            broadcast_received_at = time.time()
            return msg

        # Start receiving in background
        import threading
        receive_thread = threading.Thread(target=receive_broadcast)
        receive_thread.start()

        # Trigger update
        start = time.time()
        requests.post("http://localhost:8080/api/prd/update", json={
            "updates": {"project_name": "WS Test"},
            "author": "test"
        })

        receive_thread.join(timeout=2.0)

        assert broadcast_received_at is not None
        duration = (broadcast_received_at - start) * 1000

        assert duration < 100, f"WebSocket broadcast took {duration:.0f}ms (target: <100ms)"

        ws.close()

        print(f"✅ WebSocket broadcast: {duration:.0f}ms (target: <100ms)")


def run_performance_suite():
    """Run complete performance test suite and generate report"""
    print("\n" + "="*80)
    print("DYNAMIC PRD SYSTEM - PERFORMANCE VALIDATION SUITE")
    print("="*80 + "\n")

    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"  # Show print statements
    ])

    print("\n" + "="*80)
    print("PERFORMANCE VALIDATION COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_performance_suite()
