"""Documentation Analyzer - uses AI to extract PRD information from docs"""

import logging
import os
from typing import Dict, List, Optional
from pathlib import Path

from .doc_scanner import DocumentationFile

logger = logging.getLogger(__name__)


class DocumentationAnalyzer:
    """Analyzes documentation files using AI to extract PRD information"""

    def __init__(self):
        """Initialize documentation analyzer"""
        # Lazy import to avoid dependency issues if not used
        pass

    async def analyze_for_prd(
        self, docs: List[DocumentationFile], project_name: str
    ) -> Dict[str, any]:
        """
        Analyze documentation files to extract PRD sections

        Args:
            docs: List of documentation files
            project_name: Name of the project

        Returns:
            Dictionary with PRD sections extracted from documentation
        """
        logger.info(f"Analyzing {len(docs)} documentation files for PRD information")

        # Combine documentation content
        combined_content = self._combine_docs(docs)

        if not combined_content:
            logger.warning("No documentation content to analyze")
            return self._empty_prd_sections()

        # Use AI to extract PRD information
        prd_sections = await self._extract_prd_sections(combined_content, project_name)

        return prd_sections

    def _combine_docs(self, docs: List[DocumentationFile]) -> str:
        """Combine documentation files with headers"""
        sections = []

        for doc in docs:
            # Prioritize README
            if doc.type == "readme":
                sections.insert(0, f"# {doc.path.name}\n\n{doc.content}\n\n")
            else:
                sections.append(f"# {doc.path.name}\n\n{doc.content}\n\n")

        return "\n---\n\n".join(sections)

    async def _extract_prd_sections(self, content: str, project_name: str) -> Dict[str, any]:
        """Extract PRD sections using AI"""
        try:
            # Import OpenRouter client here to avoid dependency issues
            from api.openrouter_client import openrouter_client

            # Truncate content if too long (max ~15k chars to stay under token limits)
            if len(content) > 15000:
                logger.info("Truncating documentation content to fit token limits")
                content = content[:15000] + "\n\n... (content truncated)"

            # Build prompt for AI
            prompt = self._build_extraction_prompt(content, project_name)

            # Call AI
            result = await openrouter_client.extract_prd_from_docs(prompt)

            if result and result.get("success"):
                return result.get("prd_sections", self._empty_prd_sections())
            else:
                logger.warning(f"AI extraction failed: {result.get('error')}")
                return self._empty_prd_sections()

        except Exception as e:
            logger.warning(f"Error extracting PRD sections with AI: {e}")
            return self._empty_prd_sections()

    def _build_extraction_prompt(self, content: str, project_name: str) -> str:
        """Build prompt for AI to extract PRD sections"""
        return f"""Analyze the following documentation for the project "{project_name}" and extract information for a Product Requirements Document (PRD).

DOCUMENTATION:
{content}

Extract the following sections. If information is not available for a section, leave it empty or provide a brief placeholder.

1. **Executive Summary** - Brief overview of what the project does (2-3 sentences)
2. **Project Goals** - Main objectives and goals of the project (bullet points)
3. **Target Users** - Who is this project for? (1-2 sentences)
4. **User Stories** - Key user stories in "As a [user], I want [feature] so that [benefit]" format (3-5 stories)
5. **Technical Requirements** - Key technical requirements:
   - Frontend technologies
   - Backend technologies
   - Database requirements
   - Infrastructure needs
6. **Success Criteria** - How will success be measured? (bullet points)

Respond in JSON format:
{{
  "executive_summary": "...",
  "goals": ["goal1", "goal2", ...],
  "target_users": "...",
  "user_stories": ["story1", "story2", ...],
  "technical_requirements": {{
    "frontend": "...",
    "backend": "...",
    "database": "...",
    "infrastructure": "..."
  }},
  "success_criteria": ["criterion1", "criterion2", ...]
}}

If you cannot find specific information for a field, use reasonable defaults based on the project type and documentation you see."""

    def _empty_prd_sections(self) -> Dict[str, any]:
        """Return empty PRD sections"""
        return {
            "executive_summary": "",
            "goals": [],
            "target_users": "",
            "user_stories": [],
            "technical_requirements": {
                "frontend": "",
                "backend": "",
                "database": "",
                "infrastructure": "",
            },
            "success_criteria": [],
        }

    def sync_analyze_for_prd(
        self, docs: List[DocumentationFile], project_name: str
    ) -> Dict[str, any]:
        """
        Synchronous wrapper for analyze_for_prd (for non-async contexts)

        Args:
            docs: List of documentation files
            project_name: Name of the project

        Returns:
            Dictionary with PRD sections extracted from documentation
        """
        import asyncio

        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.analyze_for_prd(docs, project_name))
                    return future.result()
            else:
                # Run in the current loop
                return loop.run_until_complete(self.analyze_for_prd(docs, project_name))
        except Exception as e:
            logger.warning(f"Error in sync_analyze_for_prd: {e}")
            # Fallback: just run without async
            return asyncio.run(self.analyze_for_prd(docs, project_name))
