"""Console entry point. Exit discipline: 0 healthy, 1 findings, 2 operational failure."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import List, Optional

from .. import product_identity as pid
from . import doctor, validate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=pid.CANONICAL_ID)
    sub = parser.add_subparsers(dest="command")
    doctor.add_parser(sub)
    validate.add_parser(sub)
    return parser


def main(argv: Optional[List[str]] = None, *, now: Optional[datetime] = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse usage errors exit 2; --help exits 0
        return exc.code if isinstance(exc.code, int) else 2
    if getattr(args, "handler", None) is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        return args.handler(args, now=now)
    except Exception as exc:  # one line, no content: an exception message may quote the profile
        print(f"{pid.CANONICAL_ID}: internal error ({type(exc).__name__})", file=sys.stderr)
        return 2
