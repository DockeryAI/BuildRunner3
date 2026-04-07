"""
Operational Transforms for PRD Concurrent Editing

Implements basic OT for resolving conflicts when multiple users
edit the PRD simultaneously.

Currently implements:
- Last-write-wins with conflict detection
- Merge strategies for non-conflicting changes
- Conflict notification

Future enhancements:
- Full OT algorithm (Insert/Delete/Retain operations)
- Real-time collaborative editing
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Operation:
    """Single operation in an OT sequence"""

    op_type: str  # "insert", "delete", "update", "no-op"
    position: Optional[int] = None
    data: Optional[Any] = None
    author: str = "unknown"
    timestamp: str = ""


@dataclass
class Conflict:
    """Detected conflict between operations"""

    op1: Operation
    op2: Operation
    conflict_type: str  # "same_field", "dependent", "ordering"
    resolution: str  # "accept_op1", "accept_op2", "merge", "manual"


class OperationalTransform:
    """
    Operational Transform engine for PRD changes

    Handles concurrent edits and conflict resolution
    """

    def __init__(self):
        self.pending_operations: List[Operation] = []

    def transform(
        self, local_ops: List[Operation], remote_ops: List[Operation]
    ) -> Tuple[List[Operation], List[Conflict]]:
        """
        Transform local operations against remote operations

        Args:
            local_ops: Operations performed locally
            remote_ops: Operations received from server/other clients

        Returns:
            Tuple of (transformed_ops, conflicts)
        """
        conflicts = []
        transformed = []

        for local_op in local_ops:
            transformed_op = local_op
            has_conflict = False

            for remote_op in remote_ops:
                conflict = self._detect_conflict(local_op, remote_op)

                if conflict:
                    conflicts.append(conflict)
                    has_conflict = True

                    # Apply resolution strategy
                    if conflict.resolution == "accept_op1":
                        # Keep local operation
                        pass
                    elif conflict.resolution == "accept_op2":
                        # Discard local, use remote
                        transformed_op = None
                        break
                    elif conflict.resolution == "merge":
                        # Try to merge
                        transformed_op = self._merge_operations(local_op, remote_op)

            if transformed_op:
                transformed.append(transformed_op)

        return transformed, conflicts

    def _detect_conflict(self, op1: Operation, op2: Operation) -> Optional[Conflict]:
        """Detect if two operations conflict"""

        # Same feature, same field -> conflict
        if op1.op_type == "update" and op2.op_type == "update":
            if self._operations_target_same_field(op1, op2):
                # Timestamp-based resolution (last write wins)
                if op1.timestamp > op2.timestamp:
                    resolution = "accept_op1"
                else:
                    resolution = "accept_op2"

                return Conflict(op1=op1, op2=op2, conflict_type="same_field", resolution=resolution)

        # Delete vs Update -> conflict
        if (op1.op_type == "delete" and op2.op_type == "update") or (
            op1.op_type == "update" and op2.op_type == "delete"
        ):
            # Delete wins
            resolution = "accept_op1" if op1.op_type == "delete" else "accept_op2"

            return Conflict(op1=op1, op2=op2, conflict_type="dependent", resolution=resolution)

        # No conflict
        return None

    def _operations_target_same_field(self, op1: Operation, op2: Operation) -> bool:
        """Check if operations target the same field"""
        if not op1.data or not op2.data:
            return False

        # Compare feature IDs and updated fields
        return op1.data.get("feature_id") == op2.data.get("feature_id") and op1.data.get(
            "field"
        ) == op2.data.get("field")

    def _merge_operations(self, op1: Operation, op2: Operation) -> Operation:
        """Attempt to merge two operations"""
        # Simple merge: combine data if possible
        if op1.data and op2.data:
            merged_data = {**op1.data, **op2.data}

            return Operation(
                op_type=op1.op_type,
                position=op1.position,
                data=merged_data,
                author=f"{op1.author}+{op2.author}",
                timestamp=max(op1.timestamp, op2.timestamp),
            )

        return op1


class ConflictResolver:
    """
    Resolves conflicts detected by OT

    Provides different resolution strategies
    """

    @staticmethod
    def resolve_last_write_wins(conflict: Conflict) -> Operation:
        """Resolve conflict using last-write-wins strategy"""
        if conflict.op1.timestamp > conflict.op2.timestamp:
            return conflict.op1
        return conflict.op2

    @staticmethod
    def resolve_first_write_wins(conflict: Conflict) -> Operation:
        """Resolve conflict using first-write-wins strategy"""
        if conflict.op1.timestamp < conflict.op2.timestamp:
            return conflict.op1
        return conflict.op2

    @staticmethod
    def resolve_merge(conflict: Conflict) -> Optional[Operation]:
        """Attempt to merge conflicting operations"""
        # Only merge if both are updates to different fields
        if conflict.op1.op_type == "update" and conflict.op2.op_type == "update":
            if conflict.op1.data and conflict.op2.data:
                field1 = conflict.op1.data.get("field")
                field2 = conflict.op2.data.get("field")

                if field1 != field2:
                    # Different fields, can merge
                    merged_data = {**conflict.op1.data, **conflict.op2.data}

                    return Operation(
                        op_type="update",
                        data=merged_data,
                        author=f"{conflict.op1.author}+{conflict.op2.author}",
                        timestamp=max(conflict.op1.timestamp, conflict.op2.timestamp),
                    )

        return None

    @staticmethod
    def resolve_by_author_priority(
        conflict: Conflict, author_priorities: Dict[str, int]
    ) -> Operation:
        """Resolve conflict based on author priority"""
        priority1 = author_priorities.get(conflict.op1.author, 0)
        priority2 = author_priorities.get(conflict.op2.author, 0)

        if priority1 > priority2:
            return conflict.op1
        return conflict.op2


# Global OT instance
_ot_engine: Optional[OperationalTransform] = None


def get_ot_engine() -> OperationalTransform:
    """Get or create global OT engine"""
    global _ot_engine

    if _ot_engine is None:
        _ot_engine = OperationalTransform()

    return _ot_engine
