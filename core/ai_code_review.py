"""
AI Code Review System using Claude API

Provides automated code review capabilities including:
- Git diff analysis
- Architecture compliance checking
- Code quality assessment
- Best practices validation
"""
import os
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from anthropic import AsyncAnthropic
import subprocess


class CodeReviewError(Exception):
    """Base exception for code review errors"""
    pass


class CodeReviewer:
    """
    AI-powered code reviewer using Claude Sonnet API

    Features:
    - Review git diffs with AI analysis
    - Check architectural compliance against PROJECT_SPEC.md
    - Identify code quality issues
    - Provide actionable improvement suggestions
    """

    def __init__(self, api_key: Optional[str] = None, project_root: Optional[Path] = None):
        """
        Initialize CodeReviewer

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            project_root: Root directory of the project (defaults to cwd)

        Raises:
            CodeReviewError: If API key not found
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise CodeReviewError("ANTHROPIC_API_KEY not found in environment")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"  # Latest Sonnet
        self.max_tokens = 4096
        self.project_root = Path(project_root) if project_root else Path.cwd()

    async def review_diff(
        self,
        diff: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Review a git diff using Claude AI

        Args:
            diff: Git diff string to review
            context: Optional context (file_path, commit_msg, etc.)

        Returns:
            Dict with:
                - summary: Overall assessment
                - issues: List of identified issues
                - suggestions: List of improvement suggestions
                - score: Quality score 0-100

        Raises:
            CodeReviewError: If review fails
        """
        if not diff or not diff.strip():
            return {
                "summary": "No changes to review",
                "issues": [],
                "suggestions": [],
                "score": 100
            }

        # Build prompt for Claude
        prompt = self._build_diff_review_prompt(diff, context)

        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse Claude's response
            response_text = message.content[0].text
            return self._parse_review_response(response_text)

        except Exception as e:
            raise CodeReviewError(f"Failed to review diff: {e}")

    async def analyze_architecture(
        self,
        code: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Analyze code against PROJECT_SPEC.md architecture

        Args:
            code: Source code to analyze
            file_path: Path to the file being analyzed

        Returns:
            Dict with:
                - compliant: bool (True if architecture compliant)
                - violations: List of architecture violations
                - recommendations: List of architectural improvements
                - spec_alignment: Compliance score 0-100

        Raises:
            CodeReviewError: If analysis fails
        """
        # Load PROJECT_SPEC.md
        spec_content = self._load_project_spec()

        # Build prompt for architecture analysis
        prompt = self._build_architecture_prompt(code, file_path, spec_content)

        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            return self._parse_architecture_response(response_text)

        except Exception as e:
            raise CodeReviewError(f"Failed to analyze architecture: {e}")

    async def review_file(
        self,
        file_path: str,
        check_architecture: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive review of a single file

        Args:
            file_path: Path to file to review
            check_architecture: Whether to check architectural compliance

        Returns:
            Dict with combined review and architecture analysis results

        Raises:
            CodeReviewError: If file review fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise CodeReviewError(f"File not found: {file_path}")

        # Read file content
        try:
            code = file_path.read_text()
        except Exception as e:
            raise CodeReviewError(f"Failed to read file {file_path}: {e}")

        # Get git diff for the file
        diff = self._get_file_diff(str(file_path))

        # Review diff
        review_result = await self.review_diff(
            diff,
            context={"file_path": str(file_path)}
        )

        # Analyze architecture if requested
        architecture_result = {}
        if check_architecture:
            architecture_result = await self.analyze_architecture(code, str(file_path))

        return {
            "file": str(file_path),
            "review": review_result,
            "architecture": architecture_result
        }

    def _build_diff_review_prompt(self, diff: str, context: Optional[Dict] = None) -> str:
        """Build prompt for diff review"""
        context_str = ""
        if context:
            if "file_path" in context:
                context_str += f"\nFile: {context['file_path']}"
            if "commit_msg" in context:
                context_str += f"\nCommit Message: {context['commit_msg']}"

        return f"""Review the following git diff and provide a comprehensive code review.
{context_str}

Git Diff:
```
{diff}
```

Provide your review in the following format:

SUMMARY: [Overall assessment of changes]

ISSUES:
- [Issue 1 if any]
- [Issue 2 if any]

SUGGESTIONS:
- [Suggestion 1]
- [Suggestion 2]

SCORE: [0-100 quality score]

Focus on:
- Code quality and readability
- Potential bugs or errors
- Performance implications
- Security vulnerabilities
- Best practices compliance
- Test coverage
"""

    def _build_architecture_prompt(self, code: str, file_path: str, spec: str) -> str:
        """Build prompt for architecture analysis"""
        return f"""Analyze this code file against the project's architectural specification.

File: {file_path}

PROJECT_SPEC.md:
```
{spec[:2000]}  # Truncate to first 2000 chars
```

Code:
```
{code[:3000]}  # Truncate to first 3000 chars
```

Analyze and provide:

COMPLIANCE: [YES/NO - Does code follow architectural patterns defined in spec?]

VIOLATIONS:
- [Violation 1 if any]
- [Violation 2 if any]

RECOMMENDATIONS:
- [Recommendation 1]
- [Recommendation 2]

ALIGNMENT_SCORE: [0-100 score for spec alignment]

Focus on:
- Layer violations (e.g., bypassing proper layers)
- Dependency inversions
- Architectural patterns (MVC, Repository, etc.)
- Separation of concerns
- Module boundaries
"""

    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's review response"""
        lines = response.strip().split("\n")

        summary = ""
        issues = []
        suggestions = []
        score = 85  # Default score

        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
                current_section = "summary"
            elif line.startswith("ISSUES:"):
                current_section = "issues"
            elif line.startswith("SUGGESTIONS:"):
                current_section = "suggestions"
            elif line.startswith("SCORE:"):
                try:
                    score = int(line.replace("SCORE:", "").strip())
                except ValueError:
                    score = 85
                current_section = None
            elif line.startswith("- ") and current_section == "issues":
                issues.append(line[2:])
            elif line.startswith("- ") and current_section == "suggestions":
                suggestions.append(line[2:])

        return {
            "summary": summary,
            "issues": issues,
            "suggestions": suggestions,
            "score": score
        }

    def _parse_architecture_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's architecture analysis response"""
        lines = response.strip().split("\n")

        compliant = True
        violations = []
        recommendations = []
        score = 90  # Default score

        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("COMPLIANCE:"):
                compliance_value = line.replace("COMPLIANCE:", "").strip().upper()
                compliant = "YES" in compliance_value
                current_section = None
            elif line.startswith("VIOLATIONS:"):
                current_section = "violations"
            elif line.startswith("RECOMMENDATIONS:"):
                current_section = "recommendations"
            elif line.startswith("ALIGNMENT_SCORE:"):
                try:
                    score = int(line.replace("ALIGNMENT_SCORE:", "").strip())
                except ValueError:
                    score = 90
                current_section = None
            elif line.startswith("- ") and current_section == "violations":
                violations.append(line[2:])
            elif line.startswith("- ") and current_section == "recommendations":
                recommendations.append(line[2:])

        return {
            "compliant": compliant,
            "violations": violations,
            "recommendations": recommendations,
            "spec_alignment": score
        }

    def _load_project_spec(self) -> str:
        """Load PROJECT_SPEC.md from .buildrunner directory"""
        spec_path = self.project_root / ".buildrunner" / "PROJECT_SPEC.md"

        if not spec_path.exists():
            return "No PROJECT_SPEC.md found"

        try:
            return spec_path.read_text()
        except Exception:
            return "Failed to read PROJECT_SPEC.md"

    def _get_file_diff(self, file_path: str) -> str:
        """Get git diff for a file"""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD", file_path],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return result.stdout
        except Exception:
            return ""


async def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ai_code_review.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    reviewer = CodeReviewer()
    result = await reviewer.review_file(file_path)

    print(f"\n=== Code Review for {file_path} ===\n")
    print(f"Summary: {result['review']['summary']}")
    print(f"Score: {result['review']['score']}/100")

    if result['review']['issues']:
        print("\nIssues:")
        for issue in result['review']['issues']:
            print(f"  - {issue}")

    if result['review']['suggestions']:
        print("\nSuggestions:")
        for suggestion in result['review']['suggestions']:
            print(f"  - {suggestion}")

    if result.get('architecture'):
        print(f"\nArchitecture Compliance: {'✓' if result['architecture']['compliant'] else '✗'}")
        print(f"Alignment Score: {result['architecture']['spec_alignment']}/100")


if __name__ == "__main__":
    asyncio.run(main())
