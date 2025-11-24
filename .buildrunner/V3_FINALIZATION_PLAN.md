# BuildRunner 3.0 Finalization Plan

**Date:** 2025-11-24
**Status:** 2 features incomplete, finalization needed
**Timeline:** 5-7 days to complete

---

## Executive Summary

BR3 is **60% complete** relative to original vision, but the completed portions are **production-ready**. This plan finalizes the 2 incomplete features to achieve **v3.1.0 feature-complete** status.

**Current State:**
- ✅ 9 systems fully complete (100%)
- ✅ 3 systems nearly complete (95%)
- 🟡 2 systems incomplete (70-80%)
- ❌ 8 features deferred to v4.0

---

## Feature 1: Auto-Debug System (70% → 100%)

### Current Status
**What Works:**
- ✅ Basic logging with `./clog` wrapper
- ✅ Error detection and extraction
- ✅ Debug session tracking
- ✅ Interactive debug shell

**What's Missing:**
- ❌ Smart retry suggestions
- ❌ Cross-session failure analysis
- ❌ Background test runner daemon (deferred to v3.2)

### Implementation Plan (3-4 Days)

#### Day 1-2: Smart Retry Suggestions
**Files:** `core/auto_debug.py`, `cli/autodebug_commands.py`

```python
# core/auto_debug.py - Add retry analyzer
class RetryAnalyzer:
    """Analyze failures and suggest intelligent retry strategies"""

    PATTERNS = {
        'timeout': {
            'detection': r'(timeout|timed out|deadline exceeded)',
            'strategy': {
                'increase_timeout': True,
                'exponential_backoff': True,
                'max_retries': 3
            }
        },
        'import_error': {
            'detection': r'(ModuleNotFoundError|ImportError|Cannot find module)',
            'strategy': {
                'check_dependencies': True,
                'install_missing': True,
                'verify_paths': True
            }
        },
        'type_error': {
            'detection': r'(TypeError|type error|expected .+ got)',
            'strategy': {
                'run_type_checker': True,
                'suggest_type_hints': True
            }
        },
        'network_error': {
            'detection': r'(ConnectionError|NetworkError|ECONNREFUSED)',
            'strategy': {
                'retry_with_backoff': True,
                'check_connectivity': True,
                'max_retries': 5
            }
        }
    }

    def analyze_failure(self, error_log: str, context: dict) -> RetryStrategy:
        """
        Analyze error log and return actionable retry strategy

        Args:
            error_log: Full error output
            context: {command, exit_code, working_dir, env}

        Returns:
            RetryStrategy with specific actions to take
        """
        for pattern_type, config in self.PATTERNS.items():
            if re.search(config['detection'], error_log, re.IGNORECASE):
                return RetryStrategy(
                    type=pattern_type,
                    actions=config['strategy'],
                    confidence=self._calculate_confidence(error_log, config),
                    explanation=self._generate_explanation(pattern_type, context)
                )

        # No match - generic retry
        return RetryStrategy(
            type='generic',
            actions={'retry_as_is': True},
            confidence=0.3,
            explanation="No specific pattern detected. Try running again."
        )

    def suggest_fix_command(self, strategy: RetryStrategy, context: dict) -> str:
        """Generate specific fix command based on strategy"""
        if strategy.type == 'import_error':
            return f"cd {context['working_dir']} && npm install"  # or pip install
        elif strategy.type == 'timeout':
            return f"{context['command']} --timeout 60"
        elif strategy.type == 'type_error':
            return "npm run typecheck"  # or mypy .
        else:
            return context['command']  # retry as-is
```

