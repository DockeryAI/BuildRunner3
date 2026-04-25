"""Audit BR3 attach drift for a target repository."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import typer

from core.installer.drift_detector import detect_drift

_AUDIT_PATH_ARGUMENT = typer.Argument(None, help="Project path to audit; defaults to the cwd")
_AUDIT_JSON_OPTION = typer.Option(False, "--json", help="Emit machine-readable JSON")


def register(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("audit", help="Audit BR3 attach drift")
    parser.add_argument("path", nargs="?", default=Path.cwd(), type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.set_defaults(func=run)
    return parser


def run(args: argparse.Namespace) -> int:
    target_path = Path(args.path).resolve()
    report = detect_drift(target_path)

    if getattr(args, "json_output", False):
        print(json.dumps([asdict(entry) for entry in report.entries], default=str))
        return 1 if report.has_drift else 0

    print(report.summary())
    for entry in report.entries:
        print(f"{entry.kind.value} {entry.path} {entry.note}")
    return 1 if report.has_drift else 0


def audit_command(
    path: Path = _AUDIT_PATH_ARGUMENT,
    json_output: bool = _AUDIT_JSON_OPTION,
) -> None:
    namespace = argparse.Namespace(path=path or Path.cwd(), json_output=json_output)
    raise typer.Exit(run(namespace))


__all__ = ["audit_command", "register", "run"]
