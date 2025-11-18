# PROJECT_SPEC - Build 4A: Migration Tools

**Version:** 4A
**Duration:** 3-4 hours
**Goal:** Enable migration from BuildRunner 2.0 to BuildRunner 3.0 with zero data loss

---

## Overview

Build 4A creates migration tools to convert BuildRunner 2.0 projects to the new BuildRunner 3.0 format. This is critical for existing users upgrading from v2.0 to v3.0.

**Key Capabilities:**
- Parse legacy `.runner/` directory structure
- Convert to `features.json` format
- Migrate governance configurations
- Preserve git history
- Handle edge cases gracefully
- Comprehensive validation and testing

---

## Features

### Feature 1: Migration Command Interface

**Description:** CLI commands to initiate and control migration process

**Files to Create:**
1. `cli/migrate.py` (400+ lines)
   - Migration command group
   - `br migrate from-v2 <path>` command
   - Progress reporting with rich console
   - Dry-run mode for validation
   - Rollback capability
   - Interactive prompts for conflicts

**Implementation Details:**
```python
@migrate_app.command("from-v2")
def migrate_from_v2(
    project_path: str,
    dry_run: bool = False,
    backup: bool = True,
    force: bool = False
):
    """
    Migrate BuildRunner 2.0 project to 3.0 format

    Args:
        project_path: Path to BR 2.0 project
        dry_run: Validate without making changes
        backup: Create backup before migration
        force: Override validation warnings
    """
```

**Acceptance Criteria:**
- ✅ Command executes successfully on BR 2.0 projects
- ✅ Dry-run mode validates without modifications
- ✅ Clear progress reporting during migration
- ✅ Backup created automatically
- ✅ Helpful error messages for invalid inputs

---

### Feature 2: Legacy Structure Parser

**Description:** Parse and understand BuildRunner 2.0 directory structure

**Files to Create:**
2. `core/migration/v2_parser.py` (350+ lines)
   - `V2ProjectParser` class
   - Parse `.runner/` directory structure
   - Extract HRPO data
   - Parse legacy governance.yaml
   - Extract feature metadata
   - Identify Supabase integrations

**Data Structures:**
```python
@dataclass
class V2Project:
    """Represents a BuildRunner 2.0 project"""
    root_path: Path
    hrpo_data: Dict[str, Any]
    governance_config: Dict[str, Any]
    features: List[Dict[str, Any]]
    supabase_config: Optional[Dict[str, Any]]
    git_history: List[str]
    metadata: Dict[str, Any]
```

**Acceptance Criteria:**
- ✅ Correctly parses `.runner/` structure
- ✅ Extracts all HRPO data
- ✅ Handles missing/corrupt files gracefully
- ✅ Preserves all metadata
- ✅ Validates data integrity

---

### Feature 3: Format Converter

**Description:** Convert v2.0 data to v3.0 format

**Files to Create:**
3. `core/migration/converter.py` (450+ lines)
   - `MigrationConverter` class
   - HRPO → features.json mapping
   - Governance config format conversion
   - Data validation and sanitization
   - Conflict resolution strategies
   - Schema version handling

**Conversion Rules:**
```python
class MigrationConverter:
    def convert_hrpo_to_features(self, hrpo: Dict) -> List[Dict]:
        """
        Convert HRPO format to features.json format

        Mapping:
        - hrpo.hypothesis → feature.description
        - hrpo.reality → feature.status
        - hrpo.plan → feature.implementation_plan
        - hrpo.outcome → feature.acceptance_criteria
        """

    def convert_governance_config(self, old_config: Dict) -> Dict:
        """
        Convert legacy governance.yaml to new format

        Changes:
        - Rename fields for consistency
        - Update validation rules
        - Migrate quality thresholds
        """

    def migrate_supabase_data(self, supabase_config: Dict) -> Dict:
        """
        Migrate Supabase schema and data

        - Update table schemas
        - Migrate data with transformations
        - Preserve relationships
        """
```

**Acceptance Criteria:**
- ✅ All HRPO data converted correctly
- ✅ Governance configs mapped to new format
- ✅ No data loss during conversion
- ✅ Handles version conflicts
- ✅ Validates output against v3.0 schema

---

### Feature 4: Git History Preservation

**Description:** Ensure git history is preserved during migration

**Files to Create:**
4. `core/migration/git_handler.py` (200+ lines)
   - `GitMigrationHandler` class
   - Preserve commit history
   - Migrate branch structure
   - Handle migration commit
   - Tag migration point

**Implementation:**
```python
class GitMigrationHandler:
    def preserve_history(self, project_path: Path):
        """Ensure no git history loss"""

    def create_migration_commit(self, message: str):
        """Create atomic migration commit"""

    def tag_migration_point(self, version: str):
        """Tag the migration for rollback"""
```

**Acceptance Criteria:**
- ✅ Full git history preserved
- ✅ Migration creates atomic commit
- ✅ Migration tagged for reference
- ✅ No git corruption
- ✅ Branches preserved

---

### Feature 5: Edge Case Handling

**Description:** Gracefully handle edge cases and errors

