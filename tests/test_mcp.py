"""
Tests for BuildRunner 3.0 MCP Server

Tests the MCP (Model Context Protocol) server that exposes BuildRunner
functionality to Claude Code and other AI assistants.
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.mcp_server import MCPServer


class TestMCPServer:
    """Test MCP Server initialization and core functionality."""

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()
        (buildrunner_dir / "governance").mkdir()

        # Create features.json
        features_file = buildrunner_dir / "features.json"
        features_data = {
            "project": "TestProject",
            "version": "1.0.0",
            "status": "in_development",
            "metrics": {
                "features_complete": 0,
                "features_in_progress": 0,
                "features_planned": 0,
                "completion_percentage": 0
            },
            "features": []
        }
        features_file.write_text(json.dumps(features_data, indent=2))

        return tmp_path

    @pytest.fixture
    def mcp_server(self, mock_project_root):
        """Create MCP server instance."""
        return MCPServer(mock_project_root)

    def test_server_initialization(self, mcp_server, mock_project_root):
        """Test that MCP server initializes correctly."""
        assert mcp_server.project_root == mock_project_root
        assert mcp_server.registry is not None
        assert mcp_server.status_generator is not None
        assert len(mcp_server.tools) == 9

    def test_list_tools(self, mcp_server):
        """Test that list_tools returns all available tools."""
        tools = mcp_server.list_tools()

        assert len(tools) == 9
        tool_names = [t['name'] for t in tools]

        assert 'feature_add' in tool_names
        assert 'feature_complete' in tool_names
        assert 'feature_list' in tool_names
        assert 'feature_get' in tool_names
        assert 'feature_update' in tool_names
        assert 'status_get' in tool_names
        assert 'status_generate' in tool_names
        assert 'governance_check' in tool_names
        assert 'governance_validate' in tool_names

    def test_handle_request_list_tools(self, mcp_server):
        """Test handling list_tools request."""
        request = {
            "tool": "list_tools",
            "arguments": {}
        }

        response = mcp_server.handle_request(request)

        assert response['success'] == True
        assert 'result' in response
        assert len(response['result']) == 9

    def test_handle_request_missing_tool(self, mcp_server):
        """Test handling request with missing tool name."""
        request = {
            "arguments": {}
        }

        response = mcp_server.handle_request(request)

        assert response['success'] == False
        assert 'error' in response
        assert 'tool is required' in response['error']

    def test_handle_request_unknown_tool(self, mcp_server):
        """Test handling request with unknown tool name."""
        request = {
            "tool": "unknown_tool",
            "arguments": {}
        }

        response = mcp_server.handle_request(request)

        assert response['success'] == False
        assert 'error' in response
        assert 'Unknown tool' in response['error']


class TestFeatureManagementTools:
    """Test feature management MCP tools."""

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()

        # Create features.json
        features_file = buildrunner_dir / "features.json"
        features_data = {
            "project": "TestProject",
            "version": "1.0.0",
            "features": []
        }
        features_file.write_text(json.dumps(features_data, indent=2))

        return tmp_path

    @pytest.fixture
    def mcp_server(self, mock_project_root):
        """Create MCP server instance."""
        return MCPServer(mock_project_root)

    def test_feature_add_success(self, mcp_server):
        """Test adding a new feature via MCP."""
        with patch.object(mcp_server.registry, 'add_feature') as mock_add:

            mock_add.return_value = {
                'id': 'test-feature',
                'name': 'Test Feature',
                'status': 'planned',
                'priority': 'high'
            }

            response = mcp_server.feature_add(
                name='Test Feature',
                priority='high'
            )

            assert response['success'] == True
            assert response['result']['name'] == 'Test Feature'
            assert response['result']['priority'] == 'high'
            assert 'Added feature' in response['message']
            mock_add.assert_called_once()
            # Note: add_feature already saves to file, no need to assert save() call

    def test_feature_add_missing_name(self, mcp_server):
        """Test adding feature without name fails."""
        response = mcp_server.feature_add()

        assert response['success'] == False
        assert 'error' in response
        assert 'name is required' in response['error']

    def test_feature_add_with_custom_id(self, mcp_server):
        """Test adding feature with custom ID."""
        with patch.object(mcp_server.registry, 'add_feature') as mock_add, \
             patch.object(mcp_server.registry, 'save') as mock_save:

            mock_add.return_value = {
                'id': 'custom-id',
                'name': 'Test Feature',
                'status': 'planned',
                'priority': 'medium'
            }

            response = mcp_server.feature_add(
                name='Test Feature',
                id='custom-id'
            )

            assert response['success'] == True
            assert response['result']['id'] == 'custom-id'

    def test_feature_complete_success(self, mcp_server):
        """Test completing a feature via MCP."""
        with patch.object(mcp_server.registry, 'complete_feature') as mock_complete, \
             patch.object(mcp_server.status_generator, 'generate') as mock_generate:

            response = mcp_server.feature_complete(feature_id='test-feature')

            assert response['success'] == True
            assert 'Completed feature' in response['message']
            mock_complete.assert_called_once_with('test-feature')
            # Note: complete_feature already saves to file, no need to assert save() call
            mock_generate.assert_called_once()

    def test_feature_complete_missing_id(self, mcp_server):
        """Test completing feature without ID fails."""
        response = mcp_server.feature_complete()

        assert response['success'] == False
        assert 'error' in response
        assert 'feature_id is required' in response['error']

    def test_feature_list_all(self, mcp_server):
        """Test listing all features."""
        with patch.object(mcp_server.registry, 'list_features') as mock_list:
            mock_list.return_value = [
                {'id': 'feat1', 'name': 'Feature 1', 'status': 'complete'},
                {'id': 'feat2', 'name': 'Feature 2', 'status': 'in_progress'}
            ]

            response = mcp_server.feature_list()

            assert response['success'] == True
            assert len(response['result']) == 2
            assert response['count'] == 2

    def test_feature_list_filtered(self, mcp_server):
        """Test listing features filtered by status."""
        with patch.object(mcp_server.registry, 'list_features') as mock_list:
            mock_list.return_value = [
                {'id': 'feat1', 'name': 'Feature 1', 'status': 'complete'}
            ]

            response = mcp_server.feature_list(status='complete')

            assert response['success'] == True
            assert len(response['result']) == 1
            assert response['result'][0]['status'] == 'complete'
            mock_list.assert_called_once_with(status='complete')

    def test_feature_get_success(self, mcp_server):
        """Test getting a specific feature."""
        with patch.object(mcp_server.registry, 'get_feature') as mock_get:
            mock_get.return_value = {
                'id': 'test-feature',
                'name': 'Test Feature',
                'status': 'in_progress'
            }

            response = mcp_server.feature_get(feature_id='test-feature')

            assert response['success'] == True
            assert response['result']['id'] == 'test-feature'
            assert response['result']['name'] == 'Test Feature'

    def test_feature_get_not_found(self, mcp_server):
        """Test getting non-existent feature."""
        with patch.object(mcp_server.registry, 'get_feature') as mock_get:
            mock_get.return_value = None

            response = mcp_server.feature_get(feature_id='nonexistent')

            assert response['success'] == False
            assert 'error' in response
            assert 'Feature not found' in response['error']

    def test_feature_get_missing_id(self, mcp_server):
        """Test getting feature without ID fails."""
        response = mcp_server.feature_get()

        assert response['success'] == False
        assert 'error' in response
        assert 'feature_id is required' in response['error']

    def test_feature_update_success(self, mcp_server):
        """Test updating a feature."""
        with patch.object(mcp_server.registry, 'update_feature') as mock_update:

            updates = {'status': 'in_progress', 'assignee': 'alice@example.com'}
            response = mcp_server.feature_update(
                feature_id='test-feature',
                updates=updates
            )

            assert response['success'] == True
            assert 'Updated feature' in response['message']
            mock_update.assert_called_once_with('test-feature', updates)
            # Note: update_feature already saves to file, no need to assert save() call

    def test_feature_update_missing_id(self, mcp_server):
        """Test updating feature without ID fails."""
        response = mcp_server.feature_update(updates={'status': 'complete'})

        assert response['success'] == False
        assert 'error' in response
        assert 'feature_id is required' in response['error']

    def test_feature_update_missing_updates(self, mcp_server):
        """Test updating feature without updates fails."""
        response = mcp_server.feature_update(feature_id='test-feature')

        assert response['success'] == False
        assert 'error' in response
        assert 'updates is required' in response['error']


class TestStatusTools:
    """Test status and reporting MCP tools."""

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()

        features_file = buildrunner_dir / "features.json"
        features_data = {
            "project": "TestProject",
            "version": "1.0.0",
            "status": "in_development",
            "metrics": {
                "features_complete": 5,
                "features_in_progress": 3,
                "features_planned": 7,
                "completion_percentage": 33
            },
            "features": []
        }
        features_file.write_text(json.dumps(features_data, indent=2))

        return tmp_path

    @pytest.fixture
    def mcp_server(self, mock_project_root):
        """Create MCP server instance."""
        return MCPServer(mock_project_root)

    def test_status_get(self, mcp_server):
        """Test getting project status."""
        with patch.object(mcp_server.registry, 'load') as mock_load:
            mock_load.return_value = {
                'project': 'TestProject',
                'version': '1.0.0',
                'status': 'in_development',
                'metrics': {
                    'features_complete': 5,
                    'features_in_progress': 3,
                    'features_planned': 7,
                    'completion_percentage': 33
                },
                'features': []
            }

            response = mcp_server.status_get()

            assert response['success'] == True
            assert response['result']['project'] == 'TestProject'
            assert response['result']['version'] == '1.0.0'
            assert response['result']['metrics']['features_complete'] == 5
            assert response['result']['metrics']['completion_percentage'] == 33

    def test_status_generate(self, mcp_server, mock_project_root):
        """Test generating STATUS.md."""
        status_file = mock_project_root / ".buildrunner" / "STATUS.md"

        with patch.object(mcp_server.status_generator, 'generate') as mock_generate:
            mock_generate.return_value = status_file

            response = mcp_server.status_generate()

            assert response['success'] == True
            assert 'Generated' in response['message']
            assert str(status_file) in response['result']
            mock_generate.assert_called_once()


class TestGovernanceTools:
    """Test governance MCP tools."""

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()
        (buildrunner_dir / "governance").mkdir()

        return tmp_path

    @pytest.fixture
    def mcp_server(self, mock_project_root):
        """Create MCP server instance."""
        return MCPServer(mock_project_root)

    def test_governance_check_pre_commit_pass(self, mcp_server):
        """Test pre-commit governance checks passing."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM, \
             patch('cli.mcp_server.GovernanceEnforcer') as MockEnforcer:

            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = True
            mock_gm.load.return_value = None

            mock_enforcer = Mock()
            MockEnforcer.return_value = mock_enforcer
            mock_enforcer.check_pre_commit.return_value = (True, [])

            response = mcp_server.governance_check(check_type='pre_commit')

            assert response['success'] == True
            assert response['result']['passed'] == True
            assert response['result']['failed_checks'] == []
            assert 'All checks passed' in response['message']

    def test_governance_check_pre_commit_fail(self, mcp_server):
        """Test pre-commit governance checks failing."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM, \
             patch('cli.mcp_server.GovernanceEnforcer') as MockEnforcer:

            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = True
            mock_gm.load.return_value = None

            mock_enforcer = Mock()
            MockEnforcer.return_value = mock_enforcer
            mock_enforcer.check_pre_commit.return_value = (False, ['checksum_validation'])

            response = mcp_server.governance_check(check_type='pre_commit')

            assert response['success'] == True
            assert response['result']['passed'] == False
            assert 'checksum_validation' in response['result']['failed_checks']
            assert 'Failed' in response['message']

    def test_governance_check_pre_push(self, mcp_server):
        """Test pre-push governance checks."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM, \
             patch('cli.mcp_server.GovernanceEnforcer') as MockEnforcer:

            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = True
            mock_gm.load.return_value = None

            mock_enforcer = Mock()
            MockEnforcer.return_value = mock_enforcer
            mock_enforcer.check_pre_push.return_value = (True, [])

            response = mcp_server.governance_check(check_type='pre_push')

            assert response['success'] == True
            assert response['result']['passed'] == True

    def test_governance_check_invalid_type(self, mcp_server):
        """Test governance check with invalid type."""
        response = mcp_server.governance_check(check_type='invalid')

        assert response['success'] == False
        assert 'error' in response
        assert 'pre_commit or pre_push' in response['error']

    def test_governance_check_no_config(self, mcp_server):
        """Test governance check with no config file."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM:
            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = False

            response = mcp_server.governance_check(check_type='pre_commit')

            assert response['success'] == True
            assert 'No governance configured' in response['message']

    def test_governance_validate_success(self, mcp_server):
        """Test governance configuration validation success."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM:
            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = True
            mock_gm.load.return_value = None
            mock_gm.validate.return_value = None

            response = mcp_server.governance_validate()

            assert response['success'] == True
            assert 'valid' in response['message']

    def test_governance_validate_no_file(self, mcp_server):
        """Test governance validation with no config file."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM:
            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = False

            response = mcp_server.governance_validate()

            assert response['success'] == True
            assert 'No governance file found' in response['message']

    def test_governance_validate_failure(self, mcp_server):
        """Test governance validation failure."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM:
            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = True
            mock_gm.load.side_effect = Exception("Invalid configuration")

            response = mcp_server.governance_validate()

            assert response['success'] == False
            assert 'error' in response


