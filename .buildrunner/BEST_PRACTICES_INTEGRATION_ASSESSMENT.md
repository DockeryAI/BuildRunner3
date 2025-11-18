# Best Practices Integration Assessment for BuildRunner3

**Date:** 2025-11-18
**Source:** BuildRunnerSaaS Best Practices Guide (3000+ lines)
**Question:** Which principles to build into BR3? How to ensure they're used every build?

---

## TL;DR - Recommendation

**YES - Build core principles into BuildRunner3, but make it progressive:**

1. **Tier 1 (ALWAYS ENFORCED)**: Security, code quality basics, testing minimums
2. **Tier 2 (DEFAULT ON, CAN DISABLE)**: Advanced patterns, performance, documentation
3. **Tier 3 (OPT-IN)**: Enterprise patterns, complex architecture, full DevOps

**How to Enforce:** Integrate into existing BuildRunner systems:
- Quality Gates (enforce Tier 1, warn on Tier 2)
- Gap Analyzer (detect violations, suggest fixes)
- Spec Generator (embed patterns in generated specs)
- Pre-commit Hooks (block violations before commit)
- Build Orchestrator (verify compliance during builds)

---

## Analysis: What Should Be Built In?

### ✅ TIER 1: Always Enforced (Non-Negotiable)

**Rationale:** These prevent security incidents, data loss, and critical bugs. No project should skip these.

#### 1. Security Fundamentals
- **Secret Detection** (ALREADY PLANNED - Build 4E)
  - Pre-commit hooks block commits with API keys
  - Quality gate fails if secrets detected
  - Auto-mask secrets in CLI output
  - Scan git history for past leaks

- **Input Validation** (NEW)
  - Every user input must be validated with Zod/similar
  - Quality gate checks for unvalidated inputs
  - Gap analyzer detects missing validation

- **SQL Injection Prevention** (NEW)
  - Enforce parameterized queries (no string concatenation)
  - Quality gate detects raw SQL with user input
  - Template generates ORM usage by default

- **XSS Prevention** (NEW)
  - Content Security Policy headers required
  - Sanitize user input before storage
  - Escape output when rendering

#### 2. Code Quality Basics
- **Linting & Formatting** (NEW)
  - ESLint/Prettier (JS/TS) or Black/Flake8 (Python) required
  - Auto-configure on `br init`
  - Pre-commit hook runs linter
  - Quality gate fails if linting errors

- **Type Safety** (NEW)
  - TypeScript strict mode enforced for TS projects
  - Python type hints required (checked with mypy)
  - Quality gate checks type coverage

- **Error Handling** (NEW)
  - Custom error hierarchy pattern enforced
  - Gap analyzer detects unhandled errors
  - Template includes error wrapper

#### 3. Testing Minimums
- **Coverage Thresholds** (ENHANCE EXISTING)
  - Minimum 70% unit test coverage (currently 80%+ in BR3)
  - Quality gate fails below threshold
  - Gap analyzer suggests untested code

- **Test Structure** (NEW)
  - Test pyramid enforced: 70% unit, 20% integration, 10% e2e
  - Quality gate warns if imbalanced
  - Template generates test structure

#### 4. Version Control
- **Git Best Practices** (NEW)
  - .gitignore for common patterns (.env, node_modules, dist/)
  - Pre-commit hooks for linting + secret detection
  - Commit message format validation

---

### 🟡 TIER 2: Default On, Can Disable (Recommended)

**Rationale:** These are best practices that improve code quality and maintainability, but some projects may have valid reasons to skip.

#### 5. Advanced Code Quality
- **Function Complexity Limits** (NEW)
  - Max function length: 50 lines (configurable)
  - Max cyclomatic complexity: 10
  - Quality gate warns on violations
  - User can disable via `.buildrunner/config.yaml`

- **Code Documentation** (NEW)
  - JSDoc/TSDoc required for public APIs
  - Gap analyzer detects undocumented functions
  - Quality gate warns (not fails)