**CLI Integration:**
```python
# cli/autodebug_commands.py
@autodebug.command()
def retry(
    session_id: str = typer.Option(None, help="Session to retry"),
    auto_fix: bool = typer.Option(False, help="Apply suggested fixes automatically")
):
    """
    Analyze last failure and suggest intelligent retry strategy

    Example:
        br autodebug retry
        br autodebug retry --session-id abc123 --auto-fix
    """
    analyzer = RetryAnalyzer()

    # Load last failed session
    session = DebugSession.load_latest() if not session_id else DebugSession.load(session_id)

    if not session or not session.has_failures():
        typer.echo("No failures to analyze")
        return

    # Analyze last failure
    last_error = session.get_last_error()
    strategy = analyzer.analyze_failure(last_error.log, last_error.context)

    # Display strategy
    typer.echo(f"\n🔍 Failure Analysis: {strategy.type}")
    typer.echo(f"📊 Confidence: {strategy.confidence * 100:.0f}%")
    typer.echo(f"💡 Explanation: {strategy.explanation}\n")
    typer.echo(f"🛠️  Suggested Actions:")
    for action, enabled in strategy.actions.items():
        if enabled:
            typer.echo(f"   ✓ {action.replace('_', ' ').title()}")

    # Show fix command
    fix_cmd = analyzer.suggest_fix_command(strategy, last_error.context)
    typer.echo(f"\n▶ Suggested Command:\n   {fix_cmd}\n")

    if auto_fix:
        typer.echo("🚀 Applying fix...")
        result = subprocess.run(fix_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            typer.echo("✅ Fix applied successfully")
        else:
            typer.echo(f"❌ Fix failed: {result.stderr}")
```

#### Day 3: Cross-Session Failure Analysis
**Files:** `core/auto_debug.py`

```python
class SessionAnalyzer:
    """Analyze patterns across multiple debug sessions"""

    def analyze_project_patterns(self, project_path: Path) -> ProjectInsights:
        """
        Analyze all debug sessions for a project

        Returns:
            ProjectInsights with hot spots, trends, success rates
        """
        sessions_dir = project_path / '.buildrunner/debug-sessions'
        sessions = self._load_all_sessions(sessions_dir)

        return ProjectInsights(
            hot_spots=self._find_hot_spots(sessions),  # Files/commands that fail often
            error_trends=self._analyze_trends(sessions),  # Error types over time
            success_rates=self._calculate_rates(sessions),  # Success % by file/command
            recommendations=self._generate_recommendations(sessions)
        )

    def _find_hot_spots(self, sessions: List[DebugSession]) -> List[HotSpot]:
        """Find files/commands that fail frequently"""
        failure_counts = defaultdict(int)

        for session in sessions:
            for error in session.errors:
                # Track by file
                if error.file:
                    failure_counts[f"file:{error.file}"] += 1
                # Track by command
                if error.command:
                    failure_counts[f"cmd:{error.command}"] += 1

        # Return top 10 hot spots
        return [
            HotSpot(
                location=key.split(':')[1],
                type=key.split(':')[0],
                failure_count=count,
                severity='high' if count > 10 else 'medium' if count > 5 else 'low'
            )
            for key, count in sorted(failure_counts.items(), key=lambda x: -x[1])[:10]
        ]

    def _analyze_trends(self, sessions: List[DebugSession]) -> TrendReport:
        """Analyze error trends over time"""
        # Group by week
        weekly_errors = defaultdict(lambda: defaultdict(int))

        for session in sessions:
            week = session.timestamp.strftime('%Y-W%W')
            for error in session.errors:
                error_type = self._classify_error(error.log)
                weekly_errors[week][error_type] += 1

        return TrendReport(
            weekly_breakdown=dict(weekly_errors),
            most_common_type=self._find_most_common(weekly_errors),
            trend_direction='improving' if self._is_improving(weekly_errors) else 'worsening'
        )
```

**CLI Command:**
```python
@autodebug.command()
def history():
    """Analyze debug history and show patterns"""
    analyzer = SessionAnalyzer()
    insights = analyzer.analyze_project_patterns(Path.cwd())

    typer.echo("\n📊 Debug History Analysis\n")

    # Hot spots
    typer.echo("🔥 Failure Hot Spots:")
    for spot in insights.hot_spots:
        icon = "🔴" if spot.severity == 'high' else "🟡"
        typer.echo(f"   {icon} {spot.location} ({spot.failure_count} failures)")

    # Trends
    typer.echo(f"\n📈 Error Trends: {insights.error_trends.trend_direction}")
    typer.echo(f"   Most Common: {insights.error_trends.most_common_type}")

    # Recommendations
    typer.echo("\n💡 Recommendations:")
    for rec in insights.recommendations:
        typer.echo(f"   • {rec}")
```

