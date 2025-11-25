"""Build session management for BuildRunner 3"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime

class SessionStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class ComponentStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    BLOCKED = "blocked"

@dataclass
class Component:
    id: str
    name: str
    type: str
    status: ComponentStatus = ComponentStatus.NOT_STARTED
    progress: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    tests_pass: bool = False
    error: Optional[str] = None

@dataclass
class Feature:
    id: str
    name: str
    description: str
    priority: str = "medium"
    component: str = ""
    status: ComponentStatus = ComponentStatus.NOT_STARTED
    progress: float = 0.0
    tasks: List[Dict] = field(default_factory=list)
    estimated_time: int = 0

@dataclass
class BuildSession:
    id: str
    project_name: str
    project_alias: str
    project_path: str
    start_time: int
    status: SessionStatus = SessionStatus.INITIALIZING
    components: List[Component] = field(default_factory=list)
    features: List[Feature] = field(default_factory=list)
    current_component: Optional[str] = None
    current_feature: Optional[str] = None
    end_time: Optional[int] = None

class SessionManager:
    """Singleton session manager"""
    _instance = None
    _sessions: Dict[str, BuildSession] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_session(self, project_name: str, project_alias: str, project_path: str) -> BuildSession:
        session_id = f"session-{datetime.now().timestamp()}"
        session = BuildSession(
            id=session_id,
            project_name=project_name,
            project_alias=project_alias,
            project_path=project_path,
            start_time=int(datetime.now().timestamp() * 1000),
        )
        self._sessions[project_alias] = session
        return session
    
    def get_session(self, project_alias: str) -> Optional[BuildSession]:
        return self._sessions.get(project_alias)
    
    def update_component(self, project_alias: str, component_id: str, **updates):
        session = self._sessions.get(project_alias)
        if not session:
            return
        
        for comp in session.components:
            if comp.id == component_id:
                for key, value in updates.items():
                    if hasattr(comp, key):
                        setattr(comp, key, value)
                break
    
    def update_feature(self, project_alias: str, feature_id: str, **updates):
        session = self._sessions.get(project_alias)
        if not session:
            return
        
        for feat in session.features:
            if feat.id == feature_id:
                for key, value in updates.items():
                    if hasattr(feat, key):
                        setattr(feat, key, value)
                break
    
    def list_sessions(self) -> List[BuildSession]:
        return list(self._sessions.values())

session_manager = SessionManager()