#### 6. Database Best Practices
- **Migration Management** (NEW)
  - Version-controlled migrations required
  - Template generates migration structure
  - Quality gate checks for migration files

- **Query Optimization** (NEW)
  - Gap analyzer detects missing indexes
  - Warns on N+1 query patterns
  - Suggests optimization opportunities

#### 7. Performance Standards
- **Response Time Targets** (NEW)
  - API endpoints should respond < 500ms (p95)
  - Quality gate warns if exceeded (load testing)
  - Gap analyzer suggests caching opportunities

- **Caching Strategy** (NEW)
  - Template includes Redis/cache setup
  - Gap analyzer detects cacheable queries
  - Suggests cache-aside pattern

#### 8. API Design Standards
- **Consistent Response Format** (NEW)
  - Enforce standard API response structure
  - Template generates response wrappers
  - Quality gate checks for deviations

- **API Documentation** (NEW)
  - OpenAPI/Swagger spec auto-generated
  - Quality gate checks for missing docs
  - Gap analyzer suggests doc improvements

---

### 🔵 TIER 3: Opt-In (Enterprise/Advanced)

**Rationale:** These are valuable for large/complex projects but overkill for small projects or MVPs.

#### 9. Architecture Patterns
- **Clean Architecture** (OPT-IN)
  - User selects architecture during `br init`
  - Template generates folder structure
  - Gap analyzer validates layer separation

- **Microservices Support** (OPT-IN)
  - User enables via config
  - Template generates service structure
  - Quality gate checks service boundaries

#### 10. DevOps & Infrastructure
- **Docker Configuration** (OPT-IN)
  - Generate Dockerfile on request
  - Include docker-compose for local dev
  - CI/CD pipeline integration

- **Infrastructure as Code** (OPT-IN)
  - Terraform templates available
  - User selects cloud provider
  - Generate IaC during build

#### 11. Observability
- **Distributed Tracing** (OPT-IN)
  - OpenTelemetry integration
  - User enables if needed
  - Template includes setup

- **Advanced Monitoring** (OPT-IN)
  - Prometheus/Grafana dashboards
  - Custom alerts configuration
  - User-configurable thresholds

---

## How to Integrate into BuildRunner3

### 1. Configuration System

**`.buildrunner/config.yaml` additions:**

```yaml
# Best Practices Configuration
quality:
  tier1:
    enabled: true  # Cannot be disabled
    secret_detection: true
    input_validation: true
    sql_injection_prevention: true
    linting: true
    min_test_coverage: 70

  tier2:
    enabled: true  # Can be disabled
    max_function_lines: 50
    max_complexity: 10
    api_documentation: true
    database_migrations: true
    response_time_target_ms: 500

  tier3:
    clean_architecture: false
    microservices: false
    docker: false
    terraform: false
    distributed_tracing: false

# Override specific rules
overrides:
  max_function_lines: 75  # Increase limit
  min_test_coverage: 60   # Lower for MVP
```

### 2. Quality Gate Integration

**Enhance `core/quality/quality_gate.py`:**

```python
class QualityGate:
    def check(self) -> QualityResult:
        results = []

        # TIER 1 - Always enforced (FAIL on violation)
        results.append(self.check_secret_detection())      # Build 4E
        results.append(self.check_input_validation())      # NEW
        results.append(self.check_sql_injection())         # NEW
        results.append(self.check_linting())               # NEW
        results.append(self.check_test_coverage())         # EXISTING

        # TIER 2 - Default on (WARN on violation)
        if config.tier2_enabled:
            results.append(self.check_code_complexity())   # NEW
            results.append(self.check_api_docs())          # NEW
            results.append(self.check_migrations())        # NEW

        # TIER 3 - Opt-in (SUGGEST improvements)
        if config.tier3_clean_architecture:
            results.append(self.check_architecture())      # NEW

        return self.aggregate_results(results)
```

### 3. Gap Analyzer Integration

**Enhance `core/gaps/gap_analyzer.py`:**