#### Day 4: Testing & Integration
- Write 20+ unit tests for `RetryAnalyzer` and `SessionAnalyzer`
- Add integration tests for CLI commands
- Update documentation
- Test on real projects (Synapse, sales-assistant, BR3)

**Test Coverage Target:** 85%+

---

## Feature 2: Design System + Synapse Integration (80% → 100%)

### Current Status
**What Works:**
- ✅ Design system framework
- ✅ 9 industry profiles (manual)
- ✅ Profile merging logic
- ✅ `br design profile` command (partial)

**What's Missing:**
- ❌ 139+ industry profiles (claimed 148 total)
- ❌ Synapse DB integration
- ❌ `br design generate` command
- ❌ Tailwind config generation

### Key Insight: Use Synapse Database
**User confirmed:** Industry profiles already exist in Synapse DB. We don't need to build 139 profiles—just connect to the existing data.

### Implementation Plan (2-3 Days)

#### Day 1: Synapse DB Connector
**Files:** `core/design_system/synapse_connector.py`

```python
# core/design_system/synapse_connector.py
from supabase import create_client, Client
from typing import Optional, List
import os

class SynapseIndustryConnector:
    """
    Connect to Synapse database for industry profiles
    Credentials from Synapse .env file
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        # Load from environment or Synapse .env
        self.url = supabase_url or os.getenv('SUPABASE_URL')
        self.key = supabase_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not self.url or not self.key:
            raise ValueError(
                "Synapse credentials not found. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment "
                "or copy from /Users/byronhudson/Projects/Synapse/.env"
            )

        self.client: Client = create_client(self.url, self.key)

    def get_industry_profile(self, industry_name: str) -> Optional[dict]:
        """
        Fetch industry profile from Synapse

        Args:
            industry_name: Industry name (e.g., "Healthcare", "E-commerce")

        Returns:
            Industry profile with design data, or None if not found
        """
        try:
            result = self.client.table('industry_profiles')\
                .select('*')\
                .eq('industry_name', industry_name)\
                .single()\
                .execute()

            return self._transform_to_br3_format(result.data)
        except Exception as e:
            # Log error but don't crash
            print(f"Warning: Could not fetch {industry_name} from Synapse: {e}")
            return None

    def list_all_industries(self) -> List[str]:
        """Get list of all available industries"""
        result = self.client.table('industry_profiles')\
            .select('industry_name')\
            .execute()

        return sorted([row['industry_name'] for row in result.data])

    def search_industries(self, query: str) -> List[str]:
        """Search industries by keyword"""
        result = self.client.table('industry_profiles')\
            .select('industry_name')\
            .ilike('industry_name', f'%{query}%')\
            .execute()

        return [row['industry_name'] for row in result.data]

    def _transform_to_br3_format(self, synapse_data: dict) -> dict:
        """
        Transform Synapse industry profile to BR3 design system format

        Synapse fields → BR3 fields:
        - psychology_data → design_psychology
        - design_patterns → ui_patterns
        - color_psychology → color_scheme
        - typography_rules → typography
        """
        return {
            'industry': synapse_data.get('industry_name'),
            'naics_code': synapse_data.get('naics_code'),
            'design_psychology': synapse_data.get('psychology_data', {}),
            'ui_patterns': synapse_data.get('design_patterns', {}),
            'color_scheme': synapse_data.get('color_psychology', {}),
            'typography': synapse_data.get('typography_rules', {}),
            'target_audience': synapse_data.get('target_demographics', {}),
            'trust_signals': synapse_data.get('trust_factors', []),
            'conversion_patterns': synapse_data.get('conversion_psychology', {})
        }
```

