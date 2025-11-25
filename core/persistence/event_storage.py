"""
Event storage with automatic rotation and compression

Provides persistent event storage with:
- Automatic file rotation when size exceeds threshold
- Gzip compression of old files
- Cleanup of files older than retention period
"""

import json
import gzip
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from core.persistence.rotation import FileRotator

logger = logging.getLogger(__name__)


class EventStorage:
    """Manages event storage with rotation and compression."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_file_size: int = 1_000_000,  # 1MB
        retention_days: int = 30,
        compress: bool = True,
    ):
        """
        Initialize event storage.

        Args:
            storage_path: Path to events file (default: .buildrunner/events.json)
            max_file_size: Maximum file size before rotation (bytes)
            retention_days: Days to retain old files
            compress: Whether to compress rotated files
        """
        self.storage_path = storage_path or Path.cwd() / ".buildrunner" / "events.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.rotator = FileRotator(
            max_size_bytes=max_file_size,
            retention_days=retention_days,
            compress=compress,
        )

    def save(self, events: List[Dict[str, Any]]):
        """
        Save events to storage, rotating if necessary.

        Args:
            events: List of event dictionaries to save
        """
        try:
            # Check if rotation is needed before saving
            if self.rotator.should_rotate(self.storage_path):
                self._rotate()

            # Save events
            data = {
                "events": events,
                "version": "1.0",
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(events)} events to {self.storage_path}")

        except Exception as e:
            logger.error(f"Failed to save events: {e}")
            raise

    def load(self) -> List[Dict[str, Any]]:
        """
        Load events from storage.

        Returns:
            List of event dictionaries
        """
        if not self.storage_path.exists():
            return []

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            events = data.get("events", [])
            logger.debug(f"Loaded {len(events)} events from {self.storage_path}")
            return events

        except Exception as e:
            logger.error(f"Failed to load events: {e}")
            return []

    def _rotate(self):
        """Rotate the current events file."""
        rotated_path = self.rotator.rotate_file(self.storage_path)

        if rotated_path:
            logger.info(f"Rotated events file to {rotated_path}")

            # Cleanup old files
            self.rotator.cleanup_old_files(
                self.storage_path.parent,
                pattern=f"{self.storage_path.stem}.*{self.storage_path.suffix}*",
            )

    def get_rotated_files(self) -> List[Path]:
        """
        Get list of rotated event files.

        Returns:
            List of rotated file paths (newest first)
        """
        return self.rotator.get_rotated_files(self.storage_path)

    def load_from_rotated(self, rotated_path: Path) -> List[Dict[str, Any]]:
        """
        Load events from a rotated (possibly compressed) file.

        Args:
            rotated_path: Path to rotated file

        Returns:
            List of event dictionaries
        """
        try:
            # Check if file is compressed
            if rotated_path.suffix == ".gz":
                with gzip.open(rotated_path, "rt") as f:
                    data = json.load(f)
            else:
                with open(rotated_path, "r") as f:
                    data = json.load(f)

            events = data.get("events", [])
            logger.debug(f"Loaded {len(events)} events from rotated file {rotated_path}")
            return events

        except Exception as e:
            logger.error(f"Failed to load events from {rotated_path}: {e}")
            return []

    def load_all_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load events from current file and all rotated files.

        Args:
            limit: Maximum number of events to load (most recent)

        Returns:
            List of event dictionaries, sorted by timestamp (newest first)
        """
        all_events = []

        # Load current events
        current_events = self.load()
        all_events.extend(current_events)

        # Load rotated events
        for rotated_path in self.get_rotated_files():
            rotated_events = self.load_from_rotated(rotated_path)
            all_events.extend(rotated_events)

        # Sort by timestamp (newest first)
        # Assuming events have 'timestamp' field
        try:
            all_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        except Exception:
            # If sorting fails, just return unsorted
            pass

        # Apply limit if specified
        if limit:
            all_events = all_events[:limit]

        logger.info(f"Loaded {len(all_events)} total events from all files")
        return all_events

    def cleanup_old_files(self):
        """Remove rotated files older than retention period."""
        self.rotator.cleanup_old_files(
            self.storage_path.parent,
            pattern=f"{self.storage_path.stem}.*{self.storage_path.suffix}*",
        )

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about event storage.

        Returns:
            Dictionary with storage statistics
        """
        stats = {
            "current_file": str(self.storage_path),
            "current_file_exists": self.storage_path.exists(),
            "current_file_size": 0,
            "current_event_count": 0,
            "rotated_files": [],
            "total_rotated_size": 0,
        }

        # Current file stats
        if self.storage_path.exists():
            stats["current_file_size"] = self.storage_path.stat().st_size
            stats["current_event_count"] = len(self.load())

        # Rotated files stats
        rotated_files = self.get_rotated_files()
        total_rotated_size = 0

        for rotated_path in rotated_files:
            file_size = rotated_path.stat().st_size
            total_rotated_size += file_size

            stats["rotated_files"].append(
                {
                    "path": str(rotated_path),
                    "size": file_size,
                    "compressed": rotated_path.suffix == ".gz",
                }
            )

        stats["total_rotated_size"] = total_rotated_size
        stats["total_files"] = (
            1 + len(rotated_files) if stats["current_file_exists"] else len(rotated_files)
        )

        return stats
