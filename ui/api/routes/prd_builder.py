"""
PRD Builder Routes - API endpoints for interactive PRD building
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from pathlib import Path

from api.project_manager import ProjectManager
from api.openrouter_client import OpenRouterClient

router = APIRouter()
project_manager = ProjectManager()
openrouter_client = OpenRouterClient()


class ProjectInitRequest(BaseModel):
    project_name: str


class PRDParseRequest(BaseModel):
    description: str


class SuggestionsRequest(BaseModel):
    project_context: Dict
    section: str
    subsection: Optional[str] = None
    custom_request: Optional[str] = None


class PRDSaveRequest(BaseModel):
    project_path: str
    prd_data: Dict


@router.post("/project/init")
async def init_project(request: ProjectInitRequest):
    """Initialize a new project"""
    result = await project_manager.create_project(request.project_name)
    return result


@router.get("/project/list")
async def list_projects():
    """List all projects"""
    result = project_manager.list_projects()
    return result


@router.post("/prd/parse")
async def parse_prd(request: PRDParseRequest):
    """Parse natural language description into PRD"""
    result = await openrouter_client.parse_project_description(request.description)
    return result


@router.post("/prd/suggestions")
async def get_suggestions(request: SuggestionsRequest):
    """Generate AI suggestions for PRD section"""
    result = await openrouter_client.generate_feature_suggestions(
        request.project_context,
        request.section,
        request.subsection,
        request.custom_request
    )
    return result


@router.post("/prd/save")
async def save_prd(request: PRDSaveRequest):
    """Save PRD to PROJECT_SPEC.md"""
    try:
        project_path = Path(request.project_path)
        prd_content = _convert_prd_to_markdown(request.prd_data)
        
        spec_file = project_path / "PROJECT_SPEC.md"
        spec_file.write_text(prd_content)
        
        return {
            "success": True,
            "file_path": str(spec_file)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _convert_prd_to_markdown(prd_data: Dict) -> str:
    """Convert structured PRD data to markdown"""
    
    priority_emojis = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢"
    }
    
    md = f"""# PROJECT_SPEC.md

## Overview
{prd_data.get("overview", "")}

## Features

"""
    
    for feature in prd_data.get("features", []):
        pri = priority_emojis.get(feature.get("priority", "medium"), "🟡")
        md += f"""### {pri} {feature.get("title", "")}
{feature.get("description", "")}

**Acceptance Criteria:**
{feature.get("acceptance_criteria", "")}

"""

    md += "## User Stories\n\n"
    for story in prd_data.get("user_stories", []):
        pri = priority_emojis.get(story.get("priority", "medium"), "🟡")
        md += f"""### {pri} {story.get("id", "")}
As a **{story.get("role", "")}**, I want to **{story.get("action", "")}** so that **{story.get("benefit", "")}**.

"""
    
    md += "## Technical Requirements\n\n"
    for req in prd_data.get("tech_requirements", []):
        pri = priority_emojis.get(req.get("priority", "medium"), "🟡")
        md += f"""### {pri} {req.get("requirement", "")}
{req.get("rationale", "")}

"""
    
    md += "## Success Criteria\n\n"
    for criterion in prd_data.get("success_criteria", []):
        md += f"- {criterion}\n"
    
    return md
