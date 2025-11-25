"""
PRD System Integration - Connects all components

Wires together:
- PRD Controller (event emitter)
- Adaptive Planner (event listener)
- File Watcher (file change detector)
- WebSocket Broadcast (real-time updates)

This module ensures:
1. File changes → PRD Controller → Event emission → WebSocket broadcast
2. API changes → PRD Controller → Event emission → WebSocket broadcast
3. All PRD events → Adaptive Planner → Task regeneration
"""

import logging
from pathlib import Path
from typing import Optional
import asyncio

from core.prd.prd_controller import PRDChangeEvent, get_prd_controller
from core.adaptive_planner import AdaptivePlanner, get_adaptive_planner
from core.prd_file_watcher import PRDFileWatcher, start_prd_watcher

logger = logging.getLogger(__name__)


class PRDSystemIntegration:
    """
    Integrates all PRD system components

    Responsibilities:
    - Start file watcher
    - Connect PRD controller to adaptive planner
    - Connect PRD controller to WebSocket broadcast
    - Ensure all events flow correctly
    """

    def __init__(self, project_root: Path, spec_path: Optional[Path] = None):
        self.project_root = Path(project_root)

        if spec_path is None:
            spec_path = self.project_root / ".buildrunner" / "PROJECT_SPEC.md"

        self.spec_path = Path(spec_path)

        # Core components
        self.controller = get_prd_controller(self.spec_path)
        self.planner = get_adaptive_planner(self.project_root)
        self.file_watcher = None

        # WebSocket broadcast handler (set by API layer)
        self._ws_broadcast_handler = None

        # Track if system is running
        self.running = False

    def start(self, enable_file_watcher: bool = True):
        """Start integrated PRD system"""
        if self.running:
            logger.warning("PRD system already running")
            return

        logger.info("Starting integrated PRD system")

        # Connect PRD controller to WebSocket broadcast
        self.controller.subscribe(self._on_prd_change)

        # Start file watcher
        if enable_file_watcher:
            self.file_watcher = start_prd_watcher(self.spec_path)
            logger.info("File watcher started")

        # Adaptive planner is already subscribed in its __init__

        self.running = True
        logger.info("PRD system integration complete")

    def stop(self):
        """Stop integrated PRD system"""
        if not self.running:
            return

        logger.info("Stopping integrated PRD system")

        # Stop file watcher
        if self.file_watcher:
            from core.prd_file_watcher import stop_prd_watcher

            stop_prd_watcher()

        # Unsubscribe from controller
        self.controller.unsubscribe(self._on_prd_change)

        self.running = False
        logger.info("PRD system stopped")

    def set_websocket_broadcast_handler(self, handler):
        """
        Set WebSocket broadcast handler from API layer

        Handler should be an async function: async def handler(event: PRDChangeEvent)
        """
        self._ws_broadcast_handler = handler
        logger.info("WebSocket broadcast handler registered")

    def _on_prd_change(self, event: PRDChangeEvent):
        """
        Handle PRD change event

        This triggers WebSocket broadcast to all connected clients
        """
        logger.info(f"PRD change detected: {event.event_type.value}")

        # Broadcast to WebSocket clients if handler is set
        if self._ws_broadcast_handler:
            try:
                # Schedule broadcast in event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._ws_broadcast_handler(event))
                else:
                    # If no loop running, create one
                    asyncio.run(self._ws_broadcast_handler(event))
            except Exception as e:
                logger.error(f"Error broadcasting PRD change: {e}")
        else:
            logger.warning("WebSocket broadcast handler not set, skipping broadcast")


# Global integration instance
_integration: Optional[PRDSystemIntegration] = None


def get_prd_integration(
    project_root: Optional[Path] = None, spec_path: Optional[Path] = None
) -> PRDSystemIntegration:
    """Get or create global PRD integration instance"""
    global _integration

    if _integration is None:
        if project_root is None:
            project_root = Path.cwd()

        _integration = PRDSystemIntegration(project_root, spec_path)

    return _integration


def start_prd_system(
    project_root: Optional[Path] = None,
    spec_path: Optional[Path] = None,
    enable_file_watcher: bool = True,
):
    """Start integrated PRD system"""
    integration = get_prd_integration(project_root, spec_path)
    integration.start(enable_file_watcher=enable_file_watcher)
    return integration


def stop_prd_system():
    """Stop integrated PRD system"""
    global _integration

    if _integration:
        _integration.stop()
