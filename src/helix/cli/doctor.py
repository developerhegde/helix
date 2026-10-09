"""`doctor` sub-command: offline profile validation (B1)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional

from .. import config
from .. import product_identity as pid
from ..profile.doctor import OperationalError, run_doctor
from ..profile.render import to_json, to_text


def add_parser(sub: "argparse._SubParsersAction") -> None:
    parser = sub.add_parser("doctor", help="Validate a client profile offline.")
    parser.add_argument("--profile", help=f"Absolute profile directory (or {pid.PROFILE_ENV_VAR}).")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on warnings too.")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, *, now: Optional[datetime] = None) -> int:
    path = args.profile or config.client_profile_from_env()
    try:
        if not path:
            raise OperationalError(f"--profile is required (or set {pid.PROFILE_ENV_VAR})")
        report = run_doctor(path, now=now)
    except OperationalError as exc:
        print(f"{pid.CANONICAL_ID} doctor: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(to_json(report) if args.format == "json" else to_text(report))
    return report.exit_code(args.strict)
