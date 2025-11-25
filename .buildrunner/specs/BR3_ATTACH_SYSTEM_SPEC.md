# BR3 Attach System - Retrofit Existing Projects

**Version:** 1.0.0
**Status:** Specification
**Priority:** High

## Project Overview

The BR3 Attach System enables BuildRunner 3 to be attached to existing projects by automatically scanning the codebase, analyzing structure, extracting features from implemented code, and generating a comprehensive PRD that becomes the source of truth for future development.

## Feature 1: Attach Command & Orchestrator

**Priority:** High

### Description

CLI command `br attach` that orchestrates the entire retrofit process: scanning, analyzing, generating PRD, and activating BR3 for the project.

### Requirements

- Command: `br attach` (runs in current directory)
- Detect project type (Python, JavaScript/TypeScript, Go, mixed)
- Check for existing BR files (.buildrunner/, PROJECT_SPEC.md)
- Archive legacy files if present
- Orchestrate all phases: scan → analyze → generate → review → activate
- Progress indicators for each phase
- Handle errors gracefully with rollback capability

### Acceptance Criteria

- [ ] `br attach` command executes in any project directory
- [ ] Detects project languages and frameworks
- [ ] Archives legacy BuildRunner files to `.buildrunner/legacy/`
- [ ] Shows progress through all phases
- [ ] Completes in <60 seconds for medium projects (10K LOC)
- [ ] Creates backup before making changes
- [ ] Rolls back on fatal errors

### Technical Details

**CLI Integration:**
- Add to `cli/attach_commands.py`
- Typer app with `@app.command()`
- Status updates via Rich progress bars

**Orchestration Flow:**
1. Validate project directory
2. Detect languages and structure
3. Migrate legacy files
4. Scan codebase
5. Extract features
6. Generate PRD draft
7. Open for review
8. Finalize and activate

## Feature 2: Codebase Scanner & Code Intelligence

**Priority:** High

### Description

Deep codebase analysis engine that scans all source files, performs AST parsing, identifies architectural patterns, and extracts code artifacts for feature mapping.

### Requirements

- Multi-language support: Python, JavaScript/TypeScript, Go (extensible)
- AST-based parsing (not regex)
- Extract: functions, classes, API routes, models, components, tests
- Identify patterns: REST APIs, GraphQL, MVC, microservices
- Map file structure to logical modules
- Detect frameworks: FastAPI, Express, React, Next.js, Flask, Django
- Extract metadata: docstrings, comments, type hints
- Build dependency graph from imports

### Acceptance Criteria

- [ ] Parses Python files and extracts functions, classes, decorators
- [ ] Parses JS/TS files and extracts components, functions, exports
- [ ] Parses Go files and extracts packages, functions, structs
- [ ] Detects API routes from FastAPI, Express, Flask, Django
- [ ] Identifies React/Vue components
- [ ] Extracts database models (SQLAlchemy, Mongoose, GORM)
- [ ] Builds import/dependency graph
- [ ] Handles large codebases (50K+ LOC) efficiently
- [ ] Respects .gitignore patterns
- [ ] Skips node_modules, venv, build directories

### Technical Details

**Parser Strategy:**
- Use `ast` module for Python
- Use `typescript` package for JS/TS (or tree-sitter)
- Use `go/parser` or tree-sitter for Go
- Visitor pattern for AST traversal

**Artifact Types:**
```python
@dataclass
class CodeArtifact:
    type: str  # "function", "class", "route", "component", "model"
    name: str
    file_path: Path
    line_number: int
    docstring: Optional[str]
    decorators: List[str]
    dependencies: List[str]
    metadata: Dict[str, Any]
```

**Key Components:**
- `core/retrofit/codebase_scanner.py` - Main scanner
- `core/retrofit/parsers/python_parser.py`
- `core/retrofit/parsers/typescript_parser.py`
- `core/retrofit/parsers/go_parser.py`
- `core/retrofit/artifact_extractor.py`

## Feature 3: Feature Extraction Engine

**Priority:** High

### Description

Intelligent engine that analyzes code artifacts and groups them into logical features using heuristics, patterns, and ML-based clustering.

### Requirements

- Group related code artifacts into features
- Use multiple heuristics: folder structure, naming patterns, imports
- Identify feature from route groups (e.g., `/api/auth/*` → Auth feature)
- Map UI components to features
- Extract feature names from code organization
- Generate feature descriptions from docstrings/comments
- Infer requirements from implementation
- Map tests to features for acceptance criteria
- Assign confidence scores (0.0-1.0) to each feature

### Acceptance Criteria