```python
class GapAnalyzer:
    def analyze(self) -> List[Gap]:
        gaps = []

        # Security gaps (TIER 1)
        gaps.extend(self.analyze_security_gaps())
        gaps.extend(self.analyze_unvalidated_inputs())
        gaps.extend(self.analyze_sql_injection_risk())

        # Code quality gaps (TIER 2)
        gaps.extend(self.analyze_complexity_violations())
        gaps.extend(self.analyze_missing_docs())
        gaps.extend(self.analyze_missing_tests())

        # Performance gaps (TIER 2)
        gaps.extend(self.analyze_missing_indexes())
        gaps.extend(self.analyze_n_plus_one_queries())

        # Architecture gaps (TIER 3, if enabled)
        if config.tier3_clean_architecture:
            gaps.extend(self.analyze_layer_violations())

        return self.prioritize_gaps(gaps)
```

### 4. Spec Generation Templates

**Enhance `core/spec/spec_generator.py`:**

```python
class SpecGenerator:
    def generate_feature_spec(self, feature: Feature) -> str:
        spec = f"# Feature: {feature.name}\n\n"

        # Embed best practices in spec
        spec += "## Implementation Requirements\n\n"

        # TIER 1 (always included)
        spec += "### Security (REQUIRED)\n"
        spec += "- [ ] All user inputs validated with Zod schema\n"
        spec += "- [ ] No API keys in code (use environment variables)\n"
        spec += "- [ ] Parameterized queries only (no SQL concatenation)\n"
        spec += "- [ ] XSS prevention (CSP headers, sanitize input)\n\n"

        spec += "### Code Quality (REQUIRED)\n"
        spec += "- [ ] ESLint/Prettier configured and passing\n"
        spec += "- [ ] TypeScript strict mode enabled\n"
        spec += "- [ ] Error handling with custom error classes\n\n"

        spec += "### Testing (REQUIRED)\n"
        spec += f"- [ ] Unit test coverage ≥ {config.min_coverage}%\n"
        spec += "- [ ] Integration tests for critical flows\n\n"

        # TIER 2 (if enabled)
        if config.tier2_enabled:
            spec += "### Best Practices (RECOMMENDED)\n"
            spec += f"- [ ] Functions under {config.max_function_lines} lines\n"
            spec += f"- [ ] Complexity under {config.max_complexity}\n"
            spec += "- [ ] API endpoints documented with OpenAPI\n"
            spec += "- [ ] Database migrations version-controlled\n\n"

        # TIER 3 (if enabled)
        if config.tier3_clean_architecture:
            spec += "### Architecture (ADVANCED)\n"
            spec += "- [ ] Follow Clean Architecture layers\n"
            spec += "- [ ] Domain logic in domain layer only\n"
            spec += "- [ ] Infrastructure in infrastructure layer\n\n"

        return spec
```

### 5. Pre-Commit Hook System

**New: `core/hooks/best_practices_hook.py`:**

```python
class BestPracticesHook:
    """Pre-commit hook to enforce best practices"""

    def run(self) -> HookResult:
        violations = []

        # TIER 1 - Block commit on violation
        violations.extend(self.check_secrets_in_staged())
        violations.extend(self.check_linting_errors())
        violations.extend(self.check_type_errors())

        if violations:
            return HookResult(
                passed=False,
                message=f"❌ {len(violations)} violations found",
                violations=violations
            )

        # TIER 2 - Warn but allow commit
        warnings = []
        if config.tier2_enabled:
            warnings.extend(self.check_complexity_warnings())
            warnings.extend(self.check_missing_docs())

        if warnings:
            return HookResult(
                passed=True,
                message=f"⚠️  {len(warnings)} warnings (commit allowed)",
                warnings=warnings
            )

        return HookResult(passed=True, message="✅ All checks passed")
```

### 6. CLI Commands

**New commands:**

```bash
# Check best practices compliance
br quality check --tier all            # Check all tiers
br quality check --tier 1              # Only tier 1 (required)
br quality check --strict              # Fail on warnings

# Analyze gaps
br gaps analyze --category security    # Security gaps only
br gaps analyze --category performance # Performance gaps only
br gaps analyze --fix                  # Auto-fix where possible

# Configure best practices
br config set quality.tier2.enabled false      # Disable tier 2
br config set quality.max_function_lines 100   # Override limit

# Generate compliance report
br report best-practices                # Full compliance report
br report best-practices --format pdf   # PDF report
```

