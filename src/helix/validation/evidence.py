"""Offline validation of deterministic Maven and MUnit evidence files."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from .. import product_identity as pid


@dataclass(frozen=True)
class Evidence:
    maven_exit_code: int
    tests_run: int
    failures: int
    errors: int
    coverage_percent: float


def load(project_dir: str) -> tuple[Evidence | None, list[tuple[str, str]]]:
    path = os.path.join(project_dir, "target", f"{pid.CANONICAL_ID}-validation-evidence.json")
    if not os.path.isfile(path):
        return None, [("MAVEN_EVIDENCE_MISSING", "Maven and MUnit evidence is missing.")]
    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None, [("MAVEN_EVIDENCE_INVALID", "Maven and MUnit evidence is unreadable.")]
    if not isinstance(value, dict) or value.get("schema") != "mule_validation_evidence.v1":
        return None, [("MAVEN_EVIDENCE_INVALID", "Maven and MUnit evidence schema is invalid.")]
    build, tests, coverage = value.get("maven"), value.get("munit"), value.get("coverage")
    if not isinstance(build, dict) or not isinstance(tests, dict) or not isinstance(coverage, dict):
        return None, [("MAVEN_EVIDENCE_INVALID", "Maven and MUnit evidence is incomplete.")]
    fields = (build.get("exit_code"), tests.get("tests_run"), tests.get("failures"), tests.get("errors"), coverage.get("application_percent"))
    if (not isinstance(fields[0], int) or any(not isinstance(item, int) or item < 0 for item in fields[1:4])
            or not isinstance(fields[4], (int, float)) or isinstance(fields[4], bool) or not 0 <= fields[4] <= 100):
        return None, [("MAVEN_EVIDENCE_INVALID", "Maven and MUnit evidence values are invalid.")]
    return Evidence(fields[0], fields[1], fields[2], fields[3], float(fields[4])), []


def check(project_dir: str, policy: dict[str, Any]) -> tuple[Evidence | None, list[tuple[str, str]]]:
    evidence, findings = load(project_dir)
    if evidence is None:
        return None, findings
    if evidence.maven_exit_code != 0:
        findings.append(("MAVEN_BUILD_FAILED", "Maven packaging evidence reports a non-zero exit code."))
    if evidence.failures or evidence.errors:
        findings.append(("MUNIT_FAILED", "MUnit evidence reports failures or errors."))
    minimum = policy.get("testing", {}).get("minimum_application_coverage")
    if minimum is not None and (not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or evidence.coverage_percent < minimum):
        findings.append(("COVERAGE_BELOW_THRESHOLD", "MUnit application coverage is below the approved threshold."))
    return evidence, findings
