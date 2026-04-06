"""
WebSocket modules for real-time updates.

Contains WebSocket endpoints for:
- Live task updates
- Real-time telemetry events
- Session status changes
"""

from . import live_updates

__all__ = ["live_updates"]
