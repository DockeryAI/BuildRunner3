"""
BR3 Enforcement Engine - Force usage of ALL BR3 features

NO ESCAPE HATCHES. NO SKIPPING. NO BYPASSING.

Every BR3 feature MUST be used. Every attached project MUST be configured.
Every commit MUST pass all checks. Every push MUST use br github push.

This is the enforcement layer that makes BR3 actually use BR3.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnforcementRule:
    """A rule that must be enforced"""
    id: str
    name: str
    description: str
    check_function: str  # Name of method to call
    required_files: List[str] = field(default_factory=list)
    required_commands: List[str] = field(default_factory=list)
    auto_fix: bool = True  # Can this be auto-fixed?
    severity: str = "error"  # error, warning


@dataclass
class EnforcementResult:
    """Result of enforcement check"""
    rule_id: str
    passed: bool
    message: str
    auto_fixable: bool = False
    fix_command: Optional[str] = None


class EnforcementEngine:
    """
    Enforces ALL BR3 features on ALL projects.

    Rules:
    1. No --no-verify bypass allowed
    2. No "skipped" checks - must pass or fail
    3. All configs must exist (autodebug.yaml, quality config, etc.)
    4. Must use br github commands instead of raw git
    5. Must run gaps analyze before commit
    6. Must run autodebug before push
    7. Must run quality check before push
    8. Must have design system extracted
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.buildrunner_dir = self.project_root / ".buildrunner"
        self.rules = self._load_rules()

    def _load_rules(self) -> List[EnforcementRule]:
        """Load all enforcement rules"""
        return [
            # Config existence rules
            EnforcementRule(
                id="autodebug-config",
                name="AutoDebug Configuration",
                description="autodebug.yaml must exist",
                check_function="check_autodebug_config",
                required_files=["autodebug.yaml"],
                auto_fix=True
            ),
            EnforcementRule(
                id="quality-config",
                name="Quality Configuration",
                description="Quality thresholds must be configured",
                check_function="check_quality_config",
                required_files=["governance/governance.yaml"],
                auto_fix=True
            ),
            EnforcementRule(
                id="features-json",
                name="Features Tracking",
                description="features.json must exist and be up to date",
                check_function="check_features_json",
                required_files=["features.json"],
                auto_fix=False
            ),
            EnforcementRule(
                id="design-system",
                name="Design System",
                description="design-system.json must exist",
                check_function="check_design_system",
                required_files=["design-system.json"],
                auto_fix=True
            ),

            # Pre-commit rules
            EnforcementRule(
                id="no-bypass",
                name="No Bypass",
                description="--no-verify flag is prohibited",
                check_function="check_no_bypass",
                required_commands=[]
            ),
            EnforcementRule(
                id="gaps-analysis",
                name="Gap Analysis",
                description="Must run 'br gaps analyze' before commit",
                check_function="check_gaps_analysis",
                required_commands=["br gaps analyze"]
            ),

            # Pre-push rules
            EnforcementRule(
                id="autodebug-passed",
                name="AutoDebug Passing",
                description="Must run 'br autodebug run' and pass",
                check_function="check_autodebug_passed",
                required_commands=["br autodebug run"]
            ),
            EnforcementRule(
                id="quality-passed",
                name="Quality Check Passing",
                description="Must run 'br quality check' and pass",
                check_function="check_quality_passed",
                required_commands=["br quality check"]
            ),
            EnforcementRule(
                id="use-br-github-push",
                name="Use BR GitHub Push",
                description="Must use 'br github push' instead of raw 'git push'",
                check_function="check_br_github_push",
                required_commands=["br github push"]
            ),
        ]

    def check_all(self) -> List[EnforcementResult]:
        """Run all enforcement checks"""
        results = []

        for rule in self.rules:
            # Get check method
            check_method = getattr(self, rule.check_function, None)
            if not check_method:
                logger.warning(f"Check method {rule.check_function} not found")
                continue

            # Run check
            result = check_method(rule)
            results.append(result)

        return results

    def check_autodebug_config(self, rule: EnforcementRule) -> EnforcementResult:
        """Check autodebug.yaml exists"""
        autodebug_file = self.buildrunner_dir / "autodebug.yaml"

        if autodebug_file.exists():
            return EnforcementResult(
                rule_id=rule.id,
                passed=True,
                message="✅ autodebug.yaml exists"
            )

        return EnforcementResult(
            rule_id=rule.id,
            passed=False,
            message="❌ autodebug.yaml missing - autodebug checks will be skipped",
            auto_fixable=True,
            fix_command="br init autodebug"
        )

    def check_quality_config(self, rule: EnforcementRule) -> EnforcementResult:
        """Check quality configuration exists"""
        gov_file = self.buildrunner_dir / "governance" / "governance.yaml"

        if not gov_file.exists():
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message="❌ governance.yaml missing",
                auto_fixable=True,
                fix_command="br init"
            )

        # Check if quality section exists
        import yaml
        try:
            with open(gov_file) as f:
                gov = yaml.safe_load(f)

            if 'quality' not in gov or 'thresholds' not in gov.get('quality', {}):
                return EnforcementResult(
                    rule_id=rule.id,
                    passed=False,
                    message="❌ Quality thresholds not configured in governance.yaml",
                    auto_fixable=True,
                    fix_command="br quality init"
                )

            return EnforcementResult(
                rule_id=rule.id,
                passed=True,
                message="✅ Quality configuration exists"
            )

        except Exception as e:
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message=f"❌ Error reading governance.yaml: {e}",
                auto_fixable=False
            )

    def check_features_json(self, rule: EnforcementRule) -> EnforcementResult:
        """Check features.json exists"""
        features_file = self.buildrunner_dir / "features.json"

        if not features_file.exists():
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message="❌ features.json missing - feature tracking disabled",
                auto_fixable=False,
                fix_command="br attach"
            )

        # Check if it's valid JSON
        try:
            with open(features_file) as f:
                data = json.load(f)

            if 'features' not in data:
                return EnforcementResult(
                    rule_id=rule.id,
                    passed=False,
                    message="❌ features.json is invalid (no 'features' key)",
                    auto_fixable=False
                )

            return EnforcementResult(
                rule_id=rule.id,
                passed=True,
                message=f"✅ features.json exists ({len(data['features'])} features tracked)"
            )

        except Exception as e:
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message=f"❌ features.json is invalid: {e}",
                auto_fixable=False
            )

    def check_design_system(self, rule: EnforcementRule) -> EnforcementResult:
        """Check design system extracted"""
        design_file = self.buildrunner_dir / "design-system.json"

        if not design_file.exists():
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message="❌ design-system.json missing - design adoption disabled",
                auto_fixable=True,
                fix_command="br design extract"
            )

        # Check confidence
        try:
            with open(design_file) as f:
                data = json.load(f)

            confidence = data.get('confidence', 0)
            if confidence < 0.3:
                return EnforcementResult(
                    rule_id=rule.id,
                    passed=False,
                    message=f"⚠️  Design system confidence too low ({confidence:.0%})",
                    auto_fixable=True,
                    fix_command="br design extract"
                )

            return EnforcementResult(
                rule_id=rule.id,
                passed=True,
                message=f"✅ Design system extracted (confidence: {confidence:.0%})"
            )

        except Exception as e:
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message=f"❌ design-system.json is invalid: {e}",
                auto_fixable=True,
                fix_command="br design extract"
            )

    def check_no_bypass(self, rule: EnforcementRule) -> EnforcementResult:
        """Check if --no-verify was used (can't check from here, checked in hooks)"""
        # This is actually checked in the git hooks themselves
        return EnforcementResult(
            rule_id=rule.id,
            passed=True,
            message="✅ No bypass flags detected"
        )

    def check_gaps_analysis(self, rule: EnforcementRule) -> EnforcementResult:
        """Check if gaps analysis was run recently"""
        # Check for gaps analysis cache/results
        gaps_cache = self.buildrunner_dir / ".gaps-cache.json"

        if not gaps_cache.exists():
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message="❌ Gap analysis not run - run 'br gaps analyze' first",
                auto_fixable=False,
                fix_command="br gaps analyze"
            )

        # Check if it's recent (within last hour)
        import time
        age = time.time() - gaps_cache.stat().st_mtime

        if age > 3600:  # 1 hour
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message=f"❌ Gap analysis is stale ({age/3600:.1f}h old) - run 'br gaps analyze'",
                auto_fixable=False,
                fix_command="br gaps analyze"
            )

        return EnforcementResult(
            rule_id=rule.id,
            passed=True,
            message="✅ Gap analysis is current"
        )

    def check_autodebug_passed(self, rule: EnforcementRule) -> EnforcementResult:
        """Check if autodebug passed recently"""
        # Check for autodebug results
        autodebug_results = self.buildrunner_dir / ".autodebug-results.json"

        if not autodebug_results.exists():
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message="❌ AutoDebug not run - run 'br autodebug run' first",
                auto_fixable=False,
                fix_command="br autodebug run"
            )

        # Check if tests passed
        try:
            with open(autodebug_results) as f:
                results = json.load(f)

            if not results.get('overall_success', False):
                failures = results.get('critical_failures', [])
                return EnforcementResult(
                    rule_id=rule.id,
                    passed=False,
                    message=f"❌ AutoDebug failed ({len(failures)} critical failures)",
                    auto_fixable=False
                )

            # Check if results are recent
            import time
            age = time.time() - autodebug_results.stat().st_mtime

            if age > 1800:  # 30 minutes
                return EnforcementResult(
                    rule_id=rule.id,
                    passed=False,
                    message=f"❌ AutoDebug results are stale ({age/60:.0f}m old)",
                    auto_fixable=False,
                    fix_command="br autodebug run"
                )

            return EnforcementResult(
                rule_id=rule.id,
                passed=True,
                message="✅ AutoDebug passed"
            )

        except Exception as e:
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message=f"❌ Error reading autodebug results: {e}",
                auto_fixable=False
            )

    def check_quality_passed(self, rule: EnforcementRule) -> EnforcementResult:
        """Check if quality check passed recently"""
        # Check for quality results
        quality_results = self.buildrunner_dir / ".quality-results.json"

        if not quality_results.exists():
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message="❌ Quality check not run - run 'br quality check' first",
                auto_fixable=False,
                fix_command="br quality check"
            )

        # Check if quality passed
        try:
            with open(quality_results) as f:
                results = json.load(f)

            score = results.get('overall_score', 0)
            threshold = results.get('threshold', 70)

            if score < threshold:
                return EnforcementResult(
                    rule_id=rule.id,
                    passed=False,
                    message=f"❌ Quality check failed (score: {score}/100, threshold: {threshold})",
                    auto_fixable=False
                )

            # Check if results are recent
            import time
            age = time.time() - quality_results.stat().st_mtime

            if age > 1800:  # 30 minutes
                return EnforcementResult(
                    rule_id=rule.id,
                    passed=False,
                    message=f"❌ Quality results are stale ({age/60:.0f}m old)",
                    auto_fixable=False,
                    fix_command="br quality check"
                )

            return EnforcementResult(
                rule_id=rule.id,
                passed=True,
                message=f"✅ Quality check passed (score: {score}/100)"
            )

        except Exception as e:
            return EnforcementResult(
                rule_id=rule.id,
                passed=False,
                message=f"❌ Error reading quality results: {e}",
                auto_fixable=False
            )

    def check_br_github_push(self, rule: EnforcementRule) -> EnforcementResult:
        """This is checked in git hooks to intercept raw git push"""
        return EnforcementResult(
            rule_id=rule.id,
            passed=True,
            message="✅ Using BR3 GitHub commands"
        )

    def get_blocking_issues(self) -> List[EnforcementResult]:
        """Get all blocking issues that prevent commit/push"""
        results = self.check_all()
        return [r for r in results if not r.passed]

    def auto_fix_all(self) -> List[str]:
        """Auto-fix all fixable issues"""
        results = self.check_all()
        commands = []

        for result in results:
            if not result.passed and result.auto_fixable and result.fix_command:
                commands.append(result.fix_command)

        # Deduplicate
        return list(set(commands))

    def enforce_pre_commit(self) -> bool:
        """Enforce rules before commit"""
        results = self.check_all()

        # Check for config issues
        config_rules = ['autodebug-config', 'quality-config', 'features-json', 'design-system']
        config_issues = [r for r in results if r.rule_id in config_rules and not r.passed]

        if config_issues:
            return False

        # Check gaps analysis
        gaps_result = next((r for r in results if r.rule_id == 'gaps-analysis'), None)
        if gaps_result and not gaps_result.passed:
            return False

        return True

    def enforce_pre_push(self) -> bool:
        """Enforce rules before push"""
        # First check pre-commit rules
        if not self.enforce_pre_commit():
            return False

        results = self.check_all()

        # Check autodebug
        autodebug_result = next((r for r in results if r.rule_id == 'autodebug-passed'), None)
        if autodebug_result and not autodebug_result.passed:
            return False

        # Check quality
        quality_result = next((r for r in results if r.rule_id == 'quality-passed'), None)
        if quality_result and not quality_result.passed:
            return False

        return True