#### Day 2: Update Design Commands
**Files:** `cli/design_commands.py`

```python
# cli/design_commands.py
@design.command()
def profile(
    industry: str = typer.Argument(..., help="Industry name"),
    output: str = typer.Option('text', help="Output format: text, json, yaml")
):
    """
    Get industry design profile from Synapse database

    Example:
        br design profile Healthcare
        br design profile "E-commerce" --output json
    """
    try:
        connector = SynapseIndustryConnector()
        profile = connector.get_industry_profile(industry)

        if not profile:
            typer.echo(f"❌ Industry '{industry}' not found in Synapse database")
            typer.echo("\n💡 Search for available industries:")
            typer.echo(f"   br design search {industry}")
            raise typer.Exit(1)

        # Display profile
        if output == 'json':
            typer.echo(json.dumps(profile, indent=2))
        elif output == 'yaml':
            typer.echo(yaml.dump(profile, default_flow_style=False))
        else:
            _display_profile_text(profile)

    except ValueError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

@design.command()
def search(query: str = typer.Argument(..., help="Search term")):
    """
    Search available industries

    Example:
        br design search health
        br design search retail
    """
    connector = SynapseIndustryConnector()
    results = connector.search_industries(query)

    if not results:
        typer.echo(f"No industries found matching '{query}'")
    else:
        typer.echo(f"\n🔍 Found {len(results)} industries:\n")
        for industry in results:
            typer.echo(f"   • {industry}")
        typer.echo(f"\n💡 Get profile: br design profile \"{results[0]}\"")

@design.command()
def list():
    """List all available industries"""
    connector = SynapseIndustryConnector()
    industries = connector.list_all_industries()

    typer.echo(f"\n📋 {len(industries)} Industries Available:\n")
    for industry in industries:
        typer.echo(f"   • {industry}")

@design.command()
def generate(
    industry: str = typer.Argument(..., help="Industry name"),
    output_dir: Path = typer.Option('.', help="Output directory"),
    framework: str = typer.Option('tailwind', help="CSS framework: tailwind, mui, chakra")
):
    """
    Generate design system config from industry profile

    Example:
        br design generate Healthcare
        br design generate "E-commerce" --framework tailwind --output-dir ./design
    """
    connector = SynapseIndustryConnector()
    profile = connector.get_industry_profile(industry)

    if not profile:
        typer.echo(f"❌ Industry '{industry}' not found")
        raise typer.Exit(1)

    generator = DesignGenerator(framework)
    config = generator.generate_config(profile)

    # Write config files
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    if framework == 'tailwind':
        config_file = output_dir / 'tailwind.config.js'
        config_file.write_text(config)
        typer.echo(f"✅ Generated: {config_file}")

    typer.echo(f"\n🎨 Design system generated for {industry}")
```

#### Day 3: Design Config Generator
**Files:** `core/design_system/generator.py`

```python
class DesignGenerator:
    """Generate framework-specific design configs from industry profiles"""

    def __init__(self, framework: str = 'tailwind'):
        self.framework = framework

    def generate_config(self, profile: dict) -> str:
        """Generate config file based on framework"""
        if self.framework == 'tailwind':
            return self._generate_tailwind(profile)
        elif self.framework == 'mui':
            return self._generate_mui(profile)
        else:
            raise ValueError(f"Unsupported framework: {self.framework}")

    def _generate_tailwind(self, profile: dict) -> str:
        """Generate Tailwind config from industry profile"""
        colors = profile.get('color_scheme', {})
        typography = profile.get('typography', {})

        return f"""/** @type {{import('tailwindcss').Config}} */
module.exports = {{
  content: ['./src/**/*.{{js,jsx,ts,tsx}}'],
  theme: {{
    extend: {{
      colors: {json.dumps(colors, indent=8)},
      fontFamily: {json.dumps(typography.get('fonts', {}), indent=8)},
      fontSize: {json.dumps(typography.get('scales', {}), indent=8)},
      // Generated from Synapse industry profile: {profile['industry']}
      // NAICS: {profile.get('naics_code', 'N/A')}
    }},
  }},
  plugins: [],
}}
"""
```

