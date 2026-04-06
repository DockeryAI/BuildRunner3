"""
OpenRouter API Client
Integrates with OpenRouter for AI model access (Claude Opus)
"""

import os
import json
import httpx
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPUS_MODEL = "anthropic/claude-opus-4"


class OpenRouterClient:
    """Client for OpenRouter API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.warning("No OpenRouter API key found")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = OPUS_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict:
        """
        Send a chat completion request to OpenRouter

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model ID (default: Claude Opus)
            temperature: Sampling temperature
            max_tokens: Maximum response tokens

        Returns:
            Dict with response content and metadata
        """
        if not self.api_key:
            return {"success": False, "error": "OpenRouter API key not configured"}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://buildrunner.dev",
                        "X-Title": "BuildRunner 3",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )

                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "content": data["choices"][0]["message"]["content"],
                    "model": data["model"],
                    "usage": data.get("usage", {}),
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.text}")
            return {
                "success": False,
                "error": f"API error: {e.response.status_code}",
                "details": e.response.text,
            }
        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            return {"success": False, "error": str(e)}

    async def parse_project_description(self, description: str) -> Dict:
        """
        Parse a natural language project description into structured PRD data

        Args:
            description: User's project description

        Returns:
            Dict with parsed PRD sections
        """
        prompt = f"""You are a product requirements expert. Parse the following project description into a structured PRD.

Project Description:
{description}

Extract and generate:
1. Project Overview (1-2 sentences)
2. Core Features (list of 3-7 main features)
3. User Stories (3-5 user stories in "As a..., I want..., So that..." format)
4. Technical Requirements (high-level tech stack suggestions)
5. Success Criteria (3-5 measurable outcomes)

Return your response in this EXACT JSON format:
{{
  "overview": "string",
  "features": [
    {{
      "title": "string",
      "description": "string",
      "priority": "high|medium|low"
    }}
  ],
  "user_stories": ["string"],
  "technical_requirements": {{
    "frontend": "string",
    "backend": "string",
    "database": "string",
    "infrastructure": "string"
  }},
  "success_criteria": ["string"]
}}

Keep descriptions concise but clear. Focus on what matters most."""

        messages = [{"role": "user", "content": prompt}]

        result = await self.chat_completion(messages, temperature=0.5)

        if not result["success"]:
            return result

        try:
            # Parse JSON from response
            import json

            content = result["content"]

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed_data = json.loads(content)

            return {
                "success": True,
                "prd": parsed_data,
                "model": result["model"],
                "usage": result["usage"],
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {
                "success": False,
                "error": "Failed to parse response as JSON",
                "raw_response": result.get("content", ""),
            }

    async def generate_feature_suggestions(
        self,
        project_context: Dict,
        section: str,
        subsection: Optional[str] = None,
        custom_request: Optional[str] = None,
    ) -> Dict:
        """
        Generate AI-powered feature suggestions for a PRD section

        Args:
            project_context: Current PRD data
            section: Which section to generate for
            subsection: Optional subsection (for overview: name, summary, goals, users)
            custom_request: Optional specific request from user

        Returns:
            Dict with list of suggestions
        """
        # Handle overview section with subsections
        if section == "overview":
            subsection_prompts = {
                "name": "Suggest improvements or alternatives for the project name that are memorable, clear, and align with the project goals",
                "summary": "Suggest improvements or key points to include in the executive summary to make it more compelling",
                "goals": "Suggest additional goals and objectives that would strengthen this project's mission",
                "users": "Suggest additional target user segments or pain points to address",
            }

            if subsection:
                base_prompt = subsection_prompts.get(
                    subsection, "Suggest improvements for this overview field"
                )
                # Include subsection in prompt for tagged responses
                prompt = f"""Given this project context:

{json.dumps(project_context, indent=2)}

{base_prompt if not custom_request else custom_request}

Generate 3-5 suggestions in JSON format. IMPORTANT: Each suggestion MUST include a "subsection" field with value "{subsection}":
{{
  "suggestions": [
    {{
      "title": "Suggestion title",
      "description": "What it is",
      "priority": "high|medium|low",
      "rationale": "Why it's valuable",
      "subsection": "{subsection}"
    }}
  ]
}}

Return ONLY valid JSON."""
            else:
                # Generate suggestions for all overview subsections
                prompt = f"""Given this project context:

{json.dumps(project_context, indent=2)}

