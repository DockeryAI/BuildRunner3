"""
Sentry Error Tracking Integration for BuildRunner 3.2

Provides:
- Automatic error capture and reporting
- Phase and task context tagging
- Integration with telemetry system
- Performance monitoring
- Release tracking
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from functools import wraps
import traceback
from datetime import datetime

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from core.phase_manager import BuildPhase


logger = logging.getLogger(__name__)


class ErrorTracker:
    """
    Sentry-based error tracking for BuildRunner.

    Features:
    - Auto-capture exceptions with context
    - Tag errors with phase, task, agent info
    - Performance transaction tracking
    - Integration with telemetry system
    - Custom error filtering
    """

    def __init__(
        self,
        project_root: Path,
        dsn: Optional[str] = None,
        environment: str = "development",
        release: Optional[str] = None,
        sample_rate: float = 1.0,
        traces_sample_rate: float = 0.1,
        enabled: bool = True,
    ):
        """
        Initialize error tracker.

        Args:
            project_root: Project root directory
            dsn: Sentry DSN (from environment if not provided)
            environment: Environment name (dev/staging/prod)
            release: Release version
            sample_rate: Error sampling rate (0.0-1.0)
            traces_sample_rate: Performance trace sampling rate
            enabled: Enable/disable tracking
        """
        self.project_root = Path(project_root)
        self.environment = environment
        self.release = release or self._get_release_version()
        self.enabled = enabled and SENTRY_AVAILABLE
        self.current_phase: Optional[BuildPhase] = None
        self.current_task: Optional[str] = None
        self.current_agent: Optional[str] = None

        # Get DSN from environment or parameter
        self.dsn = dsn or os.environ.get("SENTRY_DSN")

        if self.enabled and self.dsn:
            self._initialize_sentry(sample_rate, traces_sample_rate)
        elif self.enabled and not self.dsn:
            logger.warning(
                "Sentry enabled but no DSN provided. Set SENTRY_DSN environment variable."
            )
            self.enabled = False
        elif not SENTRY_AVAILABLE:
            logger.info("Sentry SDK not available. Install with: pip install sentry-sdk")

    def _get_release_version(self) -> str:
        """Get release version from project"""
        try:
            # Try to read from pyproject.toml
            pyproject = self.project_root / "pyproject.toml"
            if pyproject.exists():
                import tomli

                with open(pyproject, "rb") as f:
                    data = tomli.load(f)
                    version = data.get("project", {}).get("version", "unknown")
                    return f"buildrunner@{version}"
        except Exception:
            pass

        return "buildrunner@unknown"

    def _initialize_sentry(self, sample_rate: float, traces_sample_rate: float):
        """Initialize Sentry SDK"""
        try:
            # Configure logging integration
            logging_integration = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR,  # Send errors as events
            )

            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                release=self.release,
                sample_rate=sample_rate,
                traces_sample_rate=traces_sample_rate,
                integrations=[logging_integration],
                before_send=self._before_send,
                before_breadcrumb=self._before_breadcrumb,
            )

            logger.info(f"Sentry initialized for {self.environment} environment")

        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            self.enabled = False

    def _before_send(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Filter/modify events before sending to Sentry.

        Args:
            event: Sentry event dict
            hint: Additional context

        Returns:
            Modified event or None to drop
        """
        # Add custom tags
        if "tags" not in event:
            event["tags"] = {}

        if self.current_phase:
            event["tags"]["phase"] = self.current_phase.value

        if self.current_task:
            event["tags"]["task"] = self.current_task

        if self.current_agent:
            event["tags"]["agent"] = self.current_agent

        # Add build context
        event["tags"]["build_type"] = "buildrunner"

        # Filter out sensitive data from contexts
        if "contexts" in event:
            for context_name, context_data in event["contexts"].items():
                if isinstance(context_data, dict):
                    # Remove any keys that might contain secrets
                    sensitive_keys = {"password", "token", "secret", "key", "api_key"}
                    for key in list(context_data.keys()):
                        if any(sensitive in key.lower() for sensitive in sensitive_keys):
                            context_data[key] = "[REDACTED]"

        return event

    def _before_breadcrumb(
        self, crumb: Dict[str, Any], hint: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Filter/modify breadcrumbs before adding.

        Args:
            crumb: Breadcrumb dict
            hint: Additional context

        Returns:
            Modified breadcrumb or None to drop
        """
        # Add phase context to breadcrumbs
        if self.current_phase:
            if "data" not in crumb:
                crumb["data"] = {}
            crumb["data"]["phase"] = self.current_phase.value

        return crumb

    def set_context(
        self,
        phase: Optional[BuildPhase] = None,
        task: Optional[str] = None,
        agent: Optional[str] = None,
    ):
        """
        Set current execution context for error tagging.

        Args:
            phase: Current build phase
            task: Current task ID
            agent: Current agent name
        """
        if phase is not None:
            self.current_phase = phase

        if task is not None:
            self.current_task = task

        if agent is not None:
            self.current_agent = agent

        # Update Sentry context
        if self.enabled:
            with sentry_sdk.configure_scope() as scope:
                if self.current_phase:
                    scope.set_tag("phase", self.current_phase.value)
                if self.current_task:
                    scope.set_tag("task", self.current_task)
                if self.current_agent:
                    scope.set_tag("agent", self.current_agent)

    def capture_exception(
        self, error: Exception, extra: Optional[Dict[str, Any]] = None, level: str = "error"
    ) -> Optional[str]:
        """
        Capture an exception to Sentry.

        Args:
            error: Exception to capture
            extra: Additional context data
            level: Error level (error/warning/info)

        Returns:
            Event ID if sent, None otherwise
        """
        if not self.enabled:
            return None

        try:
            with sentry_sdk.configure_scope() as scope:
                scope.level = level

                # Add extra context
                if extra:
                    for key, value in extra.items():
                        scope.set_extra(key, value)

                # Add traceback as extra
                scope.set_extra("traceback", traceback.format_exc())

                # Send to Sentry
                event_id = sentry_sdk.capture_exception(error)
                logger.debug(f"Captured exception to Sentry: {event_id}")
                return event_id

        except Exception as e:
            logger.error(f"Failed to capture exception to Sentry: {e}")
            return None

    def capture_message(
        self, message: str, level: str = "info", extra: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Capture a message to Sentry.

        Args:
            message: Message to capture
            level: Message level
            extra: Additional context

        Returns:
            Event ID if sent
        """
        if not self.enabled:
            return None

        try:
            with sentry_sdk.configure_scope() as scope:
                scope.level = level

                if extra:
                    for key, value in extra.items():
                        scope.set_extra(key, value)

                event_id = sentry_sdk.capture_message(message)
                return event_id

        except Exception as e:
            logger.error(f"Failed to capture message to Sentry: {e}")
            return None

    def start_transaction(self, name: str, op: str = "task") -> Any:
        """
        Start a performance transaction.

        Args:
            name: Transaction name
            op: Operation type

        Returns:
            Transaction object
        """
        if not self.enabled:
            return None

        try:
            transaction = sentry_sdk.start_transaction(name=name, op=op)

            # Add context
            if self.current_phase:
                transaction.set_tag("phase", self.current_phase.value)
            if self.current_task:
                transaction.set_tag("task", self.current_task)

            return transaction

        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            return None

    def add_breadcrumb(
        self,
        message: str,
        category: str = "default",
        level: str = "info",
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        Add a breadcrumb for debugging context.

        Args:
            message: Breadcrumb message
            category: Breadcrumb category
            level: Breadcrumb level
            data: Additional data
        """
        if not self.enabled:
            return

        try:
            sentry_sdk.add_breadcrumb(
                message=message, category=category, level=level, data=data or {}
            )
        except Exception as e:
            logger.error(f"Failed to add breadcrumb: {e}")

    def flush(self, timeout: int = 2):
        """
        Flush pending events to Sentry.

        Args:
            timeout: Timeout in seconds
        """
        if self.enabled:
            try:
                sentry_sdk.flush(timeout=timeout)
            except Exception as e:
                logger.error(f"Failed to flush Sentry: {e}")


def track_errors(phase: Optional[BuildPhase] = None, task: Optional[str] = None):
    """
    Decorator to automatically capture exceptions to Sentry.

    Args:
        phase: Build phase for context
        task: Task ID for context

    Example:
        @track_errors(phase=BuildPhase.CODE_GENERATION, task="task-123")
        def generate_code():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get error tracker from kwargs or create minimal one
            error_tracker = kwargs.pop("error_tracker", None)

            try:
                # Set context if tracker available
                if error_tracker and phase:
                    error_tracker.set_context(phase=phase, task=task)

                # Execute function
                return func(*args, **kwargs)

            except Exception as e:
                # Capture to Sentry
                if error_tracker:
                    error_tracker.capture_exception(
                        e,
                        extra={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                    )

                # Re-raise
                raise

        return wrapper

    return decorator


# Global instance for convenience
_global_tracker: Optional[ErrorTracker] = None


def get_global_tracker() -> Optional[ErrorTracker]:
    """Get global error tracker instance"""
    return _global_tracker


def init_global_tracker(project_root: Path, **kwargs) -> ErrorTracker:
    """
    Initialize global error tracker.

    Args:
        project_root: Project root directory
        **kwargs: Additional ErrorTracker arguments

    Returns:
        Initialized ErrorTracker instance
    """
    global _global_tracker
    _global_tracker = ErrorTracker(project_root, **kwargs)
    return _global_tracker
