"""
Real Anthropic Opus API client for PRD generation — Claude 4.7 edition

Provides intelligent PROJECT_SPEC generation, requirements analysis,
design token creation, and spec validation using Claude Opus 4.7.

--- SDK PATH NOTE (2026-04-21) ---
Installed anthropic SDK v0.73.x does not expose `output_config` as a named
parameter on `messages.create()`. Structured outputs (effort tier, etc.) are
therefore routed via extra_body={"output_config": {"effort": <tier>}} as the
interim path. The SDK's `thinking` parameter accepts the "enabled" type with
budget_tokens in the formal TypedDict — adaptive thinking (type="adaptive",
display="summarized") is passed as a plain dict since the TypedDict is
total=False and accepts extra keys at runtime.
Upgrade to an SDK that natively exposes output_config and thinking.type=adaptive
when available; remove this note and the extra_body shim at that point.
Minimum SDK version required: 0.73.0 (ThinkingBlock, extra_body support).
----------------------------------
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional
from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message


# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

# Default model — override via ANTHROPIC_MODEL env var or pass model= arg.
# Supports "opusplan" alias: pass model="opusplan" to have the client resolve
# to the current Opus planning model automatically.
_DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7")
_OPUSPLAN_ALIAS = "opusplan"
_OPUSPLAN_RESOLVED = "claude-opus-4-7"

# Per-method max_tokens (right-sized for 4.7 tokenizer; 1.0–1.35× inflation
# means old 4096 ceilings are too low for xhigh reasoning).
_MAX_TOKENS = {
    "pre_fill_spec": 16000,       # Spec output can be 2–8k; give generous headroom
    "analyze_requirements": 4096, # JSON response; 4k sufficient
    "generate_design_tokens": 4096,
    "validate_spec": 2048,        # Classification/completeness check only
}

# Effort tiers per method routed via extra_body["output_config"]["effort"]
# xhigh = spec generation (full reasoning pass)
# high  = requirements + design tokens (substantive but not exhaustive)
# medium = validation (classification-grade; per 4.7 effort guidance)
_EFFORT_TIERS = {
    "pre_fill_spec": "xhigh",
    "analyze_requirements": "high",
    "generate_design_tokens": "high",
    "validate_spec": "medium",
}

# Adaptive thinking config — passed as plain dict to avoid TypedDict literal
# constraint on "type" field. SDK v0.74.1 allows this at runtime.
_ADAPTIVE_THINKING = {"type": "adaptive", "display": "summarized"}


def _extract_text(message: Message) -> str:
    """
    Type-safe text extractor. Adaptive thinking puts ThinkingBlock first in
    content[] — positional indexing (message.content[0].text) crashes. This
    skips all non-text blocks and returns the first text block's content, or
    empty string if none found.
    """
    return next(
        (b.text for b in message.content if getattr(b, "type", None) == "text"),
        "",
    )


class OpusAPIError(Exception):
    """Opus API error"""

    pass


def with_retry(max_retries: int = 3):
    """
    Decorator for retry logic with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        Decorated async function with retry capability
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2**attempt)
                    continue

        return wrapper

    return decorator


