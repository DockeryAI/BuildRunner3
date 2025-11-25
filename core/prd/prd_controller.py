"""
PRD Controller - Single Source of Truth for PROJECT_SPEC.md

Manages the PROJECT_SPEC as the single source of truth with:
- Unified in-memory representation
- Bidirectional file sync
- Version control (last 10 versions)
- Event emission for changes
- Natural language processing for updates
- Concurrency management with file locking
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
import json
import re
import threading
from collections import deque
from filelock import FileLock
import logging

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    FEATURE_ADDED = "feature_added"
    FEATURE_REMOVED = "feature_removed"  
    FEATURE_UPDATED = "feature_updated"
    METADATA_UPDATED = "metadata_updated"


@dataclass
class PRDFeature:
    """Single feature in the PRD"""
    id: str
    name: str
    description: str = ""
    priority: str = "medium"
    status: str = "planned"  # implemented, partial, planned
    requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    technical_details: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    
    
@dataclass
class PRD:
    """Complete PRD model"""
    project_name: str
    version: str = "1.0.0"
    overview: str = ""
    features: List[PRDFeature] = field(default_factory=list)
    architecture: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert PRD to dictionary"""
        return {
            "project_name": self.project_name,
            "version": self.version,
            "overview": self.overview,
            "features": [asdict(f) for f in self.features],
            "architecture": self.architecture,
            "metadata": self.metadata,
            "last_updated": self.last_updated
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'PRD':
        """Create PRD from dictionary"""
        features = [PRDFeature(**f) for f in data.get("features", [])]
        return PRD(
            project_name=data["project_name"],
            version=data.get("version", "1.0.0"),
            overview=data.get("overview", ""),
            features=features,
            architecture=data.get("architecture", {}),
            metadata=data.get("metadata", {}),
            last_updated=data.get("last_updated", datetime.now().isoformat())
        )


@dataclass
class PRDVersion:
    """Versioned PRD snapshot"""
    timestamp: str
    author: str
    prd_snapshot: PRD
    changes: Dict[str, Any]
    summary: str


@dataclass  
class PRDChangeEvent:
    """Event emitted when PRD changes"""
    event_type: ChangeType
    affected_features: List[str]
    full_prd: PRD
    diff: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PRDController:
    """
    Central controller for PROJECT_SPEC.md management
    
    Single source of truth with:
    - In-memory PRD representation
    - Bidirectional file sync
    - Version control (last 10 versions)
    - Event emission system
    - NLP-based updates
    - File locking for concurrency
    """
    
    def __init__(self, spec_path: Path):
        self.spec_path = Path(spec_path)
        self.lock_path = self.spec_path.parent / f".{self.spec_path.name}.lock"
        self._prd: Optional[PRD] = None
        self._versions: deque = deque(maxlen=10)  # Last 10 versions
        self._listeners: List[Callable[[PRDChangeEvent], None]] = []
        self._lock = threading.Lock()
        
        # Initialize by loading from file if exists
        if self.spec_path.exists():
            self.load_from_file()
        else:
            # Create default PRD
            self._prd = PRD(
                project_name=self.spec_path.parent.name,
                overview="New project"
            )
            self._save_to_file()
    
    @property
    def prd(self) -> PRD:
        """Get current PRD (read-only access)"""
        if self._prd is None:
            raise ValueError("PRD not initialized")
        return self._prd
    
    def load_from_file(self) -> None:
        """Load PRD from PROJECT_SPEC.md file"""
        with FileLock(str(self.lock_path)):
            if not self.spec_path.exists():
                raise FileNotFoundError(f"PROJECT_SPEC not found: {self.spec_path}")
            
            content = self.spec_path.read_text()
            self._prd = self._parse_markdown(content)
            logger.info(f"Loaded PRD from {self.spec_path}")
    
    def _parse_markdown(self, content: str) -> PRD:
        """Parse PROJECT_SPEC.md markdown into PRD model"""
        # Extract project name from first heading
        project_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        project_name = project_match.group(1) if project_match else "Unknown Project"
        
        # Extract overview
        overview_match = re.search(r'##\s+(?:Project\s+)?Overview\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
        overview = overview_match.group(1).strip() if overview_match else ""
        
        # Extract features
        features = []
        feature_pattern = r'##\s+Feature\s+(\d+):\s+(.+?)\n(.*?)(?=\n##\s+Feature|\n##\s+[^F]|\Z)'
        for match in re.finditer(feature_pattern, content, re.DOTALL):
            feature_num, feature_name, feature_body = match.groups()
            
            # Extract sections from feature body
            description_match = re.search(r'###\s+Description\s*\n(.*?)(?=\n###|\Z)', feature_body, re.DOTALL)
            description = description_match.group(1).strip() if description_match else ""

            # Extract requirements
            requirements = []
            req_match = re.search(r'###\s+Requirements\s*\n(.*?)(?=\n###|\Z)', feature_body, re.DOTALL)
            if req_match:
                for line in req_match.group(1).split('\n'):
                    if line.strip().startswith(('-', '*', '•')):
                        requirements.append(line.strip()[1:].strip())

            # Extract acceptance criteria
            acceptance_criteria = []
            ac_match = re.search(r'###\s+Acceptance\s+Criteria\s*\n(.*?)(?=\n###|\Z)', feature_body, re.DOTALL)
            if ac_match:
                for line in ac_match.group(1).split('\n'):
                    if line.strip().startswith(('-', '*', '•', '[ ]')):
                        criteria = line.strip()
                        for prefix in ['-', '*', '•', '[ ]', '[x]', '[X]']:
                            if criteria.startswith(prefix):
                                criteria = criteria[len(prefix):].strip()
                                break
                        acceptance_criteria.append(criteria)
            
            # Extract priority
            priority_match = re.search(r'\*\*Priority:\*\*\s*(\w+)', feature_body, re.IGNORECASE)
            priority = priority_match.group(1).lower() if priority_match else "medium"
            
            feature = PRDFeature(
                id=f"feature-{feature_num}",
                name=feature_name.strip(),
                description=description,
                priority=priority,
                requirements=requirements,
                acceptance_criteria=acceptance_criteria
            )
            features.append(feature)
        
        return PRD(
            project_name=project_name,
            overview=overview,
            features=features,
            last_updated=datetime.now().isoformat()
        )
    
    def _save_to_file(self) -> None:
        """Save current PRD to PROJECT_SPEC.md file"""
        with FileLock(str(self.lock_path)):
            markdown = self._generate_markdown(self._prd)
            self.spec_path.write_text(markdown)
            logger.info(f"Saved PRD to {self.spec_path}")
    
    def _generate_markdown(self, prd: PRD) -> str:
        """Generate PROJECT_SPEC.md markdown from PRD model"""
        lines = []
        
        # Header
        lines.append(f"# {prd.project_name}")
        lines.append("")
        lines.append(f"**Version:** {prd.version}")
        lines.append(f"**Last Updated:** {prd.last_updated}")
        lines.append("")
        
        # Overview
        if prd.overview:
            lines.append("## Project Overview")
            lines.append("")
            lines.append(prd.overview)
            lines.append("")
        
        # Features
        for i, feature in enumerate(prd.features, 1):
            lines.append(f"## Feature {i}: {feature.name}")
            lines.append("")
            lines.append(f"**Priority:** {feature.priority.title()}")
            lines.append("")
            
            if feature.description:
                lines.append("### Description")
                lines.append("")
                lines.append(feature.description)
                lines.append("")
            
            if feature.requirements:
                lines.append("### Requirements")
                lines.append("")
                for req in feature.requirements:
                    lines.append(f"- {req}")
                lines.append("")
            
            if feature.acceptance_criteria:
                lines.append("### Acceptance Criteria")
                lines.append("")
                for criterion in feature.acceptance_criteria:
                    lines.append(f"- [ ] {criterion}")
                lines.append("")

        return "\n".join(lines)
    
    def update_prd(self, updates: Dict[str, Any], author: str = "system") -> PRDChangeEvent:
        """
        Update PRD with changes and emit event
        
        Args:
            updates: Dictionary with PRD updates
            author: Who made the change
            
        Returns:
            PRDChangeEvent with details of change
        """
        with self._lock:
            # Save current version
            old_prd = self._prd
            self._save_version(old_prd, author, "Pre-update snapshot")
            
            # Apply updates
            change_type, affected_features, diff = self._apply_updates(updates)
            
            # Update timestamp
            self._prd.last_updated = datetime.now().isoformat()
            
            # Save to file
            self._save_to_file()
            
            # Create and emit event
            event = PRDChangeEvent(
                event_type=change_type,
                affected_features=affected_features,
                full_prd=self._prd,
                diff=diff
            )
            
            self._emit_event(event)
            
            logger.info(f"PRD updated: {change_type.value} affecting {len(affected_features)} features")
            
            return event
    
    def _apply_updates(self, updates: Dict[str, Any]) -> tuple:
        """Apply updates to PRD and determine change type"""
        change_type = ChangeType.METADATA_UPDATED
        affected_features = []
        diff = {}
        
        # Handle feature additions
        if "add_feature" in updates:
            feature_data = updates["add_feature"]
            feature = PRDFeature(**feature_data)
            self._prd.features.append(feature)
            change_type = ChangeType.FEATURE_ADDED
            affected_features.append(feature.id)
            diff["added"] = [feature.id]
        
        # Handle feature removals
        if "remove_feature" in updates:
            feature_id = updates["remove_feature"]
            self._prd.features = [f for f in self._prd.features if f.id != feature_id]
            change_type = ChangeType.FEATURE_REMOVED
            affected_features.append(feature_id)
            diff["removed"] = [feature_id]
        
        # Handle feature updates
        if "update_feature" in updates:
            feature_id = updates["update_feature"]["id"]
            feature_updates = updates["update_feature"]["updates"]
            
            for feature in self._prd.features:
                if feature.id == feature_id:
                    for key, value in feature_updates.items():
                        if hasattr(feature, key):
                            setattr(feature, key, value)
                    change_type = ChangeType.FEATURE_UPDATED
                    affected_features.append(feature_id)
                    diff["updated"] = {feature_id: list(feature_updates.keys())}
                    break
        
        # Handle metadata updates
        for key in ["project_name", "version", "overview", "metadata"]:
            if key in updates:
                setattr(self._prd, key, updates[key])
                diff[key] = updates[key]
        
        return change_type, affected_features, diff
    
    def parse_natural_language(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language to PRD updates

        Uses enhanced NLP parser (spaCy if available, regex fallback)

        Supports:
        - "add feature <name>" -> add_feature
        - "remove feature <id>" -> remove_feature
        - "update feature <id> <field> <value>" -> update_feature
        - Complex commands with spaCy
        """
        try:
            from core.prd.nlp_parser import get_nlp_parser

            parser = get_nlp_parser()

            # Convert features to dict format for parser
            current_features = [
                {
                    "id": f.id,
                    "name": f.name,
                    "description": f.description,
                    "priority": f.priority
                }
                for f in self._prd.features
            ]

            return parser.parse(text, current_features)

        except Exception as e:
            logger.error(f"NLP parsing error: {e}, falling back to basic regex")

            # Fallback to basic regex (original implementation)
            text_lower = text.lower().strip()

            # Add feature pattern
            add_match = re.match(r'add\s+(?:feature\s+)?(.+)', text_lower)
            if add_match:
                feature_name = add_match.group(1).strip()
                feature_id = f"feature-{len(self._prd.features) + 1}"
                return {
                    "add_feature": {
                        "id": feature_id,
                        "name": feature_name.title(),
                        "description": f"Feature: {feature_name}",
                        "priority": "medium"
                    }
                }

            # Remove feature pattern
            remove_match = re.match(r'remove\s+(?:feature\s+)?(.+)', text_lower)
            if remove_match:
                feature_ref = remove_match.group(1).strip()
                for feature in self._prd.features:
                    if feature.id == feature_ref or feature.name.lower() == feature_ref:
                        return {"remove_feature": feature.id}

            # Update feature pattern
            update_match = re.match(r'update\s+(?:feature\s+)?(\S+)\s+to\s+(.+)', text_lower)
            if update_match:
                feature_ref = update_match.group(1).strip()
                new_desc = update_match.group(2).strip()

                for feature in self._prd.features:
                    if feature.id == feature_ref or feature.name.lower() == feature_ref:
                        return {
                            "update_feature": {
                                "id": feature.id,
                                "updates": {"description": new_desc}
                            }
                        }

            return {}
    
    def _save_version(self, prd: PRD, author: str, summary: str) -> None:
        """Save PRD version to history"""
        version = PRDVersion(
            timestamp=datetime.now().isoformat(),
            author=author,
            prd_snapshot=prd,
            changes={},
            summary=summary
        )
        self._versions.append(version)
        logger.debug(f"Saved version: {summary}")
    
    def get_versions(self) -> List[PRDVersion]:
        """Get version history"""
        return list(self._versions)
    
    def rollback_to_version(self, version_index: int) -> None:
        """Rollback to a specific version"""
        if version_index < 0 or version_index >= len(self._versions):
            raise ValueError(f"Invalid version index: {version_index}")
        
        with self._lock:
            version = self._versions[version_index]
            self._prd = version.prd_snapshot
            self._save_to_file()
            
            # Emit event
            event = PRDChangeEvent(
                event_type=ChangeType.METADATA_UPDATED,
                affected_features=[],
                full_prd=self._prd,
                diff={"rollback": version.timestamp}
            )
            self._emit_event(event)
            
            logger.info(f"Rolled back to version from {version.timestamp}")
    
    def subscribe(self, listener: Callable[[PRDChangeEvent], None]) -> None:
        """Subscribe to PRD change events"""
        self._listeners.append(listener)
        logger.debug(f"Added listener: {listener.__name__}")
    
    def unsubscribe(self, listener: Callable[[PRDChangeEvent], None]) -> None:
        """Unsubscribe from PRD change events"""
        if listener in self._listeners:
            self._listeners.remove(listener)
            logger.debug(f"Removed listener: {listener.__name__}")
    
    def _emit_event(self, event: PRDChangeEvent) -> None:
        """Emit PRD change event to all listeners"""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in listener {listener.__name__}: {e}")


# Singleton instance
_controller: Optional[PRDController] = None


def get_prd_controller(spec_path: Optional[Path] = None) -> PRDController:
    """Get or create singleton PRD controller"""
    global _controller
    
    if _controller is None:
        if spec_path is None:
            # Default to .buildrunner/PROJECT_SPEC.md
            spec_path = Path.cwd() / ".buildrunner" / "PROJECT_SPEC.md"
        _controller = PRDController(spec_path)
    
    return _controller
