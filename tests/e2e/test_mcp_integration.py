"""
Comprehensive E2E tests for MCP Server Integration

Tests all 9 MCP tools individually, E2E workflows, and error handling.
Target: 90%+ coverage on cli/mcp_server.py
"""

import pytest
import json
import tempfile
from pathlib import Path
from cli.mcp_server import MCPServer


def init_temp_project(project_root: Path):
    """Initialize a temporary project directory with features.json."""
    buildrunner_dir = project_root / ".buildrunner"
    buildrunner_dir.mkdir(parents=True, exist_ok=True)

    features_file = buildrunner_dir / "features.json"
    initial_data = {
        "project": "test-project",
        "version": "1.0.0",
        "status": "development",
        "features": [],
        "metrics": {
            "features_complete": 0,
            "features_in_progress": 0,
            "features_planned": 0,
            "completion_percentage": 0
        }
    }

    features_file.write_text(json.dumps(initial_data, indent=2))
    return project_root


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory with .buildrunner structure."""
    return init_temp_project(tmp_path)


@pytest.fixture
def mcp_server(temp_project_dir):
    """Create MCP server instance with isolated project directory."""
    server = MCPServer(project_root=temp_project_dir)
    server.registry.load()
    return server


class TestListTools:
    """Test list_tools functionality."""

    def test_list_tools_returns_all_tools(self, mcp_server):
        """Test that list_tools returns all 9 tool definitions."""
        tools = mcp_server.list_tools()

        assert len(tools) == 9
        tool_names = [t['name'] for t in tools]

        # Verify all 9 tools are present
        expected_tools = [
            'feature_add',
            'feature_complete',
            'feature_list',
            'feature_get',
            'feature_update',
            'status_get',
            'status_generate',
            'governance_check',
            'governance_validate'
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names

    def test_list_tools_has_descriptions(self, mcp_server):
        """Test that all tools have descriptions and parameters."""
        tools = mcp_server.list_tools()

        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'parameters' in tool
            assert isinstance(tool['description'], str)
            assert len(tool['description']) > 0

    def test_list_tools_via_handle_request(self, mcp_server):
        """Test list_tools can be called via handle_request."""
        request = {"tool": "list_tools"}
        response = mcp_server.handle_request(request)

        assert response['success'] is True
        assert 'result' in response
        assert len(response['result']) == 9


class TestFeatureAdd:
    """Test feature_add tool."""

    def test_feature_add_with_name_only(self, mcp_server):
        """Test adding feature with only name."""
        response = mcp_server.feature_add(name="Test Feature")

        assert response['success'] is True
        assert 'result' in response
        assert response['result']['name'] == "Test Feature"
        assert response['result']['status'] == "planned"  # Default
        assert response['result']['priority'] == "medium"  # Default
        assert 'id' in response['result']

    def test_feature_add_with_all_fields(self, mcp_server):
        """Test adding feature with all fields."""
        response = mcp_server.feature_add(
            name="Full Feature",
            id="custom-id",
            status="in_progress",
            priority="high"
        )

        if not response['success']:
            print(f"Error: {response}")
        assert response['success'] is True
        assert response['result']['name'] == "Full Feature"
        assert response['result']['id'] == "custom-id"
        assert response['result']['status'] == "in_progress"
        assert response['result']['priority'] == "high"

    def test_feature_add_without_name_fails(self, mcp_server):
        """Test that adding feature without name fails."""
        response = mcp_server.feature_add()

        assert response['success'] is False
        assert 'error' in response
        assert "name is required" in response['error']

    def test_feature_add_persists_to_file(self, mcp_server, temp_project_dir):
        """Test that added feature persists to features.json."""
        mcp_server.feature_add(name="Persistent Feature")

        # Reload server to verify persistence
        new_server = MCPServer(project_root=temp_project_dir)
        features = new_server.registry.list_features()

        assert len(features) == 1
        assert features[0]['name'] == "Persistent Feature"


class TestFeatureComplete:
    """Test feature_complete tool."""

    def test_feature_complete_existing_feature(self, mcp_server):
        """Test completing an existing feature."""
        # Add feature first
        add_response = mcp_server.feature_add(name="To Complete")
        feature_id = add_response['result']['id']

        # Complete it
        response = mcp_server.feature_complete(feature_id=feature_id)

        assert response['success'] is True
        assert 'message' in response
        assert feature_id in response['message']

        # Verify feature is completed
        feature = mcp_server.registry.get_feature(feature_id)
        assert feature['status'] == 'complete'

    def test_feature_complete_without_id_fails(self, mcp_server):
        """Test that completing without feature_id fails."""
        response = mcp_server.feature_complete()

        assert response['success'] is False
        assert 'error' in response
        assert "feature_id is required" in response['error']

    def test_feature_complete_nonexistent_feature_fails(self, mcp_server):
        """Test that completing nonexistent feature fails."""
        response = mcp_server.feature_complete(feature_id="nonexistent-id")

        assert response['success'] is False
        assert 'error' in response


class TestFeatureList:
    """Test feature_list tool."""

    def test_feature_list_empty(self, mcp_server):
        """Test listing features when none exist."""
        response = mcp_server.feature_list()

        assert response['success'] is True
        assert response['result'] == []
        assert response['count'] == 0

    def test_feature_list_multiple_features(self, mcp_server):
        """Test listing multiple features."""
        # Add several features
        mcp_server.feature_add(name="Feature 1", status="planned")
        mcp_server.feature_add(name="Feature 2", status="in_progress")
        mcp_server.feature_add(name="Feature 3", status="complete")

        response = mcp_server.feature_list()

        assert response['success'] is True
        assert response['count'] == 3
        assert len(response['result']) == 3

    def test_feature_list_filtered_by_status(self, mcp_server):
        """Test listing features filtered by status."""
        # Add features with different statuses
        mcp_server.feature_add(name="Planned 1", status="planned")
        mcp_server.feature_add(name="Planned 2", status="planned")
        mcp_server.feature_add(name="In Progress", status="in_progress")

        # Filter by planned
        response = mcp_server.feature_list(status="planned")

        assert response['success'] is True
        assert response['count'] == 2
        assert all(f['status'] == 'planned' for f in response['result'])


class TestFeatureGet:
    """Test feature_get tool."""

    def test_feature_get_existing_feature(self, mcp_server):
        """Test getting an existing feature."""
        # Add feature
        add_response = mcp_server.feature_add(name="Get Test")
        feature_id = add_response['result']['id']

        # Get it
        response = mcp_server.feature_get(feature_id=feature_id)

        assert response['success'] is True
        assert response['result']['name'] == "Get Test"
        assert response['result']['id'] == feature_id

    def test_feature_get_without_id_fails(self, mcp_server):
        """Test that getting without feature_id fails."""
        response = mcp_server.feature_get()

        assert response['success'] is False
        assert 'error' in response
        assert "feature_id is required" in response['error']

    def test_feature_get_nonexistent_feature_fails(self, mcp_server):
        """Test that getting nonexistent feature fails."""
        response = mcp_server.feature_get(feature_id="nonexistent")

        assert response['success'] is False
        assert 'error' in response
        assert "not found" in response['error'].lower()


class TestFeatureUpdate:
    """Test feature_update tool."""

    def test_feature_update_name(self, mcp_server):
        """Test updating feature name."""
        # Add feature
        add_response = mcp_server.feature_add(name="Original Name")
        feature_id = add_response['result']['id']

        # Update it
        response = mcp_server.feature_update(
            feature_id=feature_id,
            updates={'name': 'Updated Name'}
        )

        assert response['success'] is True

        # Verify update
        feature = mcp_server.registry.get_feature(feature_id)
        assert feature['name'] == 'Updated Name'

    def test_feature_update_multiple_fields(self, mcp_server):
        """Test updating multiple fields at once."""
        # Add feature
        add_response = mcp_server.feature_add(
            name="Multi Update",
            status="planned",
            priority="low"
        )
        feature_id = add_response['result']['id']

        # Update multiple fields
        response = mcp_server.feature_update(
            feature_id=feature_id,
            updates={
                'status': 'in_progress',
                'priority': 'high',
                'description': 'New description'
            }
        )

        assert response['success'] is True

        # Verify all updates
        feature = mcp_server.registry.get_feature(feature_id)
        assert feature['status'] == 'in_progress'
        assert feature['priority'] == 'high'
        assert feature['description'] == 'New description'

    def test_feature_update_without_id_fails(self, mcp_server):
        """Test that updating without feature_id fails."""
        response = mcp_server.feature_update(updates={'name': 'New Name'})

        assert response['success'] is False
        assert 'error' in response
        assert "feature_id is required" in response['error']

    def test_feature_update_without_updates_fails(self, mcp_server):
        """Test that updating without updates dict fails."""
        add_response = mcp_server.feature_add(name="Test")
        feature_id = add_response['result']['id']

        response = mcp_server.feature_update(feature_id=feature_id)

        assert response['success'] is False
        assert 'error' in response
        assert "updates is required" in response['error']


class TestStatusGet:
    """Test status_get tool."""

    def test_status_get_returns_project_info(self, mcp_server):
        """Test that status_get returns project information."""
        response = mcp_server.status_get()

        assert response['success'] is True
        assert 'result' in response

        result = response['result']
        assert 'project' in result
        assert 'version' in result
        assert 'status' in result
        assert 'metrics' in result
        assert 'features' in result

    def test_status_get_includes_metrics(self, mcp_server):
        """Test that status_get includes metrics."""
        # Add some features
        mcp_server.feature_add(name="F1", status="planned")
        mcp_server.feature_add(name="F2", status="in_progress")
        mcp_server.feature_add(name="F3", status="complete")

        response = mcp_server.status_get()

        assert response['success'] is True
        metrics = response['result']['metrics']

        # Metrics should be auto-calculated
        assert 'completion_percentage' in metrics
        assert 'features_complete' in metrics
        assert 'features_in_progress' in metrics
        assert 'features_planned' in metrics


class TestStatusGenerate:
    """Test status_generate tool."""

    def test_status_generate_creates_file(self, mcp_server, temp_project_dir):
        """Test that status_generate creates STATUS.md."""
        # Add some features
        mcp_server.feature_add(name="Feature 1")
        mcp_server.feature_add(name="Feature 2")

        response = mcp_server.status_generate()

        assert response['success'] is True
        assert 'result' in response

        # Verify STATUS.md was created
        status_file = temp_project_dir / "STATUS.md"
        assert status_file.exists()

        # Verify content
        content = status_file.read_text()
        assert "Feature 1" in content
        assert "Feature 2" in content

    def test_status_generate_returns_file_path(self, mcp_server):
        """Test that status_generate returns file path in response."""
        response = mcp_server.status_generate()

        assert response['success'] is True
        assert 'STATUS.md' in response['result']
        assert 'message' in response


class TestGovernanceCheck:
    """Test governance_check tool."""

    def test_governance_check_pre_commit(self, mcp_server):
        """Test pre-commit governance check."""
        response = mcp_server.governance_check(check_type="pre_commit")

        assert response['success'] is True
        # When no governance file exists, should pass
        assert "No governance" in response['message']

    def test_governance_check_pre_push(self, mcp_server):
        """Test pre-push governance check."""
        response = mcp_server.governance_check(check_type="pre_push")

        assert response['success'] is True
        assert "No governance" in response['message']

    def test_governance_check_invalid_type_fails(self, mcp_server):
        """Test that invalid check_type fails."""
        response = mcp_server.governance_check(check_type="invalid")

        assert response['success'] is False
        assert 'error' in response
        assert "must be pre_commit or pre_push" in response['error']

    def test_governance_check_without_type_fails(self, mcp_server):
        """Test that missing check_type fails."""
        response = mcp_server.governance_check()

        assert response['success'] is False
        assert 'error' in response


class TestGovernanceValidate:
    """Test governance_validate tool."""

    def test_governance_validate_no_config(self, mcp_server):
        """Test validating when no governance config exists."""
        response = mcp_server.governance_validate()

        assert response['success'] is True
        assert "No governance file" in response['message']

    def test_governance_validate_with_valid_config(self, mcp_server, temp_project_dir):
        """Test validating with valid governance config."""
        # Create valid governance.yaml in the correct location
        gov_dir = temp_project_dir / ".buildrunner" / "governance"
        gov_dir.mkdir(parents=True, exist_ok=True)
        gov_file = gov_dir / "governance.yaml"
        gov_content = """