class OpusClient:
    """Opus 4.7 API client for PRD wizard"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Opus client

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name; pass "opusplan" to resolve to the current Opus
                   planning model. Defaults to ANTHROPIC_MODEL env var or
                   "claude-opus-4-7".

        Raises:
            ValueError: If API key not found
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)

        raw_model = model or _DEFAULT_MODEL
        self.model = _OPUSPLAN_RESOLVED if raw_model == _OPUSPLAN_ALIAS else raw_model

    def _make_create_kwargs(self, method_name: str, messages: List[Dict]) -> Dict[str, Any]:
        """
        Build kwargs for messages.create, applying per-method effort tier,
        adaptive thinking, and right-sized max_tokens.

        The effort tier is routed via extra_body["output_config"] (interim SDK
        path — see module docstring). The thinking param uses adaptive mode.
        """
        return {
            "model": self.model,
            "max_tokens": _MAX_TOKENS[method_name],
            "messages": messages,
            "thinking": _ADAPTIVE_THINKING,
            "extra_body": {
                "output_config": {
                    "effort": _EFFORT_TIERS[method_name],
                }
            },
        }

    @with_retry(max_retries=3)
    async def pre_fill_spec(self, industry: str, use_case: str, user_input: Dict[str, str]) -> str:
        """
        Pre-fill PROJECT_SPEC.md using Opus

        Args:
            industry: Industry type (e.g., "Healthcare", "Fintech")
            use_case: Use case pattern (e.g., "Dashboard", "API")
            user_input: User responses from wizard (project_name, description, etc.)

        Returns:
            Generated PROJECT_SPEC.md content

        Raises:
            OpusAPIError: If API call fails after retries
        """
        prompt = self._build_spec_prompt(industry, use_case, user_input)

        try:
            message = await self.async_client.messages.create(
                **self._make_create_kwargs(
                    "pre_fill_spec",
                    [{"role": "user", "content": prompt}],
                )
            )
            return _extract_text(message)
        except Exception as e:
            raise OpusAPIError(f"Opus API error during spec pre-fill: {e}")

    @with_retry(max_retries=3)
    async def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        Analyze user requirements and suggest features

        Args:
            requirements: Raw user requirements text

        Returns:
            Dict with:
                - features: List of suggested features (with id, name, description)
                - architecture: Suggested architecture (frontend, backend, database)
                - tech_stack: Recommended technologies

        Raises:
            OpusAPIError: If API call fails or JSON parsing fails
        """
        prompt = f"""Analyze these project requirements and provide:
1. List of features (as feature objects with id, name, description)
2. Suggested architecture (frontend, backend, database)
3. Recommended tech stack

Requirements:
{requirements}

Respond in JSON format with the following structure:
{{
  "features": [
    {{"id": "feat-1", "name": "Feature Name", "description": "Feature description"}}
  ],
  "architecture": {{
    "frontend": "Framework/library",
    "backend": "Framework/library",
    "database": "Database system"
  }},
  "tech_stack": ["Technology 1", "Technology 2"]
}}"""

        try:
            message = await self.async_client.messages.create(
                **self._make_create_kwargs(
                    "analyze_requirements",
                    [{"role": "user", "content": prompt}],
                )
            )
            response_text = _extract_text(message)
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise OpusAPIError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise OpusAPIError(f"Requirements analysis failed: {e}")

    @with_retry(max_retries=3)
    async def generate_design_tokens(self, industry: str, use_case: str) -> Dict[str, Any]:
        """
        Generate design system tokens for industry + use case

        Args:
            industry: Industry type (e.g., "Healthcare", "Fintech")
            use_case: Use case pattern (e.g., "Dashboard", "API")

        Returns:
            Dict with design tokens compatible with Tailwind:
                - colors: Color palette (primary, secondary, accent, neutral)
                - typography: Fonts, sizes, weights
                - spacing: Spacing scale
                - borderRadius: Border radius values
                - shadows: Shadow definitions
                - breakpoints: Responsive breakpoints

        Raises:
            OpusAPIError: If API call fails or JSON parsing fails
        """
        prompt = f"""Generate design system tokens for:
Industry: {industry}
Use Case: {use_case}

Include:
- Color palette (primary, secondary, accent, neutral with shades)
- Typography (fonts, sizes, weights, line heights)
- Spacing scale (consistent spacing system)
- Border radius values
- Shadow definitions
- Responsive breakpoints

Respond in JSON format compatible with Tailwind config.

Example structure:
{{
  "colors": {{
    "primary": {{"50": "#...", "100": "#...", "500": "#...", "900": "#..."}},
    "secondary": {{"50": "#...", "500": "#...", "900": "#..."}}
  }},
  "typography": {{
    "fontFamily": {{"sans": ["Font Name", "fallback"], "mono": ["Mono Font"]}},
    "fontSize": {{"xs": "0.75rem", "sm": "0.875rem", "base": "1rem"}}
  }},
  "spacing": {{"0": "0", "1": "0.25rem", "2": "0.5rem"}},
  "borderRadius": {{"none": "0", "sm": "0.125rem", "DEFAULT": "0.25rem"}},
  "boxShadow": {{"sm": "...", "DEFAULT": "...", "lg": "..."}},
  "screens": {{"sm": "640px", "md": "768px", "lg": "1024px"}}
}}"""

        try:
            message = await self.async_client.messages.create(
                **self._make_create_kwargs(
                    "generate_design_tokens",
                    [{"role": "user", "content": prompt}],
                )
            )
            response_text = _extract_text(message)
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise OpusAPIError(f"Failed to parse design tokens JSON: {e}")
        except Exception as e:
            raise OpusAPIError(f"Design token generation failed: {e}")

    @with_retry(max_retries=3)
    async def validate_spec(self, spec_content: str) -> Dict[str, Any]:
        """
        Validate PROJECT_SPEC completeness

        Args:
            spec_content: PROJECT_SPEC.md content to validate

        Returns:
            Dict with validation results:
                - valid: bool (True if spec is complete)
                - missing_sections: List[str] (sections that are missing)
                - suggestions: List[str] (improvement suggestions)
                - score: float (0-100 completeness score)

        Raises:
            OpusAPIError: If API call fails or JSON parsing fails
        """
        prompt = f"""Validate this PROJECT_SPEC.md for completeness:

{spec_content}

Check for:
- All required sections present (Overview, Features, Architecture, etc.)
- Technical details specified clearly
- Architecture clearly defined
- Security/compliance requirements addressed
- Testing strategy included

Respond in JSON format with:
{{
  "valid": true/false,
  "missing_sections": ["section1", "section2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "score": 0-100
}}"""

        try:
            message = await self.async_client.messages.create(
                **self._make_create_kwargs(
                    "validate_spec",
                    [{"role": "user", "content": prompt}],
                )
            )
            response_text = _extract_text(message)
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise OpusAPIError(f"Failed to parse validation JSON: {e}")
        except Exception as e:
            raise OpusAPIError(f"Spec validation failed: {e}")

    def _build_spec_prompt(self, industry: str, use_case: str, user_input: Dict[str, str]) -> str:
        """
        Build prompt for PROJECT_SPEC generation

        Args:
            industry: Industry type
            use_case: Use case pattern
            user_input: User-provided project details

        Returns:
            Formatted prompt for Opus
        """
        return f"""Generate a complete PROJECT_SPEC.md for:

Industry: {industry}
Use Case: {use_case}

User Input:
{json.dumps(user_input, indent=2)}

The spec should include:

# 1. Project Overview
- Project name and description
- Target audience
- Key objectives
- Success criteria

# 2. Core Features
- Detailed feature list with descriptions
- Feature priorities
- Dependencies between features

# 3. Technical Architecture
- Frontend stack and structure
- Backend stack and APIs
- Database schema
- Infrastructure requirements

# 4. Design System
- UI/UX principles for {industry}
- Color palette
- Typography
- Component library

# 5. Compliance Requirements
- Industry-specific regulations ({industry})
- Data privacy (GDPR, CCPA, etc.)
- Security standards
- Accessibility requirements (WCAG)

# 6. Security Considerations
- Authentication and authorization
- Data encryption
- API security
- Threat mitigation

# 7. Testing Strategy
- Unit testing approach
- Integration testing
- E2E testing
- Performance testing
- Coverage targets

# 8. Deployment Plan
- Deployment environments
- CI/CD pipeline
- Monitoring and logging
- Rollback strategy

Use the BuildRunner PROJECT_SPEC.md format.
Be specific and detailed, especially for the {industry} industry and {use_case} use case.
Include concrete technical recommendations."""
