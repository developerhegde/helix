"""Text and JSON rendering of a doctor report. Findings never carry profile values."""

from __future__ import annotations

import json

from .. import product_identity as pid
from .doctor import DEFERRED_CHECKS, Report


def to_json(report: Report) -> str:
    return json.dumps(report.as_dict(), indent=2) + "\n"


def to_text(report: Report) -> str:
    lines = [f"{pid.CANONICAL_ID} doctor: client {report.client_id or '-'}, "
             f"policy {report.policy_version}, status {report.status}"]
    for f in report.findings:
        lines.append(f"{f.severity.upper():<7} {f.id} {f.path}: {f.message}")
        lines.append(f"        fix: {f.remediation}")
    lines.append(f"{report.errors} error(s), {report.warnings} warning(s)")
    lines.append("deferred to B2, not checked offline: " + ", ".join(DEFERRED_CHECKS))
    return "\n".join(lines) + "\n"
