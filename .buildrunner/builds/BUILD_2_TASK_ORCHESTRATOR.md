# Build 2: Task Orchestration Engine

**Purpose:** Transform BuildRunner into a self-orchestrating system that manages Claude automatically

**Duration:** 3 days (2 parallel worktrees)
**Branches:** `build/task-generator`, `build/orchestrator`

---

## Architecture Changes to Current BuildRunner

### Current State (Manual)
```
Human → Creates task lists → Directs Claude → Verifies output
```

### New State (Automated)
```
PROJECT_SPEC.md → BR generates tasks → BR directs Claude → BR verifies → BR continues
```

### Core Changes Required

1. **Replace manual features.json updates** with auto-generated task queue
2. **Replace manual verification** with real-time monitoring
3. **Add execution engine** that generates Claude prompts
4. **Add state persistence** for recovery
5. **Change CLI** from manual commands to orchestrated runs

---

## Parallel Execution Plan

### Worktree A: Task Generation System
**Branch:** `build/task-generator`
**Path:** `../br3-task-gen`

### Worktree B: Orchestration Runtime
**Branch:** `build/orchestrator`
**Path:** `../br3-orchestrator`

---

## Worktree A: Task Generation System

### Setup
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add ../br3-task-gen -b build/task-generator
cd ../br3-task-gen

# Initialize state tracking
cat > CLAUDE.md << 'EOF'
# Task Generator Build

## Current Batch: 1 (Core Components)
## Tasks: 3
## Status: Starting

## Completed: []
## In Progress: Task A.1
EOF
```

### Batch A1: Core Parser (3 tasks, 4 hours)

#### Task A.1: Spec Parser (90 min)
**File:** `core/spec_parser.py`

**Requirements:**
```python
class SpecParser:
    """Parse PROJECT_SPEC.md into structured features"""

    def parse_spec(self, spec_path: Path) -> Dict:
        """
        Extract:
        - Features list with descriptions
        - Technical requirements
        - Dependencies between features
        - Acceptance criteria

        Returns: {
            "features": [
                {
                    "id": "auth_system",
                    "name": "User Authentication",
                    "description": "...",
                    "requirements": [...],
                    "dependencies": [],
                    "acceptance_criteria": [...]
                }
            ]
        }
        """

    def extract_features(self, content: str) -> List[Feature]:
        """Parse markdown for ## Features sections"""

    def extract_dependencies(self, content: str) -> Dict:
        """Identify feature dependencies"""

    def validate_spec(self, spec_dict: Dict) -> bool:
        """Ensure spec has all required sections"""
```

**Tests:** `tests/test_spec_parser.py`
- Test parsing sample PROJECT_SPEC.md
- Test feature extraction
- Test dependency detection
- Test validation

**Acceptance Criteria:**
- [ ] Parses markdown PROJECT_SPEC.md
- [ ] Extracts features with metadata
- [ ] Identifies dependencies
- [ ] Returns structured dict
- [ ] 90% test coverage

#### Task A.2: Task Decomposer (90 min)
**File:** `core/task_decomposer.py`

**Requirements:**
```python
class TaskDecomposer:
    """Break features into atomic 1-2 hour tasks"""

    def decompose_feature(self, feature: Dict) -> List[Task]:
        """
        Break down into:
        - Database models (if needed)
        - API endpoints (if needed)
        - Business logic
        - UI components (if needed)
        - Tests
        - Documentation

        Each task ~1-2 hours
        """

    def estimate_complexity(self, task: Task) -> str:
        """Return 'simple' | 'medium' | 'complex'"""

    def calculate_duration(self, task: Task) -> int:
        """Estimate minutes: 60, 90, or 120"""

    def add_acceptance_criteria(self, task: Task) -> Task:
        """Add specific, measurable criteria"""
```

**Tests:** `tests/test_task_decomposer.py`
- Test feature → tasks breakdown
- Test complexity scoring
- Test duration estimates
- Test acceptance criteria generation

**Acceptance Criteria:**
- [ ] Breaks features into 1-2 hour chunks
- [ ] Assigns complexity scores
- [ ] Estimates duration
- [ ] Adds clear acceptance criteria
- [ ] 90% test coverage

#### Task A.3: Dependency Graph Builder (60 min)
**File:** `core/dependency_graph.py`

**Requirements:**
```python
class DependencyGraph:
    """Build DAG of task dependencies"""

    def __init__(self):
        self.graph = {}  # adjacency list

    def add_task(self, task_id: str, depends_on: List[str]):
        """Add task with dependencies"""

    def get_execution_order(self) -> List[List[str]]:
        """
        Return tasks in execution order
        Each sublist can run in parallel

        Example: [[task1, task2], [task3], [task4, task5]]
        """

    def find_parallelizable(self) -> List[Tuple[str, str]]:
        """Identify tasks that can run simultaneously"""

    def detect_cycles(self) -> bool:
        """Ensure no circular dependencies"""
```

**Tests:** `tests/test_dependency_graph.py`
- Test DAG construction
- Test execution ordering
- Test parallel task identification
- Test cycle detection

**Acceptance Criteria:**
- [ ] Builds valid DAG
- [ ] Calculates execution order
- [ ] Identifies parallel tasks
- [ ] Detects circular dependencies
- [ ] 90% test coverage

### Verification Gate A1
```
✅ Batch A1 Complete
- spec_parser.py created and tested
- task_decomposer.py created and tested
- dependency_graph.py created and tested
- All tests passing
- Ready for Batch A2
```

---

## Worktree B: Orchestration Runtime

### Setup
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add ../br3-orchestrator -b build/orchestrator
cd ../br3-orchestrator

# Initialize state tracking
cat > CLAUDE.md << 'EOF'
# Orchestrator Build

## Current Batch: 1 (Core Runtime)
## Tasks: 3
## Status: Starting

## Completed: []
## In Progress: Task B.1
EOF
```