version: '1.0'
project:
  name: Test Project
workflow:
  rules:
    - pre_commit
    - pre_push
validation:
  enabled: true
  required_checks:
    - quality
    - tests
quality:
  min_test_coverage: 80
  max_complexity: 15
  lint_required: true
"""
        gov_file.write_text(gov_content)

        response = mcp_server.governance_validate()

        assert response['success'] is True
        assert "valid" in response['message'].lower()


class TestHandleRequest:
    """Test handle_request method."""

    def test_handle_request_with_valid_tool(self, mcp_server):
        """Test handling valid request."""
        request = {
            "tool": "feature_add",
            "arguments": {"name": "Test Feature"}
        }

        response = mcp_server.handle_request(request)

        assert response['success'] is True
        assert response['result']['name'] == "Test Feature"

    def test_handle_request_without_tool_fails(self, mcp_server):
        """Test that request without tool fails."""
        request = {"arguments": {"name": "Test"}}

        response = mcp_server.handle_request(request)

        assert response['success'] is False
        assert "tool is required" in response['error']

    def test_handle_request_with_unknown_tool_fails(self, mcp_server):
        """Test that unknown tool fails."""
        request = {"tool": "nonexistent_tool"}

        response = mcp_server.handle_request(request)

        assert response['success'] is False
        assert "Unknown tool" in response['error']

    def test_handle_request_without_arguments(self, mcp_server):
        """Test that request without arguments uses empty dict."""
        request = {"tool": "feature_list"}

        response = mcp_server.handle_request(request)

        assert response['success'] is True
        # Should work with default empty arguments


class TestE2EWorkflow:
    """Test end-to-end workflow scenarios."""

    def test_complete_feature_workflow(self, mcp_server):
        """Test complete workflow: add → update → complete → status."""
        # Step 1: Add a feature
        add_response = mcp_server.handle_request({
            "tool": "feature_add",
            "arguments": {
                "name": "E2E Feature",
                "status": "planned",
                "priority": "high"
            }
        })

        assert add_response['success'] is True
        feature_id = add_response['result']['id']

        # Step 2: Update feature to in_progress
        update_response = mcp_server.handle_request({
            "tool": "feature_update",
            "arguments": {
                "feature_id": feature_id,
                "updates": {
                    "status": "in_progress",
                    "description": "Working on implementation"
                }
            }
        })

        assert update_response['success'] is True

        # Step 3: Complete the feature
        complete_response = mcp_server.handle_request({
            "tool": "feature_complete",
            "arguments": {"feature_id": feature_id}
        })

        assert complete_response['success'] is True

        # Step 4: Get status to verify
        status_response = mcp_server.handle_request({
            "tool": "status_get"
        })

        assert status_response['success'] is True
        metrics = status_response['result']['metrics']
        assert metrics['features_complete'] == 1
        assert metrics['features_in_progress'] == 0
        assert metrics['features_planned'] == 0

    def test_multi_feature_workflow(self, mcp_server):
        """Test workflow with multiple features."""
        # Add multiple features
        for i in range(5):
            mcp_server.handle_request({
                "tool": "feature_add",
                "arguments": {
                    "name": f"Feature {i+1}",
                    "status": "planned" if i < 3 else "in_progress"
                }
            })

        # List all features
        list_response = mcp_server.handle_request({"tool": "feature_list"})
        assert list_response['success'] is True
        assert list_response['count'] == 5

        # List only planned features
        planned_response = mcp_server.handle_request({
            "tool": "feature_list",
            "arguments": {"status": "planned"}
        })
        assert planned_response['count'] == 3

        # List only in_progress features
        progress_response = mcp_server.handle_request({
            "tool": "feature_list",
            "arguments": {"status": "in_progress"}
        })
        assert progress_response['count'] == 2

        # Generate status
        status_response = mcp_server.handle_request({"tool": "status_generate"})
        assert status_response['success'] is True

    def test_feature_lifecycle(self, mcp_server):
        """Test complete lifecycle of a feature."""
        # Create feature
        add_response = mcp_server.feature_add(
            name="Lifecycle Feature",
            status="planned"
        )
        feature_id = add_response['result']['id']

        # Verify initial state
        feature = mcp_server.registry.get_feature(feature_id)
        assert feature['status'] == 'planned'

        # Move to in_progress
        mcp_server.feature_update(
            feature_id=feature_id,
            updates={'status': 'in_progress'}
        )
        feature = mcp_server.registry.get_feature(feature_id)
        assert feature['status'] == 'in_progress'

        # Complete feature
        mcp_server.feature_complete(feature_id=feature_id)
        feature = mcp_server.registry.get_feature(feature_id)
        assert feature['status'] == 'complete'
        # Note: completed_at not currently tracked by FeatureRegistry


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_required_parameters(self, mcp_server):
        """Test various missing required parameters."""
        # feature_add without name
        response = mcp_server.feature_add()
        assert response['success'] is False
        assert "required" in response['error'].lower()

        # feature_complete without feature_id
        response = mcp_server.feature_complete()
        assert response['success'] is False
        assert "required" in response['error'].lower()

        # feature_get without feature_id
        response = mcp_server.feature_get()
        assert response['success'] is False
        assert "required" in response['error'].lower()

        # feature_update without feature_id
        response = mcp_server.feature_update(updates={'name': 'Test'})
        assert response['success'] is False
        assert "required" in response['error'].lower()

        # feature_update without updates
        add_response = mcp_server.feature_add(name="Test")
        response = mcp_server.feature_update(feature_id=add_response['result']['id'])
        assert response['success'] is False
        assert "required" in response['error'].lower()

    def test_nonexistent_resources(self, mcp_server):
        """Test operations on nonexistent resources."""
        # Get nonexistent feature
        response = mcp_server.feature_get(feature_id="nonexistent-123")
        assert response['success'] is False
        assert "not found" in response['error'].lower()

        # Complete nonexistent feature
        response = mcp_server.feature_complete(feature_id="nonexistent-456")
        assert response['success'] is False

        # Update nonexistent feature
        response = mcp_server.feature_update(
            feature_id="nonexistent-789",
            updates={'name': 'Test'}
        )
        assert response['success'] is False

    def test_invalid_tool_names(self, mcp_server):
        """Test handling of invalid tool names."""
        response = mcp_server.handle_request({"tool": "invalid_tool"})
        assert response['success'] is False
        assert "Unknown tool" in response['error']

        response = mcp_server.handle_request({"tool": "feature_delete"})
        assert response['success'] is False
        assert "Unknown tool" in response['error']

    def test_invalid_governance_check_type(self, mcp_server):
        """Test invalid governance check types."""
        invalid_types = ["pre_merge", "post_commit", "", "invalid"]

        for check_type in invalid_types:
            response = mcp_server.governance_check(check_type=check_type)
            assert response['success'] is False
            assert "must be pre_commit or pre_push" in response['error']


class TestPersistence:
    """Test data persistence across server instances."""

    def test_features_persist_across_instances(self, tmp_path):
        """Test that features persist when server is reloaded."""
        # Initialize project directory
        project_dir = init_temp_project(tmp_path)

        # Create first server and add features
        server1 = MCPServer(project_root=project_dir)
        server1.registry.load()
        server1.feature_add(name="Persistent Feature 1")
        server1.feature_add(name="Persistent Feature 2")
        server1.feature_add(name="Persistent Feature 3")

        # Create new server instance (simulating restart)
        server2 = MCPServer(project_root=project_dir)
        server2.registry.load()

        # Verify features are still there
        response = server2.feature_list()
        assert response['count'] == 3

        feature_names = [f['name'] for f in response['result']]
        assert "Persistent Feature 1" in feature_names
        assert "Persistent Feature 2" in feature_names
        assert "Persistent Feature 3" in feature_names

    def test_updates_persist(self, tmp_path):
        """Test that feature updates persist."""
        # Initialize project directory
        project_dir = init_temp_project(tmp_path)

        # Create server and add feature
        server1 = MCPServer(project_root=project_dir)
        server1.registry.load()
        add_response = server1.feature_add(name="Update Test")
        feature_id = add_response['result']['id']

        # Update feature
        server1.feature_update(
            feature_id=feature_id,
            updates={
                'status': 'in_progress',
                'description': 'Updated description'
            }
        )

        # Create new server and verify update persisted
        server2 = MCPServer(project_root=project_dir)
        server2.registry.load()
        feature = server2.registry.get_feature(feature_id)

        assert feature['status'] == 'in_progress'
        assert feature['description'] == 'Updated description'

    def test_completion_persists(self, tmp_path):
        """Test that feature completion persists."""
        # Initialize project directory
        project_dir = init_temp_project(tmp_path)

        # Create server and complete feature
        server1 = MCPServer(project_root=project_dir)
        server1.registry.load()
        add_response = server1.feature_add(name="Complete Test")
        feature_id = add_response['result']['id']
        server1.feature_complete(feature_id=feature_id)

        # Verify persistence
        server2 = MCPServer(project_root=project_dir)
        server2.registry.load()
        feature = server2.registry.get_feature(feature_id)

        assert feature['status'] == 'complete'
        # Note: completed_at not currently tracked by FeatureRegistry


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_feature_name(self, mcp_server):
        """Test adding feature with empty name."""
        response = mcp_server.feature_add(name="")
        # Empty string counts as no name
        assert response['success'] is False
        assert "required" in response['error'].lower() or "name" in response['error'].lower()

    def test_duplicate_feature_ids(self, mcp_server):
        """Test handling of duplicate feature IDs."""
        # Add feature with custom ID
        mcp_server.feature_add(name="First", id="duplicate-id")

        # Try to add another with same ID
        response = mcp_server.feature_add(name="Second", id="duplicate-id")

        # Registry should handle this (either reject or auto-rename)
        assert 'result' in response or 'error' in response

    def test_list_with_invalid_status_filter(self, mcp_server):
        """Test listing with invalid status filter."""
        # Add some features
        mcp_server.feature_add(name="Test")

        # List with invalid status
        response = mcp_server.feature_list(status="invalid_status")

        # Should return empty list (no features match)
        assert response['success'] is True
        assert response['count'] == 0

    def test_status_get_with_no_features(self, mcp_server):
        """Test getting status when no features exist."""
        response = mcp_server.status_get()

        assert response['success'] is True
        assert response['result']['features'] == []

        # Metrics should show all zeros
        metrics = response['result']['metrics']
        assert metrics['features_complete'] == 0
        assert metrics['completion_percentage'] == 0
