"""
PRD Builder API Routes
Interactive PRD creation with AI assistance
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import subprocess
from pathlib import Path

from api.project_manager import project_manager
from api.openrouter_client import openrouter_client
from core.alias_manager import alias_manager

router = APIRouter()


class ProjectInitRequest(BaseModel):
    project_name: str
    project_root: Optional[str] = None


class ProjectAttachRequest(BaseModel):
    project_path: str
    dry_run: Optional[bool] = False


class PRDParseRequest(BaseModel):
    description: str


class PRDSuggestionRequest(BaseModel):
    project_context: Dict
    section: str
    subsection: Optional[str] = None
    custom_request: Optional[str] = None


class PRDSaveRequest(BaseModel):
    project_path: str
    prd_data: Dict
    prd_markdown: Optional[str] = None  # Optional pre-serialized markdown from frontend


class PRDReadRequest(BaseModel):
    project_path: str


@router.post("/project/init")
async def initialize_project(request: ProjectInitRequest):
    """Create new project in ~/Projects and install BuildRunner"""
    result = await project_manager.create_project(
        request.project_name,
        request.project_root
    )
    return result


@router.get("/project/list")
async def list_projects():
    """List all projects"""
    result = project_manager.list_projects()
    return result


@router.post("/project/attach")
async def attach_project(request: ProjectAttachRequest):
    """
    Attach BuildRunner to an existing project
    Scans codebase and generates PROJECT_SPEC.md
    """
    try:
        project_path = Path(request.project_path)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {request.project_path}")

        if not project_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {request.project_path}")

        # Use the CLI attach command via subprocess
        # First, need to find br executable
        br_path = Path(__file__).parent.parent.parent / '.venv' / 'bin' / 'br'

        if not br_path.exists():
            # Try global br
            result = subprocess.run(['which', 'br'], capture_output=True, text=True)
            if result.returncode == 0:
                br_path = Path(result.stdout.strip())
            else:
                raise HTTPException(status_code=500, detail="BuildRunner not found in system")

        # Build command
        cmd = [str(br_path), 'attach', 'attach', str(project_path)]
        if request.dry_run:
            cmd.append('--dry-run')

        # Execute br attach command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_path)
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': result.stderr or result.stdout,
                'project_path': str(project_path)
            }

        # Parse the output to extract statistics
        output = result.stdout

        # Check if PROJECT_SPEC.md was created
        spec_file = project_path / '.buildrunner' / 'PROJECT_SPEC.md'
        prd_created = spec_file.exists() if not request.dry_run else False

        return {
            'success': True,
            'project_path': str(project_path),
            'project_name': project_path.name,
            'prd_created': prd_created,
            'prd_path': str(spec_file) if prd_created else None,
            'output': output,
            'message': f'Successfully attached BuildRunner to {project_path.name}'
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prd/parse")
async def parse_description(request: PRDParseRequest):
    """Parse natural language description into structured PRD"""
    result = await openrouter_client.parse_project_description(
        request.description
    )
    return result


@router.post("/prd/suggestions")
async def get_suggestions(request: PRDSuggestionRequest):
    """Generate AI suggestions for a PRD section"""
    result = await openrouter_client.generate_feature_suggestions(
        request.project_context,
        request.section,
        request.subsection,
        request.custom_request
    )
    return result


@router.post("/prd/read")
async def read_prd(request: PRDReadRequest):
    """Read PRD from project directory"""
    try:
        project_path = Path(request.project_path)

        # Try .buildrunner/PROJECT_SPEC.md first (BR3)
        prd_file = project_path / ".buildrunner" / "PROJECT_SPEC.md"

        if not prd_file.exists():
            # Try root PROJECT_SPEC.md as fallback
            prd_file = project_path / "PROJECT_SPEC.md"

        if not prd_file.exists():
            return {
                'success': False,
                'content': None,
                'prd_markdown': None,
                'message': 'PRD not found in project'
            }

        # Read the file
        content = prd_file.read_text()

        return {
            'success': True,
            'content': content,
            'prd_markdown': content,  # Alias for consistency
            'file_path': str(prd_file),
            'last_modified': prd_file.stat().st_mtime,
            'message': 'PRD loaded successfully'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prd/parse-markdown")
async def parse_prd_markdown(request: PRDReadRequest):
    """Parse PROJECT_SPEC.md markdown into structured PRD data for Interactive Builder"""
    try:
        project_path = Path(request.project_path)

        # Try .buildrunner/PROJECT_SPEC.md first (BR3)
        prd_file = project_path / ".buildrunner" / "PROJECT_SPEC.md"

        if not prd_file.exists():
            # Try root PROJECT_SPEC.md as fallback
            prd_file = project_path / "PROJECT_SPEC.md"

        if not prd_file.exists():
            return {
                'success': False,
                'prd_data': None,
                'message': 'PRD not found in project'
            }

        # Read and parse the markdown file
        content = prd_file.read_text()
        prd_data = _parse_markdown_to_prd(content, project_path.name)

        return {
            'success': True,
            'prd_data': prd_data,
            'file_path': str(prd_file),
            'message': 'PRD parsed successfully'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prd/save")
async def save_prd(request: PRDSaveRequest):
    """Save PRD to project directory"""
    try:
        project_path = Path(request.project_path)
        buildrunner_dir = project_path / ".buildrunner"
        buildrunner_dir.mkdir(exist_ok=True)
        prd_file = buildrunner_dir / "PROJECT_SPEC.md"

        # Use pre-serialized markdown if provided, otherwise convert from data
        if request.prd_markdown:
            markdown_content = request.prd_markdown
        else:
            markdown_content = _convert_prd_to_markdown(request.prd_data)

        # Save to file
        prd_file.write_text(markdown_content)

        return {
            'success': True,
            'file_path': str(prd_file),
            'message': 'PRD saved successfully',
            'last_modified': prd_file.stat().st_mtime
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _parse_markdown_to_prd(markdown_content: str, project_name: str) -> Dict:
    """Parse PROJECT_SPEC.md markdown into structured PRD data"""
    import re

    prd_data = {
        'project_name': project_name,
        'overview': {
            'executive_summary': '',
            'goals': '',
            'target_users': ''
        },
        'features': [],
        'user_stories': [],
        'technical_requirements': {
            'frontend': '',
            'backend': '',
            'database': '',
            'infrastructure': ''
        },
        'success_criteria': []
    }

    # Extract project name from title
    title_match = re.search(r'^#\s+(.+?)(?:\s*-\s*Product Requirements|\s*$)', markdown_content, re.MULTILINE | re.IGNORECASE)
    if title_match:
        prd_data['project_name'] = title_match.group(1).strip()

    # Extract Overview section
    overview_match = re.search(r'##\s+(?:Project\s+)?Overview\s*\n(.*?)(?=\n##|\Z)', markdown_content, re.DOTALL | re.IGNORECASE)
    if overview_match:
        overview_text = overview_match.group(1).strip()
        prd_data['overview']['executive_summary'] = overview_text[:500]  # First 500 chars

    # Extract Goals/Core Requirements
    goals_match = re.search(r'##\s+(?:Core\s+Requirements|Goals)\s*\n(.*?)(?=\n##|\Z)', markdown_content, re.DOTALL | re.IGNORECASE)
    if goals_match:
        prd_data['overview']['goals'] = goals_match.group(1).strip()

    # Extract Features - support both formats:
    # Format 1: ## Features section with ### subsections
    # Format 2: ## Feature N: direct feature headers (BuildRunner3 format)

    # Try Format 2 first (## Feature N: Title) - split by --- separators
    # This matches the BuildRunner3 format where features are separated by ---
    sections = re.split(r'\n---+\n', markdown_content)

    feature_sections = []
    for section in sections:
        # Check if this section contains a feature (strip leading/trailing whitespace first)
        section_stripped = section.strip()
        feature_header_match = re.match(r'##\s+Feature\s+(\d+):\s+(.+?)\s*\n', section_stripped, re.IGNORECASE)
        if feature_header_match:
            feature_sections.append(section_stripped)

    if feature_sections:
        for section in feature_sections:
            # Extract title from header
            header_match = re.match(r'##\s+Feature\s+\d+:\s+(.+?)\s*\n', section, re.IGNORECASE)
            if not header_match:
                continue

            title = header_match.group(1).strip()

            # Extract priority
            priority = 'medium'
            priority_match = re.search(r'\*\*Priority:\*\*\s*(Critical|High|Medium|Low)', section, re.IGNORECASE)
            if priority_match:
                priority_text = priority_match.group(1).lower()
                if priority_text in ['critical', 'high']:
                    priority = 'high'
                elif priority_text == 'low':
                    priority = 'low'

            # Extract description section
            desc_match = re.search(r'###\s+Description\s*\n+(.*?)(?=\n###|\Z)', section, re.DOTALL | re.IGNORECASE)
            description = desc_match.group(1).strip() if desc_match else ''

            # If no description found, try to get some content from the section
            if not description:
                # Get first paragraph after the header
                first_para_match = re.search(r'##\s+Feature\s+\d+:.*?\n+(.{1,300})', section, re.DOTALL)
                if first_para_match:
                    description = first_para_match.group(1).strip()

            # Extract acceptance criteria
            criteria_match = re.search(r'###\s+Acceptance Criteria\s*\n+(.*?)(?=\n###|\Z)', section, re.DOTALL | re.IGNORECASE)
            if criteria_match:
                acceptance_criteria = criteria_match.group(1).strip()
            else:
                # Try Requirements section as fallback
                req_match = re.search(r'###\s+Requirements?\s*\n+(.*?)(?=\n###|\Z)', section, re.DOTALL | re.IGNORECASE)
                acceptance_criteria = req_match.group(1).strip() if req_match else ''

            # Extract status if present
            status = 'planned'  # default
            status_match = re.search(r'\*\*Status:\*\*\s*(Implemented|Partial|Planned)', section, re.IGNORECASE)
            if status_match:
                status = status_match.group(1).lower()

            # Extract version if present
            version_match = re.search(r'\*\*Version:\*\*\s*([\d.]+)', section, re.IGNORECASE)
            version = version_match.group(1) if version_match else 'v1.0'

            feature = {
                'id': f"feature-{len(prd_data['features'])}-{hash(title) % 10000}",
                'title': title,
                'description': description,
                'priority': priority,
                'acceptance_criteria': acceptance_criteria,
                'version': version,
                'status': status
            }
            prd_data['features'].append(feature)
    else:
        # Fallback to Format 1 (## Features section)
        features_match = re.search(r'##\s+Features\s*\n(.*?)(?=##|\Z)', markdown_content, re.DOTALL | re.IGNORECASE)
        if features_match:
            features_text = features_match.group(1)
            # Find all feature sections (### headers)
            feature_pattern = r'###\s+(.*?)\n(.*?)(?=###|\Z)'
            for match in re.finditer(feature_pattern, features_text, re.DOTALL):
                title = match.group(1).strip()
                content = match.group(2).strip()

                # Remove priority emoji if present
                title = re.sub(r'^[🔴🟡🟢]\s*', '', title)

                # Extract priority
                priority = 'medium'
                if '🔴' in match.group(1) or 'High' in content:
                    priority = 'high'
                elif '🟢' in match.group(1) or 'Low' in content:
                    priority = 'low'

                # Extract description
                desc_match = re.search(r'\*\*Description:\*\*\s*(.*?)(?=\*\*|$)', content, re.DOTALL)
                description = desc_match.group(1).strip() if desc_match else content[:200]

                # Extract acceptance criteria
                criteria_match = re.search(r'\*\*Acceptance Criteria:\*\*\s*(.*?)(?=---|##|\Z)', content, re.DOTALL)
                acceptance_criteria = criteria_match.group(1).strip() if criteria_match else ''

                feature = {
                    'id': f"feature-{len(prd_data['features'])}-{hash(title) % 10000}",
                    'title': title,
                    'description': description,
                    'priority': priority,
                    'acceptance_criteria': acceptance_criteria,
                    'version': 'v1.0',
                    'status': 'planned'
                }
                prd_data['features'].append(feature)

    # Extract User Stories
    stories_match = re.search(r'##\s+User Stories\s*\n(.*?)(?=##|\Z)', markdown_content, re.DOTALL | re.IGNORECASE)
    if stories_match:
        stories_text = stories_match.group(1)
        # Find all bullet points
        for line in stories_text.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                story = line.lstrip('- *').strip()
                if story:
                    prd_data['user_stories'].append(story)

    # Extract Technical Requirements
    tech_match = re.search(r'##\s+Technical Requirements\s*\n(.*?)(?=##|\Z)', markdown_content, re.DOTALL | re.IGNORECASE)
    if tech_match:
        tech_text = tech_match.group(1)

        # Extract Frontend
        frontend_match = re.search(r'###\s+Frontend\s*\n(.*?)(?=###|\Z)', tech_text, re.DOTALL | re.IGNORECASE)
        if frontend_match:
            prd_data['technical_requirements']['frontend'] = frontend_match.group(1).strip()

        # Extract Backend
        backend_match = re.search(r'###\s+Backend\s*\n(.*?)(?=###|\Z)', tech_text, re.DOTALL | re.IGNORECASE)
        if backend_match:
            prd_data['technical_requirements']['backend'] = backend_match.group(1).strip()

        # Extract Database
        db_match = re.search(r'###\s+Database\s*\n(.*?)(?=###|\Z)', tech_text, re.DOTALL | re.IGNORECASE)
        if db_match:
            prd_data['technical_requirements']['database'] = db_match.group(1).strip()

        # Extract Infrastructure
        infra_match = re.search(r'###\s+Infrastructure\s*\n(.*?)(?=###|\Z)', tech_text, re.DOTALL | re.IGNORECASE)
        if infra_match:
            prd_data['technical_requirements']['infrastructure'] = infra_match.group(1).strip()

    # Extract Success Criteria
    success_match = re.search(r'##\s+Success Criteria\s*\n(.*?)(?=##|\Z)', markdown_content, re.DOTALL | re.IGNORECASE)
    if success_match:
        success_text = success_match.group(1)
        for line in success_text.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*') or line.startswith('[ ]'):
                criterion = re.sub(r'^\s*[-*]\s*\[\s*\]\s*', '', line).strip()
                if criterion:
                    prd_data['success_criteria'].append(criterion)

    return prd_data


def _convert_prd_to_markdown(prd_data: Dict) -> str:
    """Convert PRD data structure to markdown format"""
    md = f"""# {prd_data.get('project_name', 'Project')} - Product Requirements Document