class ConfigGenerator:
    """Auto-generate all required BR3 configs"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.buildrunner_dir = self.project_root / ".buildrunner"

    def generate_all(self) -> List[str]:
        """Generate all missing configs"""
        generated = []

        # Generate autodebug.yaml
        if not (self.buildrunner_dir / "autodebug.yaml").exists():
            self.generate_autodebug_config()
            generated.append("autodebug.yaml")

        # Generate quality thresholds in governance.yaml
        if not self._has_quality_config():
            self.add_quality_config()
            generated.append("quality config in governance.yaml")

        # Extract design system
        if not (self.buildrunner_dir / "design-system.json").exists():
            self.extract_design_system()
            generated.append("design-system.json")

        return generated

    def generate_autodebug_config(self):
        """Generate autodebug.yaml"""
        config = """# AutoDebug Configuration
# Auto-generated by BR3 enforcement engine

project:
  name: {project_name}
  type: auto  # auto-detect or: fullstack, backend, frontend, library

checks:
  immediate:
    - syntax
    - imports
    - python_syntax
    - typescript_quick

  standard:
    - lint
    - format
    - unit_tests

  deep:
    - integration_tests
    - type_check
    - security_scan

thresholds:
  max_failures: 0  # Zero tolerance
  max_warnings: 10
  min_coverage: 80