- [ ] Groups related files into feature buckets
- [ ] Detects features from API route patterns
- [ ] Maps frontend components to backend APIs
- [ ] Generates human-readable feature names
- [ ] Creates descriptions from code context
- [ ] Extracts requirements from function signatures
- [ ] Links tests to acceptance criteria
- [ ] Assigns confidence scores
- [ ] Handles ambiguous code (low confidence)
- [ ] Detects 80%+ of real features

### Technical Details

**Feature Detection Heuristics:**

1. **Route-Based:** Group by API path prefix
   - `/api/auth/*` → Authentication Feature
   - `/api/users/*` → User Management Feature

2. **Folder-Based:** Group by directory
   - `src/components/dashboard/` → Dashboard Feature
   - `backend/orders/` → Order Management Feature

3. **Import-Based:** Group by dependency clusters
   - Files importing same modules likely same feature

4. **Test-Based:** Group by test file organization
   - `tests/test_auth.py` → Authentication Feature

**Confidence Scoring:**
- 1.0: Clear pattern (route + folder + tests aligned)
- 0.8: Strong pattern (2 of 3 aligned)
- 0.6: Moderate pattern (1 of 3 aligned)
- 0.4: Weak pattern (heuristic-only)
- 0.2: Guess (single artifact)

**Key Components:**
- `core/retrofit/feature_extractor.py`
- `core/retrofit/feature_clusterer.py`
- `core/retrofit/confidence_scorer.py`

## Feature 4: PRD Synthesizer

**Priority:** High

### Description

Generates a complete PROJECT_SPEC.md from extracted features, creating proper markdown format with descriptions, requirements, acceptance criteria, and metadata.

### Requirements

- Convert extracted features to PRDFeature model
- Generate feature names from code context
- Create descriptions from docstrings and comments
- Infer requirements from function signatures and logic
- Extract acceptance criteria from test cases
- Build dependency graph between features
- Assign priorities based on code complexity and usage
- Mark confidence levels for review
- Generate proper PROJECT_SPEC.md markdown
- Preserve any existing PROJECT_SPEC content

### Acceptance Criteria

- [ ] Generates valid PROJECT_SPEC.md markdown
- [ ] Creates PRDFeature for each detected feature
- [ ] Includes feature descriptions from code
- [ ] Lists requirements inferred from implementation
- [ ] Maps test cases to acceptance criteria
- [ ] Shows confidence scores for human review
- [ ] Maintains feature dependencies
- [ ] Assigns realistic priorities
- [ ] Merges with existing content if present
- [ ] Output is immediately usable by PRD Controller

### Technical Details

**Generation Flow:**
1. Sort features by confidence (high → low)
2. Generate feature name (clean, title case)
3. Build description from:
   - Docstrings
   - File comments
   - Route documentation
   - README sections
4. Infer requirements from:
   - Function parameters
   - Database models
   - API contracts
5. Extract criteria from:
   - Test assertions
   - Validation logic
   - Error handling
6. Determine priority from:
   - Code complexity
   - Number of dependencies
   - Test coverage

**Markdown Template:**
```markdown
## Feature N: {feature_name}

**Priority:** {priority}
**Confidence:** {confidence_score}

### Description

{generated_description}

### Requirements

{inferred_requirements}

### Acceptance Criteria

{test-based_criteria}

### Technical Details

- **Files:** {file_list}
- **Dependencies:** {dependency_list}
```

**Key Components:**
- `core/retrofit/prd_synthesizer.py`
- `core/retrofit/description_builder.py`
- `core/retrofit/requirement_inferencer.py`

## Feature 5: Legacy Migration Engine

**Priority:** Medium

### Description

Migrates existing BuildRunner files (v1, v2, custom formats) to BR3 format, preserving all metadata, task history, and configurations.

### Requirements

- Detect legacy .buildrunner/ directories
- Parse old PROJECT_SPEC.md formats
- Convert old task formats to BR3
- Preserve task completion history
- Migrate configuration files
- Archive originals to `.buildrunner/legacy/`
- Maintain timestamps and metadata
- Handle malformed files gracefully

### Acceptance Criteria

- [ ] Detects legacy BuildRunner installations
- [ ] Parses v1 and v2 formats
- [ ] Converts tasks to BR3 format
- [ ] Preserves completion status
- [ ] Archives originals safely
- [ ] Logs migration actions
- [ ] Handles parse errors gracefully
- [ ] Zero data loss

### Technical Details

**Legacy Formats:**
- BuildRunner v1: Simple TODO.md
- BuildRunner v2: Structured PROJECT_SPEC.md
- Custom formats: JSON, YAML task files