## Overview
{prd_data.get('overview', '')}

## Features

"""

    # Add features
    for feature in prd_data.get('features', []):
        priority_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }.get(feature.get('priority', 'medium'), '🟡')

        md += f"""### {priority_emoji} {feature.get('title', 'Feature')}

**Description:** {feature.get('description', '')}

**Priority:** {feature.get('priority', 'medium').title()}

**Acceptance Criteria:**
{feature.get('acceptance_criteria', '- To be defined')}

---

"""

    # Add user stories
    md += """## User Stories

"""
    for story in prd_data.get('user_stories', []):
        md += f"- {story}\n"

    # Add technical requirements
    tech_req = prd_data.get('technical_requirements', {})
    md += f"""

## Technical Requirements

### Frontend
{tech_req.get('frontend', 'To be determined')}

### Backend
{tech_req.get('backend', 'To be determined')}

### Database
{tech_req.get('database', 'To be determined')}

### Infrastructure
{tech_req.get('infrastructure', 'To be determined')}

## Success Criteria

"""

    for criterion in prd_data.get('success_criteria', []):
        md += f"- [ ] {criterion}\n"

    md += f"""

---
*Generated by BuildRunner 3 - Interactive PRD Builder*
"""

    return md


class FeatureDiscoveryRequest(BaseModel):
    project_path: str


class ProjectAliasRequest(BaseModel):
    alias: str
    project_path: str


@router.post("/prd/discover-features")
async def discover_features(request: FeatureDiscoveryRequest):
    """
    Discover features from codebase automatically

    Scans the codebase and identifies:
    - API endpoints → Backend features
    - UI components → Frontend features
    - CLI commands → Tool features
    - Database models → Data features
    - Core modules → System features

    Returns PRD data with discovered features marked as "implemented"
    """
    try:
        project_path = Path(request.project_path)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project path not found")

        # Import enhanced feature discovery
        from core.feature_discovery_v2 import EnhancedFeatureDiscovery, export_to_prd_format

        # Run discovery
        discovery = EnhancedFeatureDiscovery(project_path)
        features = discovery.discover_all()

        # Get project name from path
        project_name = project_path.name

        # Export to PRD format
        prd_data = export_to_prd_format(features, project_name)

        # Add metadata
        prd_data['metadata'] = {
            'discovery_date': str(Path(project_path).stat().st_mtime),
            'feature_count': len(features),
            'total_artifacts': sum(len(f.artifacts) for f in features),
            'avg_confidence': sum(f.confidence for f in features) / len(features) if features else 0,
        }

        return {
            "success": True,
            "prd_data": prd_data,
            "features_discovered": len(features),
            "message": f"Discovered {len(features)} features from codebase"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feature discovery failed: {str(e)}")


@router.post("/project/alias")
async def set_project_alias(request: ProjectAliasRequest):
    """
    Set an alias for a project directory.

    This allows quick navigation to projects using: br alias jump <alias>
    """
    try:
        project_path = Path(request.project_path)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project path not found: {request.project_path}")

        if not project_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {request.project_path}")

        # Set the alias using alias_manager
        try:
            alias_manager.set_alias(request.alias, str(project_path))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return {
            "success": True,
            "alias": request.alias,
            "project_path": str(project_path),
            "message": f"Alias '{request.alias}' set for project: {project_path.name}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set alias: {str(e)}")
