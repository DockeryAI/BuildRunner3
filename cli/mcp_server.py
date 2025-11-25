"""
MCP (Model Context Protocol) Server for BuildRunner 3.0

Exposes BuildRunner tools to Claude Code and other MCP-compatible AI assistants.
Allows AI to manage features, check status, and interact with the governance system.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.feature_registry import FeatureRegistry
from core.status_generator import StatusGenerator
from core.governance import GovernanceManager
from core.governance_enforcer import GovernanceEnforcer


class MCPServer:
    """
    MCP Server for BuildRunner 3.0.

    Implements Model Context Protocol to expose BuildRunner functionality
    to AI assistants like Claude Code.

    Protocol Format:
        Request: {"tool": "tool_name", "arguments": {...}}
        Response: {"success": bool, "result": ..., "error": Optional[str]}
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize MCP Server.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.registry = FeatureRegistry(self.project_root)
        self.status_generator = StatusGenerator(self.project_root)

        # Available tools
        self.tools = {
            "feature_add": self.feature_add,
            "feature_complete": self.feature_complete,
            "feature_list": self.feature_list,
            "feature_get": self.feature_get,
            "feature_update": self.feature_update,
            "status_get": self.status_get,
            "status_generate": self.status_generate,
            "governance_check": self.governance_check,
            "governance_validate": self.governance_validate,
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools.

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "feature_add",
                "description": "Add a new feature to the project",
                "parameters": {
                    "name": "Feature name (required)",
                    "id": "Feature ID (optional)",
                    "status": "Status (default: planned)",
                    "priority": "Priority (default: medium)",
                }
            },
            {
                "name": "feature_complete",
                "description": "Mark a feature as complete",
                "parameters": {
                    "feature_id": "Feature ID to complete (required)",
                }
            },
            {
                "name": "feature_list",
                "description": "List all features, optionally filtered by status",
                "parameters": {
                    "status": "Filter by status (optional)",
                }
            },
            {
                "name": "feature_get",
                "description": "Get details of a specific feature",
                "parameters": {
                    "feature_id": "Feature ID (required)",
                }
            },
            {
                "name": "feature_update",
                "description": "Update a feature's properties",
                "parameters": {
                    "feature_id": "Feature ID (required)",
                    "updates": "Dictionary of updates (required)",
                }
            },
            {
                "name": "status_get",
                "description": "Get current project status and metrics",
                "parameters": {}
            },
            {
                "name": "status_generate",
                "description": "Generate STATUS.md from features.json",
                "parameters": {}
            },
            {
                "name": "governance_check",
                "description": "Run governance checks (pre-commit or pre-push)",
                "parameters": {
                    "check_type": "Type of check: pre_commit or pre_push (required)",
                }
            },
            {
                "name": "governance_validate",
                "description": "Validate governance configuration",
                "parameters": {}
            },
        ]

    # ===== Feature Management Tools =====

    def feature_add(self, **kwargs) -> Dict[str, Any]:
        """
        Add a new feature.

        Args:
            name: Feature name (required)
            description: Feature description (optional)
            id: Feature ID (optional)
            status: Status (optional, default: planned)
            priority: Priority (optional, default: medium)
            week: Week number (optional)
            build: Build identifier (optional)

        Returns:
            Response dict with added feature data
        """
        try:
            name = kwargs.get('name')
            if not name:
                return {"success": False, "error": "name is required"}

            # Call FeatureRegistry.add_feature with correct signature
            feature_id = kwargs.get('id', name.lower().replace(' ', '-'))
            description = kwargs.get('description', '')
            priority = kwargs.get('priority', 'medium')
            week = kwargs.get('week')
            build = kwargs.get('build')

            added = self.registry.add_feature(
                feature_id=feature_id,
                name=name,
                description=description,
                priority=priority,
                week=week,
                build=build
            )

            # Update status if provided (add_feature may not support it directly)
            status = kwargs.get('status')
            if status and status != 'planned':
                self.registry.update_feature(feature_id, status=status)
                # Get updated feature to return correct status
                added = self.registry.get_feature(feature_id)

            # Note: add_feature and update_feature already save to file
            # No need to call save() again

            return {
                "success": True,
                "result": added,
                "message": f"Added feature: {added['name']} ({added['id']})"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def feature_complete(self, **kwargs) -> Dict[str, Any]:
        """
        Mark a feature as complete.

        Args:
            feature_id: Feature ID (required)

        Returns:
            Response dict
        """
        try:
            feature_id = kwargs.get('feature_id')
            if not feature_id:
                return {"success": False, "error": "feature_id is required"}

            self.registry.complete_feature(feature_id)
            # Note: complete_feature already saves to file

            # Auto-generate STATUS.md
            self.status_generator.save()

            return {
                "success": True,
                "message": f"Completed feature: {feature_id}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def feature_list(self, **kwargs) -> Dict[str, Any]:
        """
        List all features.

        Args:
            status: Filter by status (optional)

        Returns:
            Response dict with features list
        """
        try:
            status = kwargs.get('status')
            features = self.registry.list_features(status=status)

            return {
                "success": True,
                "result": features,
                "count": len(features)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def feature_get(self, **kwargs) -> Dict[str, Any]:
        """
        Get a specific feature.

        Args:
            feature_id: Feature ID (required)

        Returns:
            Response dict with feature data
        """
        try:
            feature_id = kwargs.get('feature_id')
            if not feature_id:
                return {"success": False, "error": "feature_id is required"}

            feature = self.registry.get_feature(feature_id)
            if not feature:
                return {"success": False, "error": f"Feature not found: {feature_id}"}

            return {
                "success": True,
                "result": feature
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def feature_update(self, **kwargs) -> Dict[str, Any]:
        """
        Update a feature.

        Args:
            feature_id: Feature ID (required)
            updates: Dictionary of updates (required)

        Returns:
            Response dict
        """
        try:
            feature_id = kwargs.get('feature_id')
            updates = kwargs.get('updates')

            if not feature_id:
                return {"success": False, "error": "feature_id is required"}
            if not updates:
                return {"success": False, "error": "updates is required"}

            updated = self.registry.update_feature(feature_id, **updates)
            # Note: update_feature already saves to file

            if updated is None:
                return {"success": False, "error": f"Feature '{feature_id}' not found"}

            return {
                "success": True,
                "message": f"Updated feature: {feature_id}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== Status Tools =====

    def status_get(self, **kwargs) -> Dict[str, Any]:
        """
        Get current project status.

        Returns:
            Response dict with status and metrics
        """
        try:
            data = self.registry.load()

            return {
                "success": True,
                "result": {
                    "project": data.get('project'),
                    "version": data.get('version'),
                    "status": data.get('status'),
                    "metrics": data.get('metrics'),
                    "features": data.get('features', [])
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def status_generate(self, **kwargs) -> Dict[str, Any]:
        """
        Generate STATUS.md.

        Returns:
            Response dict with generated file path
        """
        try:
            self.status_generator.save()
            status_file = self.status_generator.status_file

            return {
                "success": True,
                "result": str(status_file),
                "message": f"Generated: {status_file}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== Governance Tools =====

    def governance_check(self, **kwargs) -> Dict[str, Any]:
        """
        Run governance checks.

        Args:
            check_type: Type of check (pre_commit or pre_push)

        Returns:
            Response dict with check results
        """
        try:
            check_type = kwargs.get('check_type')
            if check_type not in ['pre_commit', 'pre_push']:
                return {"success": False, "error": "check_type must be pre_commit or pre_push"}

            gm = GovernanceManager(self.project_root)
            if not gm.config_file.exists():
                return {
                    "success": True,
                    "message": "No governance configured"
                }

            gm.load()
            enforcer = GovernanceEnforcer(gm)

            if check_type == 'pre_commit':
                passed, failed = enforcer.check_pre_commit()
            else:
                passed, failed = enforcer.check_pre_push()

            return {
                "success": True,
                "result": {
                    "passed": passed,
                    "failed_checks": failed
                },
                "message": "All checks passed" if passed else f"Failed: {', '.join(failed)}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def governance_validate(self, **kwargs) -> Dict[str, Any]:
        """
        Validate governance configuration.

        Returns:
            Response dict with validation results
        """
        try:
            gm = GovernanceManager(self.project_root)
            if not gm.config_file.exists():
                return {
                    "success": True,
                    "message": "No governance file found"
                }

            gm.load()
            gm.validate()

            return {
                "success": True,
                "message": "Governance configuration valid"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== Request Handling =====

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.

        Args:
            request: Request dict with 'tool' and 'arguments'

        Returns:
            Response dict
        """
        tool_name = request.get('tool')
        arguments = request.get('arguments', {})

        if not tool_name:
            return {"success": False, "error": "tool is required"}

        if tool_name == 'list_tools':
            return {"success": True, "result": self.list_tools()}

        if tool_name not in self.tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        tool_func = self.tools[tool_name]
        return tool_func(**arguments)

    def serve_stdio(self):
        """
        Serve MCP requests over stdio (standard input/output).

        Reads JSON requests from stdin, writes JSON responses to stdout.
        """
        print("BuildRunner MCP Server started", file=sys.stderr)
        print("Ready to receive requests...", file=sys.stderr)

        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                error_response = {"success": False, "error": f"Invalid JSON: {e}"}
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                error_response = {"success": False, "error": f"Server error: {e}"}
                print(json.dumps(error_response), flush=True)


def main():
    """Main entry point for MCP server."""
    server = MCPServer()
    server.serve_stdio()


if __name__ == "__main__":
    main()