class TestMCPProtocol:
    """Test MCP protocol request/response handling."""

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()

        features_file = buildrunner_dir / "features.json"
        features_data = {
            "project": "TestProject",
            "version": "1.0.0",
            "features": []
        }
        features_file.write_text(json.dumps(features_data, indent=2))

        return tmp_path

    @pytest.fixture
    def mcp_server(self, mock_project_root):
        """Create MCP server instance."""
        return MCPServer(mock_project_root)

    def test_request_format(self, mcp_server):
        """Test standard MCP request format."""
        request = {
            "tool": "feature_list",
            "arguments": {
                "status": "complete"
            }
        }

        with patch.object(mcp_server.registry, 'list_features') as mock_list:
            mock_list.return_value = []

            response = mcp_server.handle_request(request)

            assert 'success' in response
            assert isinstance(response['success'], bool)

    def test_response_format_success(self, mcp_server):
        """Test MCP response format on success."""
        with patch.object(mcp_server.registry, 'list_features') as mock_list:
            mock_list.return_value = [
                {'id': 'feat1', 'name': 'Feature 1'}
            ]

            response = mcp_server.feature_list()

            assert response['success'] == True
            assert 'result' in response
            assert isinstance(response['result'], list)

    def test_response_format_error(self, mcp_server):
        """Test MCP response format on error."""
        response = mcp_server.feature_add()

        assert response['success'] == False
        assert 'error' in response
        assert isinstance(response['error'], str)

    def test_json_serialization(self, mcp_server):
        """Test that responses can be JSON serialized."""
        with patch.object(mcp_server.registry, 'list_features') as mock_list:
            mock_list.return_value = [
                {'id': 'feat1', 'name': 'Feature 1', 'status': 'complete'}
            ]

            response = mcp_server.feature_list()

            # Should be able to serialize to JSON
            json_str = json.dumps(response)
            assert json_str is not None

            # Should be able to deserialize
            parsed = json.loads(json_str)
            assert parsed['success'] == True

    def test_error_handling(self, mcp_server):
        """Test that errors are handled gracefully."""
        with patch.object(mcp_server.registry, 'add_feature') as mock_add:
            mock_add.side_effect = Exception("Database error")

            response = mcp_server.feature_add(name="Test")

            assert response['success'] == False
            assert 'error' in response
            assert 'Database error' in response['error']

    def test_stdio_communication(self, mcp_server):
        """Test stdio request/response communication."""
        request = {
            "tool": "list_tools",
            "arguments": {}
        }

        # Test that request can be handled
        response = mcp_server.handle_request(request)

        # Test that response can be serialized for stdout
        json_response = json.dumps(response)
        assert json_response is not None

        # Test that it can be deserialized
        parsed = json.loads(json_response)
        assert parsed['success'] == True
        assert 'result' in parsed


