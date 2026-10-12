"""Isolated Maven/MUnit execution receipt writer for B2 verification."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Sequence


class MavenRunError(ValueError):
    """The isolated Maven runner cannot be invoked safely."""


def run(project_dir: str, settings_path: str, output_path: str, *,
        maven_path: str = "mvn", goals: Sequence[str] = ("clean", "test")) -> dict[str, object]:
    """Run Maven with an explicit, restricted environment and write a receipt.

    This produces `mule_execution_receipt.v1`, not validation evidence. A later
    report parser converts known MUnit and coverage outputs into the value-free
    `mule_validation_evidence.v1` consumed by ``helix validate``.
    """
    if not os.path.isabs(project_dir) or not os.path.isdir(project_dir):
        raise MavenRunError("project directory must be absolute")
    if not os.path.isabs(settings_path) or not os.path.isfile(settings_path):
        raise MavenRunError("Maven settings file must be an absolute readable file")
    if os.path.isabs(maven_path) and not os.path.isfile(maven_path):
        raise MavenRunError("Maven executable cannot be read")
    if not goals or any(not isinstance(goal, str) or not goal or goal.startswith("-") for goal in goals):
        raise MavenRunError("Maven goals must be non-option text")
    output = Path(output_path)
    if not output.is_absolute():
        raise MavenRunError("output path must be absolute")

    command = [maven_path, "--batch-mode", "--no-transfer-progress", "--settings", settings_path, *goals]
    started = time.monotonic()
    completed = subprocess.run(command, cwd=project_dir, env=_environment(), capture_output=True, text=False, check=False)
    duration_ms = int((time.monotonic() - started) * 1000)
    receipt = {
        "schema": "mule_execution_receipt.v1",
        "command": ["mvn", "--batch-mode", "--no-transfer-progress", "--settings", "<settings>", *goals],
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return receipt


def _environment() -> dict[str, str]:
    names = ("HOME", "LANG", "PATH", "TMPDIR")
    return {name: os.environ[name] for name in names if name in os.environ}