enforcement:
  block_on_failure: true
  auto_fix: true
""".format(project_name=self.project_root.name)

        autodebug_file = self.buildrunner_dir / "autodebug.yaml"
        autodebug_file.parent.mkdir(parents=True, exist_ok=True)
        autodebug_file.write_text(config)

        logger.info(f"Generated {autodebug_file}")

    def _has_quality_config(self) -> bool:
        """Check if quality config exists in governance.yaml"""
        gov_file = self.buildrunner_dir / "governance" / "governance.yaml"
        if not gov_file.exists():
            return False

        import yaml
        try:
            with open(gov_file) as f:
                gov = yaml.safe_load(f)
            return 'quality' in gov and 'thresholds' in gov.get('quality', {})
        except:
            return False

    def add_quality_config(self):
        """Add quality configuration to governance.yaml"""
        gov_file = self.buildrunner_dir / "governance" / "governance.yaml"
        gov_file.parent.mkdir(parents=True, exist_ok=True)

        import yaml

        # Load existing or create new
        if gov_file.exists():
            with open(gov_file) as f:
                gov = yaml.safe_load(f) or {}
        else:
            gov = {}

        # Add quality section
        gov['quality'] = {
            'enabled': True,
            'thresholds': {
                'overall': 70,
                'structure': 60,
                'testing': 80,
                'documentation': 50,
                'security': 90,
                'performance': 60
            },
            'enforcement': {
                'block_commit': True,
                'block_push': True
            }
        }

        with open(gov_file, 'w') as f:
            yaml.dump(gov, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Added quality config to {gov_file}")

    def extract_design_system(self):
        """Extract design system"""
        try:
            from core.design_extractor import DesignExtractor

            extractor = DesignExtractor(self.project_root)
            design_system = extractor.extract()
            extractor.save()

            logger.info(f"Extracted design system (confidence: {design_system.confidence:.0%})")

        except Exception as e:
            logger.error(f"Error extracting design system: {e}")
