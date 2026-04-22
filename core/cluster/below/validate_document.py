#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "research_document.json"


def load_frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")

    end_marker = "\n---"
    end_index = content.find(end_marker, 4)
    if end_index == -1:
        raise ValueError("missing closing YAML frontmatter fence")

    frontmatter_text = content[4:end_index]
    data = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(data, dict):
        raise TypeError("frontmatter must be a mapping")
    return data


def validate_required(document: dict, schema: dict) -> None:
    required = schema.get("required", [])
    missing = [key for key in required if key not in document]
    if missing:
        raise ValueError(f"missing required keys: {', '.join(missing)}")


def validate_properties(document: dict, schema: dict) -> None:
    properties = schema.get("properties", {})
    for key, rules in properties.items():
        if key not in document:
            continue

        value = document[key]
        expected_type = rules.get("type")
        if expected_type == "string":
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a string")
            min_length = rules.get("minLength")
            if min_length is not None and len(value.strip()) < min_length:
                raise ValueError(f"{key} must be at least {min_length} character(s)")

        if expected_type == "array":
            if not isinstance(value, list):
                raise ValueError(f"{key} must be an array")
            min_items = rules.get("minItems")
            if min_items is not None and len(value) < min_items:
                raise ValueError(f"{key} must contain at least {min_items} item(s)")

        allowed = rules.get("enum")
        if allowed is not None and value not in allowed:
            raise ValueError(f"{key} must be one of: {', '.join(map(str, allowed))}")


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write(f"usage: {Path(sys.argv[0]).name} <path-to-md>\n")
        return 1

    target = Path(sys.argv[1])
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        document = load_frontmatter(target)
        validate_required(document, schema)
        validate_properties(document, schema)
    except Exception as exc:  # noqa: BLE001
        sys.stdout.write(f"schema violation: {exc}\n")
        return 1

    sys.stdout.write("OK\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
