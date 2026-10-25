"""`validate` sub-command: standalone B2 project validation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .. import product_identity as pid
from ..validation import validate
from ..validation.report import Report, to_json


def add_parser(sub: "argparse._SubParsersAction") -> None:
    parser = sub.add_parser("validate", help="Validate a generated Mule project offline.")
    parser.add_argument("--project", required=True, help="Absolute generated project directory.")
    parser.add_argument("--bundle", required=True, help="Absolute design_bundle.v1 JSON file.")
    parser.add_argument("--policy", required=True, help="Absolute validation_policy.v1 JSON file.")
    parser.add_argument("--naming-contract", help="Absolute naming_contract.v1 JSON file; enables the naming checks.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, **_: Any) -> int:
    try:
        if not os.path.isabs(args.project) or not os.path.isdir(args.project):
            raise ValueError("project must be an absolute directory")
        bundle = _load(args.bundle)
        policy = _load(args.policy)
        naming = _load(args.naming_contract) if args.naming_contract else None
        report = validate(args.project, bundle, policy, naming)
    except (OSError, ValueError, json.JSONDecodeError):
        print(f"{pid.CANONICAL_ID} validate: invalid invocation or input", file=sys.stderr)
        return 2
    return emit(report, args.format, "validate")


def emit(report: Report, fmt: str, command: str) -> int:
    """Print a report; exit 0 only on pass (fail and incomplete are both findings)."""
    if fmt == "json":
        sys.stdout.write(to_json(report))
    else:
        sys.stdout.write(f"{pid.CANONICAL_ID} {command}: {report.verdict}\n")
        for finding in report.findings:
            subject = f" [{finding.subject}]" if finding.subject else ""
            sys.stdout.write(f"{finding.code}: {finding.message}{subject}\n")
    return 0 if report.verdict == "pass" else 1


def _load(path: str) -> dict[str, Any]:
    if not os.path.isabs(path):
        raise ValueError("input path must be absolute")
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value