---

## Implementation Roadmap

### Phase 1: Foundation (Build 4E - Current)
- ✅ Secret detection (already planned)
- 🆕 Configuration system for tiers
- 🆕 Pre-commit hook framework
- 🆕 Basic linting integration

### Phase 2: Core Enforcement (Build 4F)
- 🆕 Input validation checks
- 🆕 SQL injection detection
- 🆕 Type safety validation
- 🆕 Error handling patterns
- 🆕 Quality gate tier system

### Phase 3: Advanced Patterns (Build 4G)
- 🆕 Code complexity analysis
- 🆕 API documentation generation
- 🆕 Database migration management
- 🆕 Performance analysis
- 🆕 Caching recommendations

### Phase 4: Enterprise Features (Build 4H)
- 🆕 Clean Architecture templates
- 🆕 Microservices support
- 🆕 Docker/IaC generation
- 🆕 Distributed tracing setup
- 🆕 Full DevOps pipeline

---

## Benefits of This Approach

### 1. Progressive Enhancement
- Small projects get essential security/quality (Tier 1)
- Growing projects adopt best practices (Tier 2)
- Enterprise projects get full patterns (Tier 3)

### 2. Learning Path
- Developers learn best practices through enforcement
- Warnings educate without blocking progress
- Gap analyzer suggests improvements

### 3. Consistency
- All BuildRunner projects follow same core standards
- Easy to onboard new developers
- Reduced code review burden

### 4. Flexibility
- Teams can disable practices that don't fit
- Override limits for specific needs
- Opt-in to advanced features

### 5. Automation
- Pre-commit hooks prevent issues early
- Quality gates catch violations before merge
- Gap analyzer finds issues proactively

---

## Configuration Example

**Small MVP Project:**
```yaml
quality:
  tier1:
    enabled: true
    min_test_coverage: 60  # Lower for MVP
  tier2:
    enabled: false  # Skip for speed
  tier3:
    enabled: false
```

**Production SaaS:**
```yaml
quality:
  tier1:
    enabled: true
    min_test_coverage: 80
  tier2:
    enabled: true
    api_documentation: true
    database_migrations: true
  tier3:
    clean_architecture: true
    docker: true
    terraform: true
    distributed_tracing: true
```

---

## Recommendation Summary

**YES - Build these into BuildRunner3:**

1. **Always Enforce (Tier 1):**
   - Secret detection ✅ (Build 4E)
   - Input validation 🆕
   - SQL injection prevention 🆕
   - Linting & formatting 🆕
   - Type safety 🆕
   - Error handling patterns 🆕
   - Minimum test coverage 🆕

2. **Default On (Tier 2):**
   - Code complexity limits 🆕
   - API documentation 🆕
   - Database migrations 🆕
   - Performance targets 🆕
   - Caching patterns 🆕

3. **Opt-In (Tier 3):**
   - Architecture patterns 🆕
   - Microservices support 🆕
   - Docker/IaC generation 🆕
   - Advanced monitoring 🆕

**How to Ensure Usage:**
- Quality gates FAIL on Tier 1 violations
- Quality gates WARN on Tier 2 violations
- Gap analyzer SUGGESTS Tier 3 improvements
- Pre-commit hooks BLOCK Tier 1 violations
- Spec generator EMBEDS requirements in feature specs
- CLI commands provide compliance reports

**Next Steps:**
1. Update Build 4E spec to include Tier 1 foundations
2. Create configuration schema for tiers
3. Enhance quality gate system
4. Implement pre-commit hook framework
5. Add best practices to spec templates

---

**Bottom Line:** BuildRunner3 should enforce core best practices (security, quality, testing) while offering progressive enhancement for advanced patterns. This ensures all projects are secure and maintainable while allowing flexibility for different project needs.
