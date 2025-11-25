"""
Event Collector - Collects and stores telemetry events

Features:
- Event collection and buffering
- Event filtering by type, severity, etc.
- Persistent storage with rotation and compression
- Event querying and retrieval
- Automatic cleanup of old events
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional
import json
import uuid
import logging

from .event_schemas import Event, EventType, TaskEvent, BuildEvent, ErrorEvent, PerformanceEvent
from core.persistence.event_storage import EventStorage
from core.persistence.database import Database

logger = logging.getLogger(__name__)


@dataclass
class EventFilter:
    """Filter for querying events."""

    event_types: Optional[List[EventType]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    min_severity: Optional[str] = None


class EventCollector:
    """Collects and stores telemetry events."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        db_path: Optional[Path] = None,
        buffer_size: int = 100,
        auto_flush: bool = True,
        max_file_size: int = 1_000_000,  # 1MB
        retention_days: int = 30,
        use_sqlite: bool = True,
    ):
        """
        Initialize event collector.

        Args:
            storage_path: Path to store events (JSON file, legacy)
            db_path: Path to SQLite database (default: .buildrunner/telemetry.db)
            buffer_size: Number of events to buffer before flushing
            auto_flush: Automatically flush buffer when full
            max_file_size: Maximum file size before rotation (bytes)
            retention_days: Days to retain old rotated files
            use_sqlite: Use SQLite for persistence (default: True)
        """
        self.storage_path = storage_path or Path.cwd() / ".buildrunner" / "events.json"
        self.db_path = db_path or Path.cwd() / ".buildrunner" / "telemetry.db"
        self.buffer_size = buffer_size
        self.auto_flush = auto_flush
        self.use_sqlite = use_sqlite

        # Initialize SQLite database if enabled
        if self.use_sqlite:
            self.db = Database(self.db_path)
            self._init_database()
        else:
            self.db = None

        # Initialize event storage with rotation (legacy/backup)
        self.event_storage = EventStorage(
            storage_path=self.storage_path,
            max_file_size=max_file_size,
            retention_days=retention_days,
            compress=True,
        )

        self.events: List[Event] = []
        self.buffer: List[Event] = []
        self.listeners: List[Callable[[Event], None]] = []

        # Load existing events
        self._load()

    def _init_database(self):
        """Initialize SQLite database schema."""
        if not self.db:
            return

        # Create events table
        schema = """
        CREATE TABLE IF NOT EXISTS events (
            -- Primary Key
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Core Event Fields
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            session_id TEXT,

            -- Task-related fields (for TaskEvent)
            task_id TEXT,
            task_type TEXT,
            task_description TEXT,
            complexity_level TEXT,
            model_used TEXT,
            file_count INTEGER,
            line_count INTEGER,

            -- Build-related fields (for BuildEvent)
            build_id TEXT,
            build_phase TEXT,
            total_tasks INTEGER,
            completed_tasks INTEGER,
            failed_tasks INTEGER,

            -- Error-related fields (for ErrorEvent)
            error_type TEXT,
            error_message TEXT,
            stack_trace TEXT,
            component TEXT,
            severity TEXT,

            -- Performance metrics
            duration_ms REAL,
            tokens_used INTEGER,
            cost_usd REAL,
            total_cost_usd REAL,
            cpu_percent REAL,
            memory_mb REAL,

            -- Status flags
            success BOOLEAN DEFAULT 1,

            -- Flexible metadata (JSON)
            metadata TEXT,

            -- Timestamps for tracking
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Indexes for fast queries
        CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_task_id ON events(task_id) WHERE task_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_session_id ON events(session_id) WHERE session_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_build_id ON events(build_id) WHERE build_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_type_timestamp ON events(event_type, timestamp DESC);

        -- Statistics view
        CREATE VIEW IF NOT EXISTS event_statistics AS
        SELECT
            event_type,
            COUNT(*) as count,
            AVG(duration_ms) as avg_duration_ms,
            SUM(cost_usd) as total_cost_usd,
            SUM(tokens_used) as total_tokens,
            MIN(timestamp) as first_occurrence,
            MAX(timestamp) as last_occurrence
        FROM events
        GROUP BY event_type;
        """

        try:
            self.db.run_migration(schema)
            logger.info(f"SQLite telemetry database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def collect(self, event: Event) -> str:
        """
        Collect an event and persist to SQLite.

        Args:
            event: Event to collect

        Returns:
            Event ID
        """
        # Generate event ID if not set
        if not event.event_id:
            event.event_id = str(uuid.uuid4())

        # Persist to SQLite immediately (non-blocking)
        if self.use_sqlite and self.db:
            try:
                self._persist_event(event)
            except Exception as e:
                logger.error(f"Failed to persist event to SQLite: {e}")
                # Don't fail collection on DB errors

        # Add to buffer for in-memory queries
        self.buffer.append(event)

        # Notify listeners
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as e:
                logger.warning(f"Event listener failed: {e}")

        # Auto-flush if buffer is full
        if self.auto_flush and len(self.buffer) >= self.buffer_size:
            self.flush()

        return event.event_id

    def flush(self):
        """Flush buffered events to storage."""
        if not self.buffer:
            return

        # Add buffer to events
        self.events.extend(self.buffer)
        self.buffer.clear()

        # Save to disk
        self._save()

    def query(
        self,
        filter: Optional[EventFilter] = None,
        limit: Optional[int] = None,
    ) -> List[Event]:
        """
        Query events with optional filtering.

        Args:
            filter: Event filter
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        # Query from SQLite if enabled
        if self.use_sqlite and self.db:
            return self._query_sqlite(filter, limit)

        # Fallback to in-memory query
        # Flush buffer to include recent events
        if self.buffer:
            self.flush()

        # Apply filter
        results = self.events

        if filter:
            if filter.event_types:
                results = [e for e in results if e.event_type in filter.event_types]

            if filter.start_time:
                results = [e for e in results if e.timestamp >= filter.start_time]

            if filter.end_time:
                results = [e for e in results if e.timestamp <= filter.end_time]

            if filter.session_id:
                results = [e for e in results if e.session_id == filter.session_id]

            if filter.task_id:
                results = [
                    e for e in results if hasattr(e, "task_id") and e.task_id == filter.task_id
                ]

        # Apply limit
        if limit:
            results = results[-limit:]  # Most recent

        return results

    def get_by_id(self, event_id: str) -> Optional[Event]:
        """
        Get event by ID.

        Args:
            event_id: Event ID

        Returns:
            Event or None if not found
        """
        # Check buffer first
        for event in self.buffer:
            if event.event_id == event_id:
                return event

        # Check stored events
        for event in self.events:
            if event.event_id == event_id:
                return event

        return None

    def get_recent(self, count: int = 10) -> List[Event]:
        """
        Get most recent events.

        Args:
            count: Number of events to return

        Returns:
            List of recent events
        """
        # Use SQLite if available
        if self.use_sqlite and self.db:
            return self._query_sqlite(filter=None, limit=count)

        # Fallback to in-memory
        # Combine buffer and events
        all_events = self.events + self.buffer

        # Sort by timestamp (most recent first)
        sorted_events = sorted(all_events, key=lambda e: e.timestamp, reverse=True)

        return sorted_events[:count]

    def get_count(
        self,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """
        Get count of events.

        Args:
            event_type: Filter by event type
            since: Filter by time (events since this time)

        Returns:
            Count of matching events
        """
        events = self.events + self.buffer

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if since:
            events = [e for e in events if e.timestamp >= since]

        return len(events)

    def clear_old_events(self, days: int = 30):
        """
        Clear events older than specified days.

        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now() - timedelta(days=days)
        self.events = [e for e in self.events if e.timestamp >= cutoff]
        self._save()

    def add_listener(self, listener: Callable[[Event], None]):
        """
        Add event listener.

        Args:
            listener: Function to call when event is collected
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Event], None]):
        """
        Remove event listener.

        Args:
            listener: Listener to remove
        """
        if listener in self.listeners:
            self.listeners.remove(listener)

    def _query_sqlite(
        self,
        filter: Optional[EventFilter] = None,
        limit: Optional[int] = None,
    ) -> List[Event]:
        """
        Query events from SQLite database.

        Args:
            filter: Event filter
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        # Build SQL query
        sql = "SELECT * FROM events WHERE 1=1"
        params = []

        if filter:
            if filter.event_types:
                placeholders = ",".join("?" * len(filter.event_types))
                sql += f" AND event_type IN ({placeholders})"
                params.extend([et.value for et in filter.event_types])

            if filter.start_time:
                sql += " AND timestamp >= ?"
                params.append(filter.start_time.isoformat())

            if filter.end_time:
                sql += " AND timestamp <= ?"
                params.append(filter.end_time.isoformat())

            if filter.session_id:
                sql += " AND session_id = ?"
                params.append(filter.session_id)

            if filter.task_id:
                sql += " AND task_id = ?"
                params.append(filter.task_id)

        # Order by timestamp descending (most recent first)
        sql += " ORDER BY timestamp DESC"

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        # Execute query
        try:
            rows = self.db.query(sql, tuple(params))

            # Convert rows to Event objects
            events = []
            for row in rows:
                # Reconstruct event from row
                event_type = EventType(row["event_type"])
                timestamp = datetime.fromisoformat(row["timestamp"])

                # Determine event class based on type
                if "TASK_" in row["event_type"]:
                    event = TaskEvent(
                        event_type=event_type,
                        timestamp=timestamp,
                        event_id=row["event_id"],
                        session_id=row.get("session_id", ""),
                        task_id=row.get("task_id", ""),
                        task_type=row.get("task_type", ""),
                        task_description=row.get("task_description", ""),
                        complexity_level=row.get("complexity_level", ""),
                        model_used=row.get("model_used", ""),
                        file_count=row.get("file_count", 0) or 0,
                        line_count=row.get("line_count", 0) or 0,
                        duration_ms=row.get("duration_ms", 0.0) or 0.0,
                        tokens_used=row.get("tokens_used", 0) or 0,
                        cost_usd=row.get("cost_usd", 0.0) or 0.0,
                        success=bool(row.get("success", True)),
                        error_message=row.get("error_message", ""),
                        metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
                    )
                elif "BUILD_" in row["event_type"]:
                    event = BuildEvent(
                        event_type=event_type,
                        timestamp=timestamp,
                        event_id=row["event_id"],
                        session_id=row.get("session_id", ""),
                        build_id=row.get("build_id", ""),
                        build_phase=row.get("build_phase", ""),
                        total_tasks=row.get("total_tasks", 0) or 0,
                        completed_tasks=row.get("completed_tasks", 0) or 0,
                        failed_tasks=row.get("failed_tasks", 0) or 0,
                        duration_ms=row.get("duration_ms", 0.0) or 0.0,
                        total_cost_usd=row.get("total_cost_usd", 0.0) or 0.0,
                        success=bool(row.get("success", True)),
                        error_message=row.get("error_message", ""),
                        metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
                    )
                elif "ERROR_" in row["event_type"] or "EXCEPTION_" in row["event_type"]:
                    event = ErrorEvent(
                        event_type=event_type,
                        timestamp=timestamp,
                        event_id=row["event_id"],
                        session_id=row.get("session_id", ""),
                        error_type=row.get("error_type", ""),
                        error_message=row.get("error_message", ""),
                        stack_trace=row.get("stack_trace", ""),
                        task_id=row.get("task_id", ""),
                        component=row.get("component", ""),
                        severity=row.get("severity", "error"),
                        metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
                    )
                elif "PERFORMANCE_" in row["event_type"]:
                    event = PerformanceEvent(
                        event_type=event_type,
                        timestamp=timestamp,
                        event_id=row["event_id"],
                        session_id=row.get("session_id", ""),
                        metric_name=row.get("component", ""),
                        metric_value=row.get("duration_ms", 0.0) or 0.0,
                        metric_unit="ms",
                        component=row.get("component", ""),
                        operation="",
                        cpu_percent=row.get("cpu_percent", 0.0) or 0.0,
                        memory_mb=row.get("memory_mb", 0.0) or 0.0,
                        metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
                    )
                else:
                    # Default to base Event
                    event = Event(
                        event_type=event_type,
                        timestamp=timestamp,
                        event_id=row["event_id"],
                        session_id=row.get("session_id", ""),
                        metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
                    )

                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to query SQLite: {e}")
            return []

    def _persist_event(self, event: Event):
        """
        Persist single event to SQLite database.

        Args:
            event: Event to persist
        """
        if not self.db:
            return

        # Build event data dictionary with all possible fields
        data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "session_id": event.session_id or None,
            "metadata": json.dumps(event.metadata) if event.metadata else None,
        }

        # Add TaskEvent-specific fields
        if isinstance(event, TaskEvent):
            data.update(
                {
                    "task_id": event.task_id or None,
                    "task_type": event.task_type or None,
                    "task_description": event.task_description or None,
                    "complexity_level": event.complexity_level or None,
                    "model_used": event.model_used or None,
                    "file_count": event.file_count if event.file_count else None,
                    "line_count": event.line_count if event.line_count else None,
                    "duration_ms": event.duration_ms if event.duration_ms else None,
                    "tokens_used": event.tokens_used if event.tokens_used else None,
                    "cost_usd": event.cost_usd if event.cost_usd else None,
                    "success": event.success,
                    "error_message": event.error_message or None,
                }
            )

        # Add BuildEvent-specific fields
        elif isinstance(event, BuildEvent):
            data.update(
                {
                    "build_id": event.build_id or None,
                    "build_phase": event.build_phase or None,
                    "total_tasks": event.total_tasks if event.total_tasks else None,
                    "completed_tasks": event.completed_tasks if event.completed_tasks else None,
                    "failed_tasks": event.failed_tasks if event.failed_tasks else None,
                    "duration_ms": event.duration_ms if event.duration_ms else None,
                    "total_cost_usd": event.total_cost_usd if event.total_cost_usd else None,
                    "success": event.success,
                    "error_message": event.error_message or None,
                }
            )

        # Add ErrorEvent-specific fields
        elif isinstance(event, ErrorEvent):
            data.update(
                {
                    "error_type": event.error_type or None,
                    "error_message": event.error_message or None,
                    "stack_trace": event.stack_trace or None,
                    "task_id": event.task_id or None,
                    "component": event.component or None,
                    "severity": event.severity or None,
                }
            )

        # Add PerformanceEvent-specific fields
        elif isinstance(event, PerformanceEvent):
            data.update(
                {
                    "duration_ms": event.metric_value if event.metric_unit == "ms" else None,
                    "component": event.component or None,
                    "cpu_percent": event.cpu_percent if event.cpu_percent else None,
                    "memory_mb": event.memory_mb if event.memory_mb else None,
                }
            )

        # Insert into database
        try:
            self.db.insert("events", data)
        except Exception as e:
            logger.error(f"Failed to insert event into database: {e}")
            raise

    def _save(self):
        """Save events to disk with automatic rotation."""
        try:
            # Convert events to dict
            event_dicts = [e.to_dict() for e in self.events]

            # Use EventStorage which handles rotation automatically
            self.event_storage.save(event_dicts)

        except Exception as e:
            logger.error(f"Failed to save events: {e}")

    def _load(self):
        """Load events from disk."""
        try:
            # Load events using EventStorage
            event_dicts = self.event_storage.load()

            # Convert dicts to Event objects
            # Note: This loads as base Event class - subclasses not preserved
            self.events = [Event.from_dict(e) for e in event_dicts]

            logger.info(f"Loaded {len(self.events)} events from storage")

        except Exception as e:
            logger.error(f"Failed to load events: {e}")
            self.events = []

    def export_csv(self, output_path: Path, filter: Optional[EventFilter] = None):
        """
        Export events to CSV.

        Args:
            output_path: Path to output CSV file
            filter: Optional filter for events
        """
        import csv

        events = self.query(filter=filter)

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "Event ID",
                    "Event Type",
                    "Timestamp",
                    "Session ID",
                    "Metadata",
                ]
            )

            # Data
            for event in events:
                writer.writerow(
                    [
                        event.event_id,
                        event.event_type.value,
                        event.timestamp.isoformat(),
                        event.session_id,
                        str(event.metadata),
                    ]
                )

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about collected events.

        Returns:
            Statistics dictionary
        """
        # Use SQLite statistics view if available
        if self.use_sqlite and self.db:
            try:
                # Get statistics from view
                stats_rows = self.db.query("SELECT * FROM event_statistics")

                # Get total count
                total_result = self.db.query_one("SELECT COUNT(*) as count FROM events")
                total = total_result["count"] if total_result else 0

                # Get time range
                time_result = self.db.query_one(
                    "SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM events"
                )

                by_type = {}
                for row in stats_rows:
                    by_type[row["event_type"]] = row["count"]

                return {
                    "total_events": total,
                    "buffered_events": len(self.buffer),
                    "stored_events": total,
                    "by_type": by_type,
                    "events_by_type": by_type,  # Backward compatibility
                    "oldest_event": time_result["oldest"] if time_result else None,
                    "newest_event": time_result["newest"] if time_result else None,
                    "listeners": len(self.listeners),
                }
            except Exception as e:
                logger.error(f"Failed to get statistics from SQLite: {e}")
                # Fall through to in-memory version

        # Fallback to in-memory statistics
        all_events = self.events + self.buffer

        if not all_events:
            return {
                "total_events": 0,
                "events_by_type": {},
                "oldest_event": None,
                "newest_event": None,
            }

        # Count by type
        by_type = {}
        for event in all_events:
            by_type[event.event_type.value] = by_type.get(event.event_type.value, 0) + 1

        # Find oldest and newest
        sorted_events = sorted(all_events, key=lambda e: e.timestamp)
        oldest = sorted_events[0].timestamp
        newest = sorted_events[-1].timestamp

        return {
            "total_events": len(all_events),
            "buffered_events": len(self.buffer),
            "stored_events": len(self.events),
            "events_by_type": by_type,
            "by_type": by_type,
            "oldest_event": oldest.isoformat(),
            "newest_event": newest.isoformat(),
            "listeners": len(self.listeners),
        }
