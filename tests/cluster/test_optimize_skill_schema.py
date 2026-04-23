"""
tests/cluster/test_optimize_skill_schema.py

Phase 1: Schema parsing tests for /optimize-skill rubrics.

Verifies:
  - valid rubric (website-build.yaml) parses cleanly
  - missing required keys reject
  - invalid threshold values reject (out-of-range)
  - invalid types reject
  - cross-field constraint: train_split + holdout_split == len(inputs)
  - skill-name match: rubric.skill matches filename stem
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent
SCHEMA_PATH = PROJECT_ROOT / ".buildrunner/skill-evals/_schema.yaml"
RUBRIC_PATH = PROJECT_ROOT / ".buildrunner/skill-evals/website-build.yaml"


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def validate_rubric(rubric: dict, schema: dict) -> list[str]:
    """Minimal validator mirroring the inline Python in /optimize-skill Step 1."""
    errors: list[str] = []
    fields = schema["fields"]

    type_map = {"str": str, "int": int, "float": (int, float), "bool": bool, "list": list}

    for key, spec in fields.items():
        if spec.get("required") and key not in rubric:
            errors.append(f"missing required key: {key}")
            continue
        if key not in rubric:
            continue
        v = rubric[key]
        expected = type_map.get(spec.get("type"))
        if expected and not isinstance(v, expected):
            errors.append(f"{key}: expected {spec['type']}, got {type(v).__name__}")
            continue
        if "min" in spec and isinstance(v, (int, float)) and v < spec["min"]:
            errors.append(f"{key}: {v} < min {spec['min']}")
        if "max" in spec and isinstance(v, (int, float)) and v > spec["max"]:
            errors.append(f"{key}: {v} > max {spec['max']}")
        if "min_len" in spec and hasattr(v, "__len__") and len(v) < spec["min_len"]:
            errors.append(f"{key}: len={len(v)} < min_len {spec['min_len']}")
        if "max_len" in spec and hasattr(v, "__len__") and len(v) > spec["max_len"]:
            errors.append(f"{key}: len={len(v)} > max_len {spec['max_len']}")

    # Cross-field: train + holdout == inputs
    if "train_split" in rubric and "holdout_split" in rubric and "inputs" in rubric:
        if rubric["train_split"] + rubric["holdout_split"] != len(rubric["inputs"]):
            errors.append(
                f"cross-field: train_split({rubric['train_split']}) + "
                f"holdout_split({rubric['holdout_split']}) != len(inputs)({len(rubric['inputs'])})"
            )

    return errors


@pytest.fixture
def schema():
    return load_yaml(SCHEMA_PATH)


@pytest.fixture
def valid_rubric():
    return load_yaml(RUBRIC_PATH)


def test_schema_loads(schema):
    assert schema["version"] == 1
    assert "fields" in schema
    assert "skill" in schema["fields"]


def test_valid_rubric_parses_clean(valid_rubric, schema):
    errors = validate_rubric(valid_rubric, schema)
    assert errors == [], f"website-build.yaml should validate clean, got: {errors}"


def test_missing_required_key_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    del rubric["skill"]
    errors = validate_rubric(rubric, schema)
    assert any("missing required key: skill" in e for e in errors)


def test_missing_inputs_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    del rubric["inputs"]
    errors = validate_rubric(rubric, schema)
    assert any("missing required key: inputs" in e for e in errors)


def test_too_few_inputs_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    rubric["inputs"] = rubric["inputs"][:5]
    errors = validate_rubric(rubric, schema)
    assert any("inputs:" in e and "min_len" in e for e in errors)


def test_too_few_criteria_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    rubric["criteria"] = rubric["criteria"][:2]
    errors = validate_rubric(rubric, schema)
    assert any("criteria:" in e and "min_len" in e for e in errors)


def test_too_many_criteria_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    extra = {"name": "extra", "question": "extra?"}
    rubric["criteria"] = rubric["criteria"] + [extra, extra, extra]
    errors = validate_rubric(rubric, schema)
    assert any("criteria:" in e and "max_len" in e for e in errors)


def test_pass_threshold_out_of_range_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    rubric["pass_threshold"] = 1.5
    errors = validate_rubric(rubric, schema)
    assert any("pass_threshold" in e and "max" in e for e in errors)


def test_max_iterations_zero_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    rubric["max_iterations"] = 0
    errors = validate_rubric(rubric, schema)
    assert any("max_iterations" in e and "min" in e for e in errors)


def test_budget_negative_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    rubric["budget_usd"] = -1.0
    errors = validate_rubric(rubric, schema)
    assert any("budget_usd" in e and "min" in e for e in errors)


def test_invalid_type_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    rubric["max_iterations"] = "three"  # string instead of int
    errors = validate_rubric(rubric, schema)
    assert any("max_iterations" in e and "expected" in e for e in errors)


def test_train_holdout_mismatch_rejected(valid_rubric, schema):
    rubric = copy.deepcopy(valid_rubric)
    rubric["train_split"] = 10
    rubric["holdout_split"] = 6  # 16 != 20
    errors = validate_rubric(rubric, schema)
    assert any("cross-field" in e for e in errors)


def test_skill_name_matches_filename(valid_rubric):
    assert valid_rubric["skill"] == RUBRIC_PATH.stem
