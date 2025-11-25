"""
End-to-End tests for complete PRD system

Tests complete user flows:
1. Natural language → PRD update → Task regeneration
2. UI editor → API → WebSocket broadcast → Multi-client sync
3. File edit → Detection → Plan update → Broadcast
4. Version history and rollback
5. Error recovery scenarios
"""

import pytest
import asyncio
import time
import tempfile
import shutil
from pathlib import Path
import json
from unittest.mock import Mock, AsyncMock

from core.prd.prd_controller import PRDController, get_prd_controller
from core.adaptive_planner import AdaptivePlanner
from core.task_queue import TaskQueue
from core.prd_file_watcher import PRDFileWatcher
from core.prd_integration import PRDSystemIntegration


class TestCompleteUserFlows:
    """Test complete end-to-end user workflows"""

    @pytest.fixture
    def setup_system(self):
        """Setup complete PRD system"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"

        # Create initial spec
        spec_path.write_text("""# Test Project

## Overview
Test project for E2E testing

## Feature 1: Initial Feature
**Priority:** high

### Description
Initial feature for testing

### Requirements
- Requirement 1
- Requirement 2

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
""")

        # Initialize system
        task_queue = TaskQueue()
        controller = PRDController(spec_path)
        planner = AdaptivePlanner(temp_dir, task_queue)
        integration = PRDSystemIntegration(temp_dir, spec_path)

        yield {
            "temp_dir": temp_dir,
            "spec_path": spec_path,
            "controller": controller,
            "planner": planner,
            "integration": integration,
            "task_queue": task_queue
        }

        # Cleanup
        integration.stop()
        shutil.rmtree(temp_dir)

    def test_natural_language_to_tasks_flow(self, setup_system):
        """
        Test: User says "add authentication" → PRD updates → Tasks generated

        Flow:
        1. Parse natural language input
        2. Update PRD
        3. Emit event
        4. Adaptive planner regenerates tasks
        5. Tasks available in queue
        """
        sys = setup_system
        sys["integration"].start(enable_file_watcher=False)

        # Initial task count
        initial_tasks = len(sys["task_queue"].tasks)

        # Step 1: Parse natural language
        updates = sys["controller"].parse_natural_language("add authentication feature")
        assert "add_feature" in updates
        assert updates["add_feature"]["name"] == "Authentication Feature"

        # Step 2: Update PRD
        event = sys["controller"].update_prd(updates, author="user")

        # Step 3: Verify event emitted
        assert event.event_type.value == "feature_added"
        assert len(event.affected_features) == 1

        # Step 4: Wait for regeneration
        time.sleep(0.5)

        # Step 5: Verify tasks generated
        new_task_count = len(sys["task_queue"].tasks)
        assert new_task_count > initial_tasks, "New tasks should be generated"

        # Verify feature exists in PRD
        feature_ids = [f.id for f in sys["controller"].prd.features]
        assert any("authentication" in fid.lower() for fid in feature_ids)

        print(f"✅ NL → Tasks: {new_task_count - initial_tasks} tasks generated")

    def test_file_edit_detection_and_update(self, setup_system):
        """
        Test: User edits PROJECT_SPEC.md → File watcher detects → Plan updates

        Flow:
        1. Start file watcher
        2. Edit file directly
        3. Wait for detection
        4. Verify PRD reloaded
        5. Verify event emitted
        6. Verify tasks regenerated
        """
        sys = setup_system
        sys["integration"].start(enable_file_watcher=True)

        # Track events
        events_received = []

        def event_listener(event):
            events_received.append(event)

        sys["controller"].subscribe(event_listener)

        # Initial state
        initial_feature_count = len(sys["controller"].prd.features)

        # Edit file
        new_content = sys["spec_path"].read_text() + """

## Feature 2: New Feature from File Edit
**Priority:** medium

### Description
This feature was added by editing the file directly