**Testing:**
- Test Synapse connection with real credentials
- Verify 148+ industries are accessible
- Test all CLI commands
- Generate sample Tailwind configs for 5 industries

---

## Timeline Summary

| Feature | Days | Status |
|---------|------|--------|
| Auto-Debug: Smart Retry | 2 | 🟡 In progress |
| Auto-Debug: Cross-Session Analysis | 1 | ⏳ Pending |
| Auto-Debug: Testing | 1 | ⏳ Pending |
| Design System: Synapse Connector | 1 | ⏳ Pending |
| Design System: CLI Updates | 1 | ⏳ Pending |
| Design System: Config Generator | 1 | ⏳ Pending |
| **Total** | **7 days** | |

---

## V4.0 Roadmap: Deferred Features

The following 8 features from the original BUILD_PLAN.md are **deferred to v4.0** (20-30 weeks):

### 1. AI Code Review & Refactoring System
**Description:** Automated code review with refactoring suggestions
**Scope:** AI-powered analysis, automated refactoring proposals, style enforcement
**Effort:** 3-4 weeks

### 2. Environment & Dependency Intelligence
**Description:** Smart dependency management and environment detection
**Scope:** Auto-detect missing deps, version conflict resolution, environment setup
**Effort:** 2-3 weeks

### 3. Predictive Intelligence System
**Description:** Machine learning for build time prediction and optimization
**Scope:** Historical analysis, prediction models, optimization recommendations
**Effort:** 4-5 weeks

### 4. Human-Readable Reporting Suite
**Description:** Beautiful reports for stakeholders (non-technical audiences)
**Scope:** PDF/HTML reports, executive dashboards, progress visualizations
**Effort:** 2-3 weeks

### 5. Build Intelligence Enhancements
**Description:** Advanced build optimization and caching
**Scope:** Incremental builds, smart caching, parallel compilation
**Effort:** 3-4 weeks

### 6. Natural Language Programming Interface
**Description:** Code via natural language (full NLP interface)
**Scope:** NL → Code generation, conversational programming, AI pair programming
**Effort:** 4-5 weeks

### 7. Learning & Knowledge System
**Description:** System that learns from your codebase and patterns
**Scope:** Pattern recognition, custom recommendations, team knowledge base
**Effort:** 3-4 weeks

### 8. Proactive Monitoring & Alerts
**Description:** 24/7 monitoring with intelligent alerting
**Scope:** Health checks, anomaly detection, Slack/email alerts, dashboards
**Effort:** 2-3 weeks

**Total Effort for V4 Features:** 23-31 weeks

These features represent the "AI-first" vision for BuildRunner and require substantial R&D.

---

## Success Criteria

### V3.1 Feature-Complete Definition
- ✅ All 14 tracked features at 100% completion
- ✅ Auto-debug: Smart retry + cross-session analysis working
- ✅ Design system: Synapse DB integration + 148+ profiles accessible
- ✅ Test coverage: 85%+ on all systems
- ✅ Documentation: Complete for all features
- ✅ Production validation: Tested on 3+ real projects

### Acceptance Tests
1. Run `br autodebug retry` on a failed command → Get intelligent retry suggestion
2. Run `br autodebug history` → See hot spots and patterns across sessions
3. Run `br design profile Healthcare` → Get profile from Synapse DB
4. Run `br design generate Healthcare` → Generate Tailwind config
5. Run `br design list` → See 148+ industries

---

## Next Steps

1. **Immediate:** Start Day 1 of Auto-Debug implementation
2. **Day 3:** Begin Synapse connector implementation
3. **Day 7:** Feature freeze, begin testing
4. **Day 8:** Update VERSION_3_ROADMAP.md with v3.1 completion
5. **Day 9:** Update BUILD_PLAN_V4.0.md with deferred features
6. **Day 10:** Release v3.1.0-complete

---

**End of Finalization Plan**
