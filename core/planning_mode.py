"""
Planning Mode Detection - Detect Strategic Discussions

Detects when user is in planning/strategy mode and suggests appropriate
model switching (Opus for planning, Sonnet for execution).
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any


class PlanningModeDetector:
    """
    Detect strategic planning conversations and suggest model switching.

    Features:
    - Detect strategic keywords
    - Auto-suggest Opus for planning, Sonnet for execution
    - Log planning sessions to context
    """

    # Strategic keywords that indicate planning mode
    STRATEGIC_KEYWORDS = [
        'architecture', 'design', 'approach', 'strategy', 'plan',
        'should we', 'how should', 'what if', 'consider', 'evaluate',
        'pros and cons', 'trade-offs', 'decide', 'choose', 'compare',
        'long-term', 'scalability', 'maintainability', 'performance',
        'security', 'infrastructure', 'deployment', 'migration'
    ]

    # Tactical keywords that indicate execution mode
    TACTICAL_KEYWORDS = [
        'implement', 'build', 'create', 'write', 'code', 'fix', 'debug',
        'test', 'deploy', 'commit', 'push', 'run', 'execute', 'install',
        'configure', 'setup', 'add', 'update', 'delete', 'modify'
    ]

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.planning_log = self.project_root / ".buildrunner" / "context" / "planning-notes.md"

    def detect_mode(self, text: str) -> Tuple[str, float]:
        """
        Detect if text is strategic (planning) or tactical (execution).

        Returns:
            Tuple of (mode, confidence) where mode is 'planning' or 'execution'
            and confidence is 0.0 to 1.0
        """
        text_lower = text.lower()

        # Count strategic keywords
        strategic_count = sum(1 for keyword in self.STRATEGIC_KEYWORDS if keyword in text_lower)

        # Count tactical keywords
        tactical_count = sum(1 for keyword in self.TACTICAL_KEYWORDS if keyword in text_lower)

        # Calculate confidence
        total_keywords = strategic_count + tactical_count

        if total_keywords == 0:
            return 'execution', 0.5  # Default to execution mode

        strategic_ratio = strategic_count / total_keywords

        if strategic_ratio > 0.6:
            return 'planning', strategic_ratio
        elif strategic_ratio < 0.4:
            return 'execution', 1.0 - strategic_ratio
        else:
            return 'mixed', 0.5

    def suggest_model(self, mode: str, confidence: float) -> Optional[str]:
        """
        Suggest which model to use based on detected mode.

        Returns:
            'opus' for planning, 'sonnet' for execution, None for mixed/uncertain
        """
        if confidence < 0.6:
            return None  # Not confident enough to suggest

        if mode == 'planning':
            return 'opus'
        elif mode == 'execution':
            return 'sonnet'
        else:
            return None

    def log_planning_session(self, user_input: str, mode: str, confidence: float):
        """Log planning session to context"""
        self.planning_log.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()

        log_entry = f"""
## Planning Session - {timestamp}

**Mode**: {mode} (confidence: {confidence:.2f})

**User Input**:
{user_input}

---
"""

        # Append to log
        with open(self.planning_log, 'a') as f:
            f.write(log_entry)

    def get_planning_history(self, limit: int = 10) -> List[str]:
        """Get recent planning sessions"""
        if not self.planning_log.exists():
            return []

        with open(self.planning_log, 'r') as f:
            content = f.read()

        # Split by session separator
        sessions = content.split('---')

        # Return most recent sessions
        return sessions[-limit:] if sessions else []

    def analyze_conversation(self, messages: List[str]) -> Dict[str, float]:
        """
        Analyze entire conversation to determine overall mode.

        Returns:
            Dictionary with mode distribution percentages
        """
        modes = {'planning': 0, 'execution': 0, 'mixed': 0}

        for message in messages:
            mode, _ = self.detect_mode(message)
            modes[mode] += 1

        total = len(messages)

        if total == 0:
            return {'planning': 0.0, 'execution': 0.0, 'mixed': 0.0}

        return {
            'planning': modes['planning'] / total,
            'execution': modes['execution'] / total,
            'mixed': modes['mixed'] / total
        }


class ModelSwitchSuggester:
    """
    Suggest model switches during conversation.
    """

    def __init__(self, detector: PlanningModeDetector):
        self.detector = detector
        self.current_model = 'sonnet'  # Default

    def should_suggest_switch(self, user_input: str) -> Tuple[bool, Optional[str], str]:
        """
        Determine if model switch should be suggested.

        Returns:
            Tuple of (should_switch, suggested_model, reason)
        """
        mode, confidence = self.detector.detect_mode(user_input)
        suggested_model = self.detector.suggest_model(mode, confidence)

        if not suggested_model or suggested_model == self.current_model:
            return False, None, ""

        # Build reason
        if suggested_model == 'opus':
            reason = (
                "Detected strategic planning discussion. "
                "Opus is better suited for architecture decisions, "
                "trade-off analysis, and long-term planning."
            )
        else:
            reason = (
                "Detected tactical execution request. "
                "Sonnet is optimized for code implementation, "
                "debugging, and rapid iteration."
            )

        return True, suggested_model, reason

    def format_suggestion(self, suggested_model: str, reason: str) -> str:
        """Format switch suggestion for user"""
        return f"""
╔═══════════════════════════════════════╗
║   Model Switch Recommended            ║
╠═══════════════════════════════════════╣
║ Suggested Model: {suggested_model.upper():<22} ║
║                                       ║
║ {reason[:37]}║
║ {reason[37:74] if len(reason) > 37 else ' ' * 37}║
╚═══════════════════════════════════════╝