**Files to Create:**
5. `core/migration/validators.py` (250+ lines)
   - Pre-migration validation
   - Post-migration verification
   - Data integrity checks
   - Error recovery strategies

**Edge Cases:**
- Missing `.runner/` directory
- Corrupt governance.yaml
- Incomplete HRPO data
- Version conflicts
- Supabase connection failures
- Large project handling (>1000 features)
- Non-standard directory structures

**Acceptance Criteria:**
- ✅ Detects invalid v2.0 projects
- ✅ Clear error messages
- ✅ Suggests fixes for common issues
- ✅ Graceful degradation
- ✅ Rollback on critical errors

---

### Feature 6: Comprehensive Testing

**Description:** Thorough test coverage for migration

**Files to Create:**
6. `tests/test_migration.py` (400+ lines)
   - Test v2.0 project parsing
   - Test format conversion
   - Test edge cases
   - Test git preservation
   - Integration tests with real v2.0 projects

**Test Scenarios:**
- Standard v2.0 project migration
- Project with missing files
- Project with corrupt configs
- Large project (stress test)
- Project with complex git history
- Dry-run validation
- Rollback scenarios

**Acceptance Criteria:**
- ✅ 85%+ test coverage
- ✅ All edge cases tested
- ✅ Integration tests pass
- ✅ Real v2.0 project tested
- ✅ Performance acceptable (<30s for typical project)

---

### Feature 7: Documentation

**Description:** User-facing migration documentation

**Files to Create:**
7. `docs/MIGRATION.md` (300+ lines)
   - Migration guide
   - Step-by-step instructions
   - Common issues and solutions
   - Examples with screenshots
   - FAQ section

**Documentation Sections:**
- Prerequisites
- Backup recommendations
- Migration command usage
- Validation steps
- Troubleshooting
- Rollback procedure
- Examples with real projects

**Acceptance Criteria:**
- ✅ Clear step-by-step guide
- ✅ Examples for common scenarios
- ✅ Troubleshooting section complete
- ✅ Rollback documented
- ✅ FAQ addresses common questions

---

## Implementation Plan

### Phase 1: Core Parser (1 hour)
**Files:** `core/migration/v2_parser.py`
- Parse `.runner/` structure
- Extract HRPO and governance data
- Basic validation

### Phase 2: Converter & Validator (1.5 hours)
**Files:** `core/migration/converter.py`, `core/migration/validators.py`
- Format conversion logic
- Edge case handling
- Validation rules

### Phase 3: CLI & Git Integration (1 hour)
**Files:** `cli/migrate.py`, `core/migration/git_handler.py`
- Migration command
- Git history preservation
- Progress reporting

### Phase 4: Testing & Documentation (0.5-1 hour)
**Files:** `tests/test_migration.py`, `docs/MIGRATION.md`
- Comprehensive tests
- User documentation
- Real project validation

---

## Dependencies

**Python Packages:**
- Python 3.11+
- pytest (testing)
- rich (console UI)
- pyyaml (config parsing)
- gitpython (git operations)

**External:**
- Git installed and configured
- Access to v2.0 project for testing

---

## Acceptance Criteria

### Functional Requirements:
- ✅ `br migrate from-v2 <path>` successfully migrates v2.0 projects
- ✅ All HRPO data converted to features.json
- ✅ Governance configs migrated correctly
- ✅ Git history fully preserved
- ✅ Dry-run mode validates without changes
- ✅ Backup created automatically

### Quality Requirements:
- ✅ 85%+ test coverage
- ✅ All tests passing
- ✅ Migration completes <30s for typical project
- ✅ Clear error messages
- ✅ Comprehensive documentation

### Validation:
- ✅ Tested on real BuildRunner 2.0 project
- ✅ No data loss verified
- ✅ Git integrity verified
- ✅ Edge cases handled gracefully

---

## Success Metrics

**Definition of Done:**
1. All 7 features implemented
2. 85%+ test coverage achieved
3. Successfully migrated build-runner-2.0 project in this workspace
4. Documentation complete
5. All acceptance criteria met
6. Quality gates passed

**Quality Gates:**
- Test coverage ≥ 85%
- All tests passing
- Code quality score ≥ 70
- Documentation complete
- No critical bugs

---

## Deliverables

**Code Files (7 files):**
1. `cli/migrate.py` - CLI migration commands
2. `core/migration/v2_parser.py` - v2.0 project parser
3. `core/migration/converter.py` - Format converter
4. `core/migration/git_handler.py` - Git operations
5. `core/migration/validators.py` - Validation logic
6. `tests/test_migration.py` - Test suite
7. `docs/MIGRATION.md` - User documentation

**Test Results:**
- All tests passing
- Coverage report
- Real project migration proof

**Documentation:**
- Migration guide
- API documentation
- Troubleshooting guide

---

## Notes

**Real-World Testing:**
This build will be tested on the actual `build-runner-2.0` project in the workspace at `/Users/byronhudson/Projects/build-runner-2.0`, providing real validation.

**Rollback Strategy:**
- All migrations create automatic backups
- Git tags mark migration point
- Rollback command available: `br migrate rollback`

**Future Enhancements:**
- Migrate from other project management tools
- Batch migration for multiple projects
- Cloud migration support (sync to remote)