### Requirements
- Requirement A
- Requirement B
"""
        sys["spec_path"].write_text(new_content)

        # Wait for detection
        timeout = time.time() + 3.0
        while len(events_received) == 0 and time.time() < timeout:
            time.sleep(0.1)

        assert len(events_received) > 0, "File change event not received"

        # Verify PRD updated
        new_feature_count = len(sys["controller"].prd.features)
        assert new_feature_count == initial_feature_count + 1

        # Verify event details
        event = events_received[0]
        assert event.event_type.value == "feature_added"
        assert len(event.affected_features) == 1

        print(f"✅ File edit detected in {len(events_received)} events")

    def test_version_history_and_rollback(self, setup_system):
        """
        Test: Multiple changes → Version history → Rollback works

        Flow:
        1. Make 3 PRD changes
        2. Verify 3 versions saved
        3. Rollback to version 1
        4. Verify state restored
        5. Verify event emitted
        """
        sys = setup_system
        sys["integration"].start(enable_file_watcher=False)

        # Make 3 changes
        for i in range(3):
            sys["controller"].update_prd({
                "add_feature": {
                    "id": f"version-test-{i}",
                    "name": f"Version Test Feature {i}",
                    "description": "Testing version control"
                }
            }, author="test")

        # Check version history
        versions = sys["controller"].get_versions()
        assert len(versions) >= 3

        # Current state
        current_features = len(sys["controller"].prd.features)

        # Rollback to first version
        sys["controller"].rollback_to_version(0)

        # Verify rollback
        rolled_back_features = len(sys["controller"].prd.features)
        assert rolled_back_features < current_features

        # Verify first version state
        assert rolled_back_features == 1  # Only initial feature

        print(f"✅ Rollback: {current_features} → {rolled_back_features} features")

    def test_completed_work_preservation(self, setup_system):
        """
        Test: Mark tasks complete → Update PRD → Completed tasks preserved

        Flow:
        1. Generate initial plan
        2. Mark some tasks as completed
        3. Update PRD (add new feature)
        4. Verify completed tasks still exist
        5. Verify completed tasks still marked as completed
        """
        sys = setup_system
        sys["integration"].start(enable_file_watcher=False)

        # Generate initial plan
        result = sys["planner"].initial_plan_from_prd()
        assert result.tasks_generated > 0

        # Complete some tasks
        completed_task_ids = []
        for task_id in result.ready_tasks[:2]:
            sys["task_queue"].complete_task(task_id)
            completed_task_ids.append(task_id)

        assert len(completed_task_ids) == 2

        # Update PRD
        sys["controller"].update_prd({
            "add_feature": {
                "id": "preservation-test",
                "name": "Preservation Test Feature",
                "description": "Testing completed work preservation"
            }
        }, author="test")

        time.sleep(0.5)

        # Verify completed tasks preserved
        for task_id in completed_task_ids:
            task = sys["task_queue"].get_task(task_id)
            assert task is not None, f"Completed task {task_id} was removed"
            assert task.status.value == "completed", f"Completed task {task_id} status changed"

        print(f"✅ Preserved {len(completed_task_ids)} completed tasks")

    def test_concurrent_updates_from_multiple_sources(self, setup_system):
        """
        Test: API update + File edit happening concurrently → Both handled correctly

        Flow:
        1. Start file watcher
        2. Trigger API update
        3. Immediately edit file
        4. Both changes should be processed
        5. Final state should have both changes
        """
        sys = setup_system
        sys["integration"].start(enable_file_watcher=True)

        # Track all events
        events = []

        def track_events(event):
            events.append(event)

        sys["controller"].subscribe(track_events)

        initial_count = len(sys["controller"].prd.features)

        # API update
        sys["controller"].update_prd({
            "add_feature": {
                "id": "api-update",
                "name": "API Update Feature",
                "description": "From API"
            }
        }, author="api-user")

        # File edit (immediate)
        content = sys["spec_path"].read_text()
        sys["spec_path"].write_text(content + """

