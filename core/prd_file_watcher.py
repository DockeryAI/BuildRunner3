"""File watcher for PROJECT_SPEC.md - detects external changes"""
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import logging
import time

from core.prd.prd_controller import get_prd_controller

logger = logging.getLogger(__name__)


class PRDFileHandler(FileSystemEventHandler):
    """Handle PROJECT_SPEC.md file changes"""
    
    def __init__(self, spec_path: Path, debounce_seconds: float = 1.0):
        self.spec_path = Path(spec_path)
        self.debounce_seconds = debounce_seconds
        self._last_modified = 0
        self._ignore_next = False
    
    def on_modified(self, event):
        """Handle file modification"""
        if event.src_path != str(self.spec_path):
            return

        # Debounce rapid changes
        current_time = time.time()
        if current_time - self._last_modified < self.debounce_seconds:
            return

        # Ignore changes caused by internal writes
        if self._ignore_next:
            self._ignore_next = False
            return

        self._last_modified = current_time

        try:
            logger.info(f"Detected external change to {self.spec_path}")
            controller = get_prd_controller()

            # Save old PRD for comparison
            old_prd = controller._prd

            # Reload from file
            controller.load_from_file()
            new_prd = controller._prd

            # Determine what changed and emit event
            from core.prd.prd_controller import PRDChangeEvent, ChangeType
            from datetime import datetime

            # Simple change detection - compare feature lists
            old_feature_ids = {f.id for f in old_prd.features} if old_prd else set()
            new_feature_ids = {f.id for f in new_prd.features}

            added = new_feature_ids - old_feature_ids
            removed = old_feature_ids - new_feature_ids

            # Determine change type
            if added:
                change_type = ChangeType.FEATURE_ADDED
                affected_features = list(added)
                diff = {"added": list(added)}
            elif removed:
                change_type = ChangeType.FEATURE_REMOVED
                affected_features = list(removed)
                diff = {"removed": list(removed)}
            else:
                change_type = ChangeType.METADATA_UPDATED
                affected_features = []
                diff = {"file_updated": True}

            # Create and emit event
            event = PRDChangeEvent(
                event_type=change_type,
                affected_features=affected_features,
                full_prd=new_prd,
                diff=diff,
                timestamp=datetime.now().isoformat()
            )

            controller._emit_event(event)

            logger.info(f"PRD reloaded from file: {change_type.value}, {len(affected_features)} features affected")
        except Exception as e:
            logger.error(f"Error reloading PRD: {e}")
    
    def ignore_next_change(self):
        """Mark next change as internal (should be ignored)"""
        self._ignore_next = True


class PRDFileWatcher:
    """Watch PROJECT_SPEC.md for external changes"""
    
    def __init__(self, spec_path: Path):
        self.spec_path = Path(spec_path)
        self.observer = Observer()
        self.handler = PRDFileHandler(spec_path)
    
    def start(self):
        """Start watching file"""
        watch_dir = self.spec_path.parent
        self.observer.schedule(self.handler, str(watch_dir), recursive=False)
        self.observer.start()
        logger.info(f"Started watching {self.spec_path}")
    
    def stop(self):
        """Stop watching file"""
        self.observer.stop()
        self.observer.join()
        logger.info("Stopped file watcher")
    
    def ignore_next_change(self):
        """Ignore next file change (caused by internal write)"""
        self.handler.ignore_next_change()


# Global watcher instance
_watcher: PRDFileWatcher = None


def start_prd_watcher(spec_path: Path = None):
    """Start global PRD file watcher"""
    global _watcher
    
    if spec_path is None:
        spec_path = Path.cwd() / ".buildrunner" / "PROJECT_SPEC.md"
    
    if _watcher is None:
        _watcher = PRDFileWatcher(spec_path)
        _watcher.start()
    
    return _watcher


def stop_prd_watcher():
    """Stop global PRD file watcher"""
    global _watcher
    
    if _watcher:
        _watcher.stop()
        _watcher = None