Generate 2-3 suggestions for EACH of these overview subsections:
- name: Improvements for the project name
- summary: Key points for the executive summary
- goals: Additional goals and objectives
- users: Additional target user segments

Generate suggestions in JSON format. IMPORTANT: Each suggestion MUST include a "subsection" field indicating which subsection it belongs to (name/summary/goals/users):
{{
  "suggestions": [
    {{
      "title": "Suggestion title",
      "description": "What it is",
      "priority": "high|medium|low",
      "rationale": "Why it's valuable",
      "subsection": "name"
    }}
  ]
}}

Return ONLY valid JSON."""
        elif section == "stories":
            # Generate user stories in proper format
            prompt = f"""Given this project context:

{json.dumps(project_context, indent=2)}

{custom_request if custom_request else "Generate user stories for this project"}

Generate 3-5 user stories in JSON format. Each story should follow the format "As a [role], I want to [action], so that [benefit]":
{{
  "suggestions": [
    {{
      "title": "As a [role], I want to [action], so that [benefit]",
      "description": "Acceptance criteria or additional details about this user story",
      "priority": "high|medium|low",
      "rationale": "Why this user story is important for the product"
    }}
  ]
}}

Return ONLY valid JSON."""

        elif section == "technical":
            # Generate technical requirements
            prompt = f"""Given this project context:

{json.dumps(project_context, indent=2)}

{custom_request if custom_request else "Suggest technical requirements for this project"}

Generate 3-5 technical requirements covering frontend, backend, database, or infrastructure. Be specific about technologies, frameworks, or architectural decisions:
{{
  "suggestions": [
    {{
      "title": "Requirement title (e.g., 'React Native for mobile app')",
      "description": "Detailed explanation of the requirement and why it's needed",
      "priority": "high|medium|low",
      "rationale": "Technical justification for this choice"
    }}
  ]
}}

Return ONLY valid JSON."""

        elif section == "success":
            # Generate success criteria
            prompt = f"""Given this project context:

{json.dumps(project_context, indent=2)}

{custom_request if custom_request else "Suggest measurable success criteria for this project"}

Generate 3-5 success criteria that are specific, measurable, and time-bound. Focus on KPIs and metrics:
{{
  "suggestions": [
    {{
      "title": "Success metric title",
      "description": "How to measure this metric and what the target is (e.g., '90% user satisfaction within 3 months')",
      "priority": "high|medium|low",
      "rationale": "Why this metric is important for project success"
    }}
  ]
}}

Return ONLY valid JSON."""

        else:
            # Handle features or unknown sections
            base_prompt = "Suggest additional features that would enhance this project"
            if custom_request:
                base_prompt = custom_request

            prompt = f"""Given this project context:

{json.dumps(project_context, indent=2)}

{base_prompt}

Generate 3-5 suggestions in JSON format:
{{
  "suggestions": [
    {{
      "title": "Suggestion title",
      "description": "What it is",
      "priority": "high|medium|low",
      "rationale": "Why it's valuable"
    }}
  ]
}}

Return ONLY valid JSON."""

        messages = [{"role": "user", "content": prompt}]

        result = await self.chat_completion(messages, temperature=0.7)

        if not result["success"]:
            return result

        try:
            content = result["content"]

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed_data = json.loads(content)

            return {
                "success": True,
                "suggestions": parsed_data.get("suggestions", []),
                "model": result["model"],
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse suggestions JSON: {e}")
            return {
                "success": False,
                "error": "Failed to parse suggestions",
                "raw_response": result.get("content", ""),
            }

    async def extract_prd_from_docs(self, prompt: str) -> Dict:
        """
        Extract PRD sections from documentation using AI

        Args:
            prompt: Formatted prompt with documentation content

        Returns:
            Dict with success flag and prd_sections
        """
        messages = [{"role": "user", "content": prompt}]

        result = await self.chat_completion(messages, temperature=0.3, max_tokens=2000)

        if not result["success"]:
            return result

        try:
            content = result["content"]

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed_data = json.loads(content)

            return {
                "success": True,
                "prd_sections": parsed_data,
                "model": result["model"],
                "usage": result.get("usage", {}),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse PRD extraction JSON: {e}")
            return {
                "success": False,
                "error": "Failed to parse PRD sections",
                "raw_response": result.get("content", ""),
            }


# Singleton instance
openrouter_client = OpenRouterClient()