Switch models? (y/n):
"""


# ===== Enhanced Auto-Detection Functions =====

def detect_planning_mode(
    user_prompt: str,
    project_state: Dict[str, Any],
    conversation_history: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Detect if user request requires planning mode (Opus)

    Args:
        user_prompt: User's request
        project_state: Current project state (features, spec exists, etc.)
        conversation_history: Recent conversation (not currently used)

    Returns:
        Dict with:
            - use_opus: bool (True if Opus recommended)
            - confidence: float (0-1)
            - reason: str (explanation for decision)
    """
    # Indicators for Opus (planning mode)
    opus_indicators = [
        "new project",
        "design",
        "architecture",
        "plan",
        "spec",
        "requirements",
        "what should",
        "how to structure",
        "best approach",
        "strategy",
        "evaluate",
        "compare",
        "consider"
    ]

    # Indicators for Sonnet (execution mode)
    sonnet_indicators = [
        "implement",
        "add feature",
        "fix bug",
        "write test",
        "update",
        "refactor",
        "debug",
        "build",
        "create",
        "code",
        "install",
        "run"
    ]

    # Check if PROJECT_SPEC.md exists
    has_spec = project_state.get("has_spec", False)

    # Check if features defined
    has_features = len(project_state.get("features", [])) > 0

    # Score prompt
    prompt_lower = user_prompt.lower()
    opus_score = sum(1 for indicator in opus_indicators if indicator in prompt_lower)
    sonnet_score = sum(1 for indicator in sonnet_indicators if indicator in prompt_lower)

    # Decision logic
    if not has_spec and not has_features:
        # New project - always use Opus for planning
        return {
            "use_opus": True,
            "confidence": 0.95,
            "reason": "New project detected - planning mode recommended"
        }

    if opus_score > sonnet_score:
        # Planning-related request
        confidence = min(0.9, 0.6 + (opus_score * 0.1))
        return {
            "use_opus": True,
            "confidence": confidence,
            "reason": f"Planning-related keywords detected ({opus_score})"
        }

    if sonnet_score > opus_score:
        # Execution-related request
        confidence = min(0.9, 0.6 + (sonnet_score * 0.1))
        return {
            "use_opus": False,
            "confidence": confidence,
            "reason": f"Execution-related keywords detected ({sonnet_score})"
        }

    # Ambiguous - default to Sonnet for existing projects
    if has_spec and has_features:
        return {
            "use_opus": False,
            "confidence": 0.6,
            "reason": "Ambiguous request, defaulting to execution mode"
        }

    # Ambiguous - default to Opus for new projects
    return {
        "use_opus": True,
        "confidence": 0.6,
        "reason": "Ambiguous request, defaulting to planning mode"
    }


def should_use_opus(detection: Dict[str, Any], confidence_threshold: float = 0.7) -> Optional[bool]:
    """
    Decide if Opus should be used based on detection

    Args:
        detection: Result from detect_planning_mode()
        confidence_threshold: Minimum confidence for auto-selection

    Returns:
        True if Opus should be used, False if not, None if uncertain
    """
    if detection["confidence"] >= confidence_threshold:
        return detection["use_opus"]

    # Low confidence - ask user
    return None


def should_use_sonnet(detection: Dict[str, Any], confidence_threshold: float = 0.7) -> Optional[bool]:
    """
    Decide if Sonnet should be used based on detection

    Args:
        detection: Result from detect_planning_mode()
        confidence_threshold: Minimum confidence for auto-selection

    Returns:
        True if Sonnet should be used, False if not, None if uncertain
    """
    if detection["confidence"] >= confidence_threshold:
        return not detection["use_opus"]

    # Low confidence - ask user
    return None


def get_project_state(project_root: Path) -> Dict[str, Any]:
    """
    Get current project state for mode detection

    Args:
        project_root: Root directory of the project

    Returns:
        Dict with:
            - has_spec: bool (PROJECT_SPEC.md exists)
            - has_features: bool (features.json exists)
            - features: List[Dict] (list of features)
            - feature_count: int (total features)
            - completed_count: int (completed features)
    """
    project_root = Path(project_root)
    buildrunner_dir = project_root / ".buildrunner"

    spec_path = buildrunner_dir / "PROJECT_SPEC.md"
    features_path = buildrunner_dir / "features.json"

    has_spec = spec_path.exists()
    has_features = features_path.exists()

    features = []
    if has_features:
        try:
            features_data = json.loads(features_path.read_text())
            features = features_data.get("features", [])
        except (json.JSONDecodeError, FileNotFoundError):
            features = []

    completed = [f for f in features if f.get("status") == "completed"]

    return {
        "has_spec": has_spec,
        "has_features": has_features,
        "features": features,
        "feature_count": len(features),
        "completed_count": len(completed)
    }


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python planning_mode.py <project_root> <text>")
        sys.exit(1)

    project_root = sys.argv[1]
    text = ' '.join(sys.argv[2:])

    # Legacy detector
    detector = PlanningModeDetector(project_root)
    mode, confidence = detector.detect_mode(text)

    print(f"\n=== Legacy Detector ===")
    print(f"Detected Mode: {mode}")
    print(f"Confidence: {confidence:.2%}")

    suggested_model = detector.suggest_model(mode, confidence)
    if suggested_model:
        print(f"Suggested Model: {suggested_model}")

    # New enhanced detector
    print(f"\n=== Enhanced Detector ===")
    project_state = get_project_state(Path(project_root))
    detection = detect_planning_mode(text, project_state, [])

    print(f"Use Opus: {detection['use_opus']}")
    print(f"Confidence: {detection['confidence']:.2%}")
    print(f"Reason: {detection['reason']}")

    use_opus = should_use_opus(detection)
    if use_opus is not None:
        print(f"Decision: Use {'Opus' if use_opus else 'Sonnet'}")
    else:
        print(f"Decision: Ask user (low confidence)")


if __name__ == "__main__":
    main()