**Migration Strategy:**
1. Backup entire .buildrunner/ to .buildrunner/legacy/
2. Parse old formats
3. Convert to BR3 data models
4. Generate new PROJECT_SPEC.md
5. Preserve completed task metadata

**Key Components:**
- `core/retrofit/legacy_migrator.py`
- `core/retrofit/parsers/legacy_parser.py`

## Feature 6: Task Reconciliation

**Priority:** Medium

### Description

Maps existing code to "completed" tasks in the task queue, marking implemented features as done while identifying gaps for new tasks.

### Requirements

- Mark features with existing code as "implemented"
- Create COMPLETED tasks for existing functionality
- Identify gaps between PRD and code
- Generate tasks for missing features
- Preserve work history if available
- Initialize task queue with correct state
- Set realistic task estimates based on existing code

### Acceptance Criteria

- [ ] Maps code to completed tasks
- [ ] Marks implemented features as complete
- [ ] Identifies missing functionality
- [ ] Generates tasks for gaps
- [ ] Sets correct task status
- [ ] Initializes dependency graph
- [ ] Provides gap analysis report
- [ ] Ready for immediate use

### Technical Details

**Reconciliation Logic:**
```python
for feature in extracted_features:
    if has_implementation(feature):
        # Create COMPLETED tasks
        tasks = generate_tasks_from_code(feature)
        for task in tasks:
            task.status = TaskStatus.COMPLETED
    else:
        # Create PENDING tasks
        tasks = generate_tasks_from_prd(feature)
        for task in tasks:
            task.status = TaskStatus.PENDING
```

**Key Components:**
- `core/retrofit/task_reconciler.py`
- `core/retrofit/gap_analyzer.py`

## Feature 7: Interactive Review Mode

**Priority:** Low

### Description

Interactive UI for reviewing and editing the auto-generated PRD before finalizing, with confidence indicators and suggested edits.

### Requirements

- Display draft PRD with confidence scores
- Highlight low-confidence sections
- Allow inline editing
- Suggest improvements for weak descriptions
- Show detected vs. actual feature counts
- Enable feature merging/splitting
- Validate changes before saving
- Provide "accept all" quick option

### Acceptance Criteria

- [ ] Shows draft PRD in readable format
- [ ] Displays confidence scores per feature
- [ ] Allows editing before finalization
- [ ] Highlights areas needing attention
- [ ] Enables feature reorganization
- [ ] Validates PRD structure
- [ ] Saves reviewed PRD
- [ ] Skippable with --auto flag

### Technical Details

**Review Interface:**
- Rich-based TUI with syntax highlighting
- Edit mode using $EDITOR
- Confidence indicators (🟢🟡🔴)
- Side-by-side code reference

**Key Components:**
- `cli/attach_review.py`
- Integration with Rich TUI

## Non-Functional Requirements

### Performance
- Scan 10K LOC project in <30 seconds
- Generate PRD in <10 seconds
- Total attach time <60 seconds for medium projects

### Accuracy
- 80%+ feature detection accuracy
- 90%+ file categorization accuracy
- Zero data loss during migration

### Compatibility
- Python 3.8+
- Node.js 16+ (for JS/TS parsing)
- Works on macOS, Linux, Windows

### Extensibility
- Plugin architecture for new languages
- Configurable heuristics
- Custom feature detectors

## Dependencies

### Python Packages
```
tree-sitter>=0.20.0      # Universal AST parsing
tree-sitter-python>=0.20.0
tree-sitter-javascript>=0.20.0
tree-sitter-typescript>=0.20.0
tree-sitter-go>=0.20.0
ast-decompiler>=0.7.0    # AST utilities
```

### External Tools
- Tree-sitter CLI (optional, for parser generation)

## Success Metrics

- Successful attach in 95% of projects
- 80%+ feature detection accuracy
- 90%+ user satisfaction with generated PRD
- <5 minutes manual review time
- Zero data loss in 100% of migrations

## Future Enhancements

1. **AI-Powered Feature Detection**
   - Use LLM to understand code intent
   - Better feature naming and descriptions
   - Context-aware requirement inference

2. **Multi-Repo Support**
   - Attach to monorepos
   - Link microservices
   - Cross-repo dependencies

3. **Continuous Sync**
   - Keep PRD in sync with code changes
   - Detect new features automatically
   - Alert on PRD-code drift

4. **Language Expansion**
   - Java, C#, Ruby, PHP, Rust
   - Mobile (Swift, Kotlin)
   - Infrastructure (Terraform, Kubernetes)

---

**This specification defines Build 4F: BR3 Attach System**