### Batch B1: Core Runtime (3 tasks, 4 hours)

#### Task B.1: Batch Optimizer (90 min)
**File:** `core/batch_optimizer.py`

**Requirements:**
```python
class BatchOptimizer:
    """Group tasks into optimal batches for Claude"""

    BATCH_RULES = {
        "simple": 3,      # Basic CRUD, functions
        "medium": 2,      # Business logic, APIs
        "complex": 1,     # Algorithms, state machines
        "critical": 1     # Auth, payments, security
    }

    def create_batches(self, tasks: List[Task]) -> List[Batch]:
        """
        Group by:
        - Domain (never mix frontend/backend/database)
        - Complexity (fewer complex tasks per batch)
        - Dependencies (dependent tasks separate)

        Max 3 tasks per batch
        """

    def validate_batch(self, batch: Batch) -> bool:
        """
        Ensure:
        - Same domain
        - Total time < 4 hours
        - No dependency conflicts
        """

    def prioritize_batches(self, batches: List[Batch]) -> List[Batch]:
        """Order by dependency and priority"""
```

**Tests:** `tests/test_batch_optimizer.py`
- Test domain grouping
- Test batch size limits
- Test complexity-based sizing
- Test validation

**Acceptance Criteria:**
- [ ] Groups tasks by domain
- [ ] Respects complexity limits
- [ ] Max 3 tasks per batch
- [ ] Validates batch coherence
- [ ] 90% test coverage

#### Task B.2: Prompt Builder (90 min)
**File:** `core/prompt_builder.py`

**Requirements:**
```python
class PromptBuilder:
    """Generate focused Claude prompts from task batches"""

    def build_prompt(self, batch: Batch, context: Context) -> str:
        """
        Generate prompt with:
        - Clear task descriptions
        - File paths to create/modify
        - Dependencies/context
        - Acceptance criteria
        - Explicit stop point
        """

    def add_context(self, prompt: str, context: Context) -> str:
        """
        Include:
        - Completed components
        - Available dependencies
        - Current state

        Max 4000 tokens context
        """

    def add_verification(self, prompt: str, criteria: List) -> str:
        """Add specific success criteria"""

    def format_for_claude(self, prompt: str) -> str:
        """Claude-optimized formatting"""
```

**Tests:** `tests/test_prompt_builder.py`
- Test prompt generation
- Test context inclusion
- Test token limits
- Test formatting

**Acceptance Criteria:**
- [ ] Generates clear, focused prompts
- [ ] Includes relevant context only
- [ ] Stays under token limits
- [ ] Has explicit stop points
- [ ] 90% test coverage

#### Task B.3: Context Manager (60 min)
**File:** `core/context_manager.py`

**Requirements:**
```python
class ContextManager:
    """Manage context window for optimal Claude performance"""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.context_dir = Path(".buildrunner/context")

    def get_context_for_batch(self, batch: Batch) -> Context:
        """
        Gather:
        - Dependencies (completed code)
        - Specifications
        - Current state

        Within token budget
        """

    def track_completed(self, task_id: str, files: List[Path]):
        """Store completed components"""

    def calculate_tokens(self, text: str) -> int:
        """Estimate token count"""

    def compress_if_needed(self, context: str) -> str:
        """Compress context if over budget"""
```

**Tests:** `tests/test_context_manager.py`
- Test context gathering
- Test token counting
- Test compression
- Test state tracking

**Acceptance Criteria:**
- [ ] Gathers relevant context
- [ ] Respects token limits
- [ ] Tracks completed work
- [ ] Compresses when needed
- [ ] 90% test coverage

### Verification Gate B1
```
✅ Batch B1 Complete
- batch_optimizer.py created and tested
- prompt_builder.py created and tested
- context_manager.py created and tested
- All tests passing
- Ready for Batch B2
```

---

## Integration Commands

After both worktrees complete Batch 1:

```bash
# Check status
cd ../br3-task-gen && git status && pytest tests/
cd ../br3-orchestrator && git status && pytest tests/

# If all tests pass, continue to Batch 2
# If issues, fix before proceeding
```

---

## Expected Output Structure

```
.buildrunner/
├── core/
│   ├── spec_parser.py       (from A.1)
│   ├── task_decomposer.py   (from A.2)
│   ├── dependency_graph.py  (from A.3)
│   ├── batch_optimizer.py   (from B.1)
│   ├── prompt_builder.py    (from B.2)
│   └── context_manager.py   (from B.3)
└── tests/
    ├── test_spec_parser.py
    ├── test_task_decomposer.py
    ├── test_dependency_graph.py
    ├── test_batch_optimizer.py
    ├── test_prompt_builder.py
    └── test_context_manager.py
```

---

## Next Steps (After Batch 1)

### Batch A2: Task Queue System
- Task queue manager
- Priority scheduling
- State persistence

### Batch B2: Execution Engine
- Orchestrator main loop
- File monitor
- Verification engine

These will complete the Task Orchestration Engine, allowing BuildRunner to self-orchestrate all remaining development.