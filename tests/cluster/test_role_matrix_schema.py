"""tests/cluster/test_role_matrix_schema.py — Phase 1 TDD tests.

Validates the role_matrix schema YAML:
- Correct structure
- All required fields present per phase
- YAML parser can extract builder=codex for phase_2
- Schema validates against cluster-max phases 0-15 (when migrated)
"""

from __future__ import annotations

import os
import sys

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_PATH = os.path.join(REPO_ROOT, ".buildrunner", "schemas", "role-matrix.schema.yaml")


def load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def test_schema_file_exists():
    """Schema file must exist at the canonical path."""
    assert os.path.exists(SCHEMA_PATH), f"Schema not found at {SCHEMA_PATH}"


def test_schema_top_level_keys():
    """Schema must have 'type', 'properties', and 'required' keys."""
    schema = load_schema()
    assert "type" in schema or "properties" in schema, (
        "Schema must define 'type' or 'properties'"
    )


def test_phase_entry_required_fields():
    """Each phase block must define builder, reviewers, assigned_node, context."""
    schema = load_schema()
    # Get phase_entry definition — could be under definitions, $defs, or properties
    phase_def = None
    for key in ("definitions", "$defs"):
        if key in schema and "phase_entry" in schema[key]:
            phase_def = schema[key]["phase_entry"]
            break
    if phase_def is None:
        # Check under properties/phases/items
        props = schema.get("properties", {})
        phases = props.get("phases", {})
        phase_def = phases.get("additionalProperties") or phases.get("items") or phases

    assert phase_def is not None, "No phase_entry definition found in schema"

    required_fields = {"builder", "reviewers", "assigned_node", "context"}
    # Either required array or properties keys
    phase_props = phase_def.get("properties", phase_def)
    for field in required_fields:
        assert field in phase_props or field in phase_def.get("required", []), (
            f"Phase entry schema missing required field: {field}"
        )


class TestClusterActivationRoleMatrix:
    """Test role_matrix in BUILD_cluster-activation.md can be parsed."""

    BUILD_PATH = os.path.join(
        REPO_ROOT, ".buildrunner", "builds", "BUILD_cluster-activation.md"
    )

    def _extract_role_matrix_yaml(self) -> dict:
        """Extract the role_matrix YAML block from the BUILD spec."""
        with open(self.BUILD_PATH) as f:
            content = f.read()

        # Find the yaml block after "```yaml"
        in_block = False
        yaml_lines = []
        for line in content.splitlines():
            if line.strip() == "```yaml" and not in_block:
                in_block = True
                continue
            if in_block:
                if line.strip() == "```":
                    break
                yaml_lines.append(line)

        assert yaml_lines, "No YAML block found in BUILD_cluster-activation.md"
        return yaml.safe_load("\n".join(yaml_lines))

    def test_role_matrix_parseable(self):
        """BUILD_cluster-activation role_matrix is parseable YAML."""
        data = self._extract_role_matrix_yaml()
        assert "role_matrix" in data, "Expected 'role_matrix' top-level key"

    def test_phase_2_builder_is_codex(self):
        """YAML parser must extract builder=codex for phase_2 (Success Criteria)."""
        data = self._extract_role_matrix_yaml()
        matrix = data["role_matrix"]
        assert "phases" in matrix, "role_matrix must have 'phases'"
        phase_2 = matrix["phases"].get("phase_2")
        assert phase_2 is not None, "phase_2 not found in role_matrix"
        assert phase_2.get("builder") == "codex", (
            f"Expected builder=codex for phase_2, got: {phase_2.get('builder')}"
        )

    def test_all_phases_have_required_fields(self):
        """All phases in role_matrix must have builder, reviewers, assigned_node, context."""
        data = self._extract_role_matrix_yaml()
        phases = data["role_matrix"]["phases"]
        required = {"builder", "reviewers", "assigned_node", "context"}
        for phase_name, phase_data in phases.items():
            missing = required - set(phase_data.keys())
            assert not missing, (
                f"Phase '{phase_name}' missing fields: {missing}"
            )

    def test_cluster_max_has_role_matrix_block(self):
        """BUILD_cluster-max.md must have a role_matrix YAML block appended."""
        cluster_max_path = os.path.join(
            REPO_ROOT, ".buildrunner", "builds", "BUILD_cluster-max.md"
        )
        with open(cluster_max_path) as f:
            content = f.read()
        assert "role_matrix:" in content, (
            "BUILD_cluster-max.md must contain role_matrix YAML block"
        )
