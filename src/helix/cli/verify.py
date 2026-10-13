"""`verify` sub-command: run Maven and MUnit, collect value-free evidence, then validate."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .. import product_identity as pid
from ..validation import maven_runner, report_parser, validate
from .validate import _load, emit

_RECEIPT = "target/maven-execution.json"


def add_parser(sub: "argparse._SubParsersAction") -> None:
    parser = sub.add_parser("verify", help="Run Maven and MUnit, then validate the generated project.")
    parser.add_argument("--project", required=True, help="Absolute generated project directory.")
    parser.add_argument("--bundle", required=True, help="Absolute design_bundle.v1 JSON file.")
    parser.add_argument("--policy", required=True, help="Absolute validation_policy.v1 JSON file.")
    parser.add_argument("--naming-contract", required=True, help="Absolute naming_contract.v1 JSON file.")
    parser.add_argument("--settings", required=True, help="Absolute Maven settings file.")
    parser.add_argument("--maven", default="mvn", help="Maven executable.")
    parser.add_argument("--munit-report", default="target/munit-results.xml", help="Project-relative MUnit report.")
    parser.add_argument("--coverage-report", default="target/coverage-summary.json", help="Project-relative coverage summary.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, **_: Any) -> int:
    try:
        if not os.path.isabs(args.project) or not os.path.isdir(args.project):
            raise ValueError("project must be an absolute directory")
        if not os.path.isabs(args.settings) or not os.path.isfile(args.settings):
            raise ValueError("settings must be an absolute file")
        bundle, policy, naming = _load(args.bundle), _load(args.policy), _load(args.naming_contract)
    except (OSError, ValueError, json.JSONDecodeError):
        print(f"{pid.CANONICAL_ID} verify: invalid invocation or input", file=sys.stderr)
        return 2
    _collect_evidence(args)
    return emit(validate(args.project, bundle, policy, naming), args.format, "verify")


def _collect_evidence(args: argparse.Namespace) -> None:
    """Leave fresh evidence or none. A summary from an earlier run is removed first,
    so a Maven run that cannot start yields an incomplete verdict, never a stale pass."""
    evidence = f"target/{pid.CANONICAL_ID}-validation-evidence.json"
    for relative in (_RECEIPT, evidence):
        try:
            os.remove(os.path.join(args.project, *relative.split("/")))
        except FileNotFoundError:
            pass
    try:
        maven_runner.run(args.project, args.settings, os.path.join(args.project, *_RECEIPT.split("/")),
                         maven_path=args.maven)
        report_parser.parse(args.project, _RECEIPT, munit_report=args.munit_report,
                            coverage_report=args.coverage_report, output_path=evidence)
    except (OSError, ValueError):  # Maven could not start, or a report is missing or malformed
        pass
