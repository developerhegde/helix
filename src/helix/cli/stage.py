"""`stage` sub-command: write an attempt's immutable validation inputs from a healthy profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from typing import Any, Optional

from .. import config
from .. import product_identity as pid
from ..naming import compile_contract
from ..profile.doctor import OperationalError
from ..profile.loader import ProfileInvalid, load_profile
from ..standards import bundle_path, load as load_standards
from ..validation.policy_compiler import PolicyCompileError, compile_policy

POLICY_FILE, NAMING_FILE, STANDARDS_FILE = "validation-policy.json", "naming-contract.json", "standards-bundle.yaml"


def add_parser(sub: "argparse._SubParsersAction") -> None:
    parser = sub.add_parser("stage", help="Write the validation policy, naming contract and standards bundle for an attempt.")
    parser.add_argument("--profile", help=f"Absolute profile directory (or {pid.PROFILE_ENV_VAR}).")
    parser.add_argument("--out-dir", required=True, help="Absolute directory to create; it must not already hold files.")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, *, now: Optional[datetime] = None) -> int:
    name = f"{pid.CANONICAL_ID} stage"
    path = args.profile or config.client_profile_from_env()
    try:
        if not path:
            raise OperationalError(f"--profile is required (or set {pid.PROFILE_ENV_VAR})")
        if not os.path.isabs(args.out_dir) or (os.path.isdir(args.out_dir) and os.listdir(args.out_dir)):
            raise OperationalError("--out-dir must be an absolute path that holds no files")
        profile = load_profile(path, now=now)
        contract = compile_contract(profile.data["naming"])
        standards = load_standards(profile.root, profile.client_id, profile.data["standards"])
        policy = compile_policy(standards.data, standards.digest, contract)
    except ProfileInvalid as exc:
        print(f"{name}: the profile has {exc.report.errors} error(s); run the doctor", file=sys.stderr)
        return 1
    except (OperationalError, PolicyCompileError) as exc:
        print(f"{name}: {exc}", file=sys.stderr)
        return 2
    os.makedirs(args.out_dir, exist_ok=True)
    policy_text = _canonical(policy)
    _write(os.path.join(args.out_dir, POLICY_FILE), policy_text)
    _write(os.path.join(args.out_dir, NAMING_FILE), _canonical(contract.to_staged()))
    shutil.copyfile(bundle_path(profile.root, profile.data["standards"]), os.path.join(args.out_dir, STANDARDS_FILE))
    digest = hashlib.sha256(policy_text.rstrip("\n").encode("utf-8")).hexdigest()
    sys.stdout.write(f"{name}: policy {digest[:12]}, naming {contract.digest[:12]}, standards {standards.digest[:12]}\n")
    return 0


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
