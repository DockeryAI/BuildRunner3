"""
OpenRouter Client - Interface to Claude Opus for PRD generation
"""

import os
import json
import httpx
from typing import Dict, Optional, List


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "anthropic/claude-opus-4"


class OpenRouterClient:
    """Client for OpenRouter API integration"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            print("Warning: No OpenRouter API key found")

    async def parse_project_description(self, description: str) -> Dict:
        """
        Parse a natural language project description into structured PRD

        Args:
            description: Natural language description of the project

        Returns:
            Dict with parsed PRD structure
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "OpenRouter API key not configured"
            }

        prompt = f"""Parse this project description into a structured PRD.
        
Project Description:
{description}

Generate a JSON response with this structure:
{{
  "overview": "2-3 sentence summary",
  "features": [
    {{
      "id": "f1",
      "title": "Feature name",
      "description": "What it does",
      "priority": "high|medium|low",
      "acceptance_criteria": "How to verify it works"
    }}
  ],
  "user_stories": [
    {{
      "id": "us1",
      "role": "user type",
      "action": "what they want to do",
      "benefit": "why they want it",
      "priority": "high|medium|low"
    }}
  ],
  "tech_requirements": [
    {{
      "id": "tr1",
      "requirement": "technical requirement",
      "rationale": "why it's needed",
      "priority": "high|medium|low"
    }}
  ],
  "success_criteria": [
    "measurable success metric"
  ]
}}

Return ONLY valid JSON, no other text."""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.5
                    }
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"OpenRouter API error: {response.status_code}"
                    }

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Parse JSON from content (handle markdown code blocks)
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                prd_data = json.loads(content)

                return {
                    "success": True,
                    "prd": prd_data
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_feature_suggestions(
        self,
        project_context: Dict,
        section: str,
        subsection: Optional[str] = None,
        custom_request: Optional[str] = None
    ) -> Dict:
        """
        Generate AI suggestions for a specific PRD section

        Args:
            project_context: Current PRD data
            section: Which section to generate suggestions for
            custom_request: Optional custom request from user

        Returns:
            Dict with suggestions
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "OpenRouter API key not configured"
            }

        # Handle overview section with subsections
        if section == "overview":
            subsection_prompts = {
                "name": "Suggest improvements or alternatives for the project name that are memorable, clear, and align with the project goals",
                "summary": "Suggest improvements or key points to include in the executive summary to make it more compelling",
                "goals": "Suggest additional goals and objectives that would strengthen this project's mission",
                "users": "Suggest additional target user segments or pain points to address"
            }

            if subsection:
                base_prompt = subsection_prompts.get(subsection, "Suggest improvements for this overview field")
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
        else:
            # Handle other sections (features, user_stories, etc.)
            section_prompts = {
                "features": "Suggest additional features that would enhance this project",
                "user_stories": "Suggest additional user stories for this project",
                "tech_requirements": "Suggest technical requirements for this project",
                "success_criteria": "Suggest success criteria for measuring this project"
            }

            base_prompt = section_prompts.get(section, "Suggest improvements")
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

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7
                    }
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"OpenRouter API error: {response.status_code}"
                    }

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # Parse JSON from content
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                suggestions_data = json.loads(content)

                return {
                    "success": True,
                    "suggestions": suggestions_data.get("suggestions", [])
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