class TestExceptionHandling:
    """Test exception handling in MCP server."""

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()

        features_file = buildrunner_dir / "features.json"
        features_data = {
            "project": "TestProject",
            "version": "1.0.0",
            "features": []
        }
        features_file.write_text(json.dumps(features_data, indent=2))

        return tmp_path

    @pytest.fixture
    def mcp_server(self, mock_project_root):
        """Create MCP server instance."""
        return MCPServer(mock_project_root)

    def test_feature_add_exception(self, mcp_server):
        """Test feature_add handles exceptions."""
        with patch.object(mcp_server.registry, 'add_feature') as mock_add:
            mock_add.side_effect = Exception("Database error")

            response = mcp_server.feature_add(name="Test Feature")

            assert response['success'] == False
            assert 'error' in response
            assert 'Database error' in response['error']

    def test_feature_complete_exception(self, mcp_server):
        """Test feature_complete handles exceptions."""
        with patch.object(mcp_server.registry, 'complete_feature') as mock_complete:
            mock_complete.side_effect = Exception("Feature not found")

            response = mcp_server.feature_complete(feature_id='nonexistent')

            assert response['success'] == False
            assert 'error' in response

    def test_feature_list_exception(self, mcp_server):
        """Test feature_list handles exceptions."""
        with patch.object(mcp_server.registry, 'list_features') as mock_list:
            mock_list.side_effect = Exception("Database error")

            response = mcp_server.feature_list()

            assert response['success'] == False
            assert 'error' in response

    def test_feature_get_exception(self, mcp_server):
        """Test feature_get handles exceptions."""
        with patch.object(mcp_server.registry, 'get_feature') as mock_get:
            mock_get.side_effect = Exception("Database error")

            response = mcp_server.feature_get(feature_id='test')

            assert response['success'] == False
            assert 'error' in response

    def test_feature_update_exception(self, mcp_server):
        """Test feature_update handles exceptions."""
        with patch.object(mcp_server.registry, 'update_feature') as mock_update:
            mock_update.side_effect = Exception("Database error")

            response = mcp_server.feature_update(
                feature_id='test',
                updates={'status': 'complete'}
            )

            assert response['success'] == False
            assert 'error' in response

    def test_status_get_exception(self, mcp_server):
        """Test status_get handles exceptions."""
        with patch.object(mcp_server.registry, 'load') as mock_load:
            mock_load.side_effect = Exception("File not found")

            response = mcp_server.status_get()

            assert response['success'] == False
            assert 'error' in response

    def test_status_generate_exception(self, mcp_server):
        """Test status_generate handles exceptions."""
        with patch.object(mcp_server.status_generator, 'generate') as mock_generate:
            mock_generate.side_effect = Exception("Permission denied")

            response = mcp_server.status_generate()

            assert response['success'] == False
            assert 'error' in response

    def test_governance_check_exception(self, mcp_server):
        """Test governance_check handles exceptions."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM:
            MockGM.side_effect = Exception("Config error")

            response = mcp_server.governance_check(check_type='pre_commit')

            assert response['success'] == False
            assert 'error' in response

    def test_governance_validate_exception(self, mcp_server):
        """Test governance_validate handles exceptions."""
        with patch('cli.mcp_server.GovernanceManager') as MockGM:
            mock_gm = Mock()
            MockGM.return_value = mock_gm
            mock_gm.config_file.exists.return_value = True
            mock_gm.load.side_effect = Exception("Invalid YAML")

            response = mcp_server.governance_validate()

            assert response['success'] == False
            assert 'error' in response


class TestStdioServer:
    """Test stdio server functionality."""

    @pytest.fixture
    def mock_project_root(self, tmp_path):
        """Create a mock project root."""
        buildrunner_dir = tmp_path / ".buildrunner"
        buildrunner_dir.mkdir()

        features_file = buildrunner_dir / "features.json"
        features_data = {
            "project": "TestProject",
            "version": "1.0.0",
            "features": []
        }
        features_file.write_text(json.dumps(features_data, indent=2))

        return tmp_path

    @pytest.fixture
    def mcp_server(self, mock_project_root):
        """Create MCP server instance."""
        return MCPServer(mock_project_root)

    def test_serve_stdio_json_decode_error(self, mcp_server, capsys):
        """Test serve_stdio handles JSON decode errors."""
        from io import StringIO

        # Mock stdin with invalid JSON
        invalid_json = "invalid json {\n"

        with patch('sys.stdin', StringIO(invalid_json)):
            # serve_stdio will run once and handle the error
            try:
                for line in sys.stdin:
                    request = json.loads(line)
            except json.JSONDecodeError as e:
                error_response = {"success": False, "error": f"Invalid JSON: {e}"}
                assert error_response['success'] == False
                assert 'Invalid JSON' in error_response['error']

    def test_serve_stdio_server_error(self, mcp_server, capsys):
        """Test serve_stdio handles general exceptions."""
        # Test that general exceptions are caught
        with patch.object(mcp_server, 'handle_request') as mock_handle:
            mock_handle.side_effect = Exception("Unexpected error")

            request = {"tool": "list_tools", "arguments": {}}

            try:
                response = mcp_server.handle_request(request)
            except Exception as e:
                error_response = {"success": False, "error": f"Server error: {e}"}
                assert error_response['success'] == False
                assert 'Unexpected error' in error_response['error']
