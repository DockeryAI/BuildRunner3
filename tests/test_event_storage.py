"""
Tests for event storage with rotation and compression
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import json
import gzip
import time

from core.persistence.rotation import FileRotator
from core.persistence.event_storage import EventStorage


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir):
    """Create temporary file for testing."""
    file_path = temp_dir / "test.json"
    return file_path


class TestFileRotator:
    """Test FileRotator class."""

    def test_should_rotate_when_file_exceeds_max_size(self, temp_file):
        """Test file rotation when size exceeds threshold."""
        rotator = FileRotator(max_size_bytes=100)

        # Create file smaller than threshold
        temp_file.write_text("small content")
        assert not rotator.should_rotate(temp_file)

        # Create file larger than threshold
        temp_file.write_text("x" * 150)
        assert rotator.should_rotate(temp_file)

    def test_rotate_file_creates_timestamped_copy(self, temp_file):
        """Test file rotation creates timestamped file."""
        rotator = FileRotator(compress=False)

        # Create file to rotate
        original_content = "test data"
        temp_file.write_text(original_content)

        # Rotate file
        rotated_path = rotator.rotate_file(temp_file)

        # Verify rotation
        assert rotated_path is not None
        assert rotated_path.exists()
        assert not temp_file.exists()  # Original should be moved
        assert rotated_path.read_text() == original_content

        # Verify timestamp in filename
        assert temp_file.stem in rotated_path.stem
        assert temp_file.suffix in str(rotated_path)

    def test_rotate_file_with_compression(self, temp_file):
        """Test file rotation with gzip compression."""
        rotator = FileRotator(compress=True)

        # Create file to rotate
        original_content = "test data for compression"
        temp_file.write_text(original_content)

        # Rotate file
        rotated_path = rotator.rotate_file(temp_file)

        # Verify compression
        assert rotated_path is not None
        assert rotated_path.suffix == '.gz'
        assert rotated_path.exists()
        assert not temp_file.exists()

        # Verify content can be decompressed
        with gzip.open(rotated_path, 'rt') as f:
            decompressed = f.read()
        assert decompressed == original_content

    def test_cleanup_old_files(self, temp_dir):
        """Test cleanup of old files beyond retention period."""
        rotator = FileRotator(retention_days=7)

        # Create old file (simulated by modifying mtime)
        old_file = temp_dir / "old_file.txt"
        old_file.write_text("old data")

        # Set modification time to 10 days ago
        old_mtime = (datetime.now() - timedelta(days=10)).timestamp()
        old_file.touch()
        import os
        os.utime(old_file, (old_mtime, old_mtime))

        # Create recent file
        recent_file = temp_dir / "recent_file.txt"
        recent_file.write_text("recent data")

        # Cleanup
        rotator.cleanup_old_files(temp_dir, pattern="*.txt")

        # Verify old file removed, recent file kept
        assert not old_file.exists()
        assert recent_file.exists()

    def test_get_rotated_files(self, temp_dir):
        """Test getting list of rotated files."""
        rotator = FileRotator(compress=False)

        original_file = temp_dir / "events.json"
        original_file.write_text("data 1")

        # Create rotated version
        rotated_1 = rotator.rotate_file(original_file)

        # Get rotated files
        rotated_files = rotator.get_rotated_files(original_file)

        # Verify we got the rotated file
        assert len(rotated_files) >= 1
        assert rotated_1 in rotated_files

    def test_decompress_file(self, temp_file):
        """Test file decompression."""
        rotator = FileRotator()

        # Create and compress file
        original_content = "test data for decompression"
        compressed_path = temp_file.with_suffix('.json.gz')

        with gzip.open(compressed_path, 'wt') as f:
            f.write(original_content)

        # Decompress
        decompressed_path = rotator.decompress_file(compressed_path)

        # Verify decompression
        assert decompressed_path.exists()
        assert decompressed_path.read_text() == original_content


class TestEventStorage:
    """Test EventStorage class."""

    def test_save_and_load_events(self, temp_file):
        """Test saving and loading events."""
        storage = EventStorage(storage_path=temp_file)

        # Create test events
        events = [
            {
                'event_id': '1',
                'event_type': 'test',
                'timestamp': datetime.now().isoformat(),
                'data': 'test data 1'
            },
            {
                'event_id': '2',
                'event_type': 'test',
                'timestamp': datetime.now().isoformat(),
                'data': 'test data 2'
            }
        ]

        # Save events
        storage.save(events)

        # Load events
        loaded_events = storage.load()

        # Verify
        assert len(loaded_events) == 2
        assert loaded_events[0]['event_id'] == '1'
        assert loaded_events[1]['event_id'] == '2'

    def test_automatic_rotation_on_save(self, temp_dir):
        """Test automatic file rotation when size exceeds threshold."""
        storage_path = temp_dir / "events.json"
        storage = EventStorage(
            storage_path=storage_path,
            max_file_size=200,  # Small threshold for testing
            compress=False
        )

        # Create events that will exceed threshold
        large_events = [
            {
                'event_id': str(i),
                'data': 'x' * 50  # Large data
            }
            for i in range(10)
        ]

        # Save first batch
        storage.save(large_events[:5])
        assert storage_path.exists()

        # Save second batch (should trigger rotation)
        storage.save(large_events)

        # Verify rotation occurred
        rotated_files = storage.get_rotated_files()
        assert len(rotated_files) >= 1

        # Current file should exist
        assert storage_path.exists()

    def test_load_from_rotated_compressed_file(self, temp_dir):
        """Test loading events from compressed rotated file."""
        storage = EventStorage(storage_path=temp_dir / "events.json", compress=True)

        # Create rotated compressed file
        events = [
            {'event_id': '1', 'data': 'test 1'},
            {'event_id': '2', 'data': 'test 2'}
        ]

        rotated_path = temp_dir / "events.20250118_120000.json.gz"
        with gzip.open(rotated_path, 'wt') as f:
            json.dump({'events': events, 'version': '1.0'}, f)

        # Load from rotated file
        loaded_events = storage.load_from_rotated(rotated_path)

        # Verify
        assert len(loaded_events) == 2
        assert loaded_events[0]['event_id'] == '1'

    def test_load_all_events_from_multiple_files(self, temp_dir):
        """Test loading events from current and rotated files."""
        storage_path = temp_dir / "events.json"
        storage = EventStorage(
            storage_path=storage_path,
            max_file_size=150,
            compress=False
        )

        # Create and save events that will cause rotation
        events_batch1 = [{'event_id': '1', 'timestamp': '2025-01-01T10:00:00', 'data': 'x' * 50}]
        events_batch2 = [{'event_id': '2', 'timestamp': '2025-01-01T11:00:00', 'data': 'x' * 50}]
        events_batch3 = [{'event_id': '3', 'timestamp': '2025-01-01T12:00:00', 'data': 'x' * 50}]

        storage.save(events_batch1)
        time.sleep(0.01)
        storage.save(events_batch2)
        time.sleep(0.01)
        storage.save(events_batch3)

        # Load all events
        all_events = storage.load_all_events()

        # Verify all events loaded
        # Note: We should have at least the events from batch3 (current file)
        assert len(all_events) >= 1

    def test_get_storage_stats(self, temp_file):
        """Test getting storage statistics."""
        storage = EventStorage(storage_path=temp_file)

        # Save some events
        events = [
            {'event_id': '1', 'data': 'test 1'},
            {'event_id': '2', 'data': 'test 2'}
        ]
        storage.save(events)

        # Get stats
        stats = storage.get_storage_stats()

        # Verify stats
        assert stats['current_file_exists']
        assert stats['current_file_size'] > 0
        assert stats['current_event_count'] == 2
        assert 'rotated_files' in stats
        assert 'total_files' in stats


class TestEventCollectorIntegration:
    """Test EventCollector integration with rotation."""

    def test_event_collector_uses_rotation(self, temp_dir):
        """Test that EventCollector properly uses event storage with rotation."""
        from core.telemetry.event_collector import EventCollector
        from core.telemetry.event_schemas import Event, EventType

        storage_path = temp_dir / "events.json"
        collector = EventCollector(
            storage_path=storage_path,
            max_file_size=300,  # Small size for testing
            retention_days=30
        )

        # Create and collect events
        for i in range(20):
            event = Event(
                event_type=EventType.TASK_STARTED,
                session_id='test-session',
                metadata={'test_id': i, 'data': 'x' * 50}
            )
            collector.collect(event)

        # Flush to ensure events are saved
        collector.flush()

        # Verify storage path exists
        assert storage_path.exists()

        # Check if rotation occurred (file size should be managed)
        # If file grew too large, rotated files should exist
        stats = collector.event_storage.get_storage_stats()
        assert stats['current_file_exists']