## Feature X: File Edit Feature
**Priority:** low
""")

        # Wait for both to process
        time.sleep(2.0)

        # Verify both changes applied
        final_count = len(sys["controller"].prd.features)
        assert final_count >= initial_count + 2

        # Verify both features exist
        feature_ids = [f.id for f in sys["controller"].prd.features]
        assert "api-update" in feature_ids
        assert any("feature-x" in fid.lower() for fid in feature_ids)

        print(f"✅ Concurrent updates: {len(events)} events, {final_count} features")


class TestMultiClientSync:
    """Test multi-client WebSocket synchronization"""

    @pytest.fixture
    def setup_system(self):
        """Setup system with mock WebSocket clients"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"

        spec_path.write_text("# Test Project\n")

        integration = PRDSystemIntegration(temp_dir, spec_path)

        # Mock WebSocket clients
        mock_clients = [Mock() for _ in range(3)]
        mock_broadcast = AsyncMock()

        # Track broadcasts
        broadcasts = []

        async def capture_broadcast(event):
            broadcasts.append(event)
            await mock_broadcast(event)

        integration.set_websocket_broadcast_handler(capture_broadcast)
        integration.start(enable_file_watcher=False)

        yield {
            "temp_dir": temp_dir,
            "spec_path": spec_path,
            "integration": integration,
            "controller": integration.controller,
            "clients": mock_clients,
            "broadcasts": broadcasts
        }

        integration.stop()
        shutil.rmtree(temp_dir)

    def test_single_update_broadcasts_to_all_clients(self, setup_system):
        """
        Test: Single PRD update → Broadcast to all connected clients

        Flow:
        1. 3 clients connected
        2. Update PRD
        3. All 3 clients receive update
        4. Update contains correct data
        """
        sys = setup_system

        # Update PRD
        sys["controller"].update_prd({
            "add_feature": {
                "id": "broadcast-test",
                "name": "Broadcast Test Feature",
                "description": "Testing broadcast"
            }
        }, author="test")

        # Wait for async broadcast
        time.sleep(0.5)

        # Verify broadcast occurred
        assert len(sys["broadcasts"]) > 0

        # Verify event content
        event = sys["broadcasts"][0]
        assert event.event_type.value == "feature_added"
        assert "broadcast-test" in event.affected_features

        print(f"✅ Broadcast: {len(sys['broadcasts'])} events sent to {len(sys['clients'])} clients")

    def test_file_edit_broadcasts_to_clients(self, setup_system):
        """Test: File edit → Detected → Broadcast to clients"""
        sys = setup_system

        # Start file watcher
        from core.prd_file_watcher import start_prd_watcher
        watcher = start_prd_watcher(sys["spec_path"])

        try:
            # Edit file
            sys["spec_path"].write_text("""# Test Project

## Feature 1: From File
**Priority:** high
""")

            # Wait for detection and broadcast
            timeout = time.time() + 3.0
            while len(sys["broadcasts"]) == 0 and time.time() < timeout:
                time.sleep(0.1)

            assert len(sys["broadcasts"]) > 0, "File edit not broadcast"

            print(f"✅ File edit broadcast: {len(sys['broadcasts'])} events")

        finally:
            from core.prd_file_watcher import stop_prd_watcher
            stop_prd_watcher()


class TestErrorRecovery:
    """Test error handling and recovery"""

    def test_invalid_natural_language_doesnt_crash(self):
        """Test: Invalid NL input returns empty updates gracefully"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"
        spec_path.write_text("# Test\n")

        try:
            controller = PRDController(spec_path)

            # Invalid inputs
            invalid_inputs = [
                "",
                "asdfasdfasdf",
                "!@#$%^&*()",
                "delete everything",
                "make it better"
            ]

            for input_text in invalid_inputs:
                updates = controller.parse_natural_language(input_text)
                # Should return empty dict, not crash
                assert isinstance(updates, dict)

            print(f"✅ Handled {len(invalid_inputs)} invalid inputs gracefully")

        finally:
            shutil.rmtree(temp_dir)

    def test_corrupted_spec_file_recovery(self):
        """Test: Corrupted PROJECT_SPEC.md doesn't crash system"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"

        # Create valid spec
        spec_path.write_text("# Valid Project\n")
        controller = PRDController(spec_path)

        try:
            # Corrupt the file
            spec_path.write_text("### Invalid markdown\n**Unclosed bold\n")

            # Try to reload - should handle gracefully
            try:
                controller.load_from_file()
                # Should not crash, though PRD might be in unexpected state
                assert controller.prd is not None
            except Exception as e:
                # Expected to fail gracefully, not crash
                assert "PRD" in str(e) or "parse" in str(e).lower()

            print("✅ Handled corrupted file gracefully")

        finally:
            shutil.rmtree(temp_dir)


def run_e2e_suite():
    """Run complete E2E test suite"""
    print("\n" + "="*80)
    print("DYNAMIC PRD SYSTEM - END-TO-END TEST SUITE")
    print("="*80 + "\n")

    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"
    ])

    print("\n" + "="*80)
    print("E2E TESTS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_e2e_suite()
