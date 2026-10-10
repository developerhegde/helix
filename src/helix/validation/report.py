"""Stable public validation report and orchestrator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from . import design_binding, pom_policy, project_policy, property_policy, reference_scan


@dataclass(frozen=True)
class Finding:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class Report:
    policy_version: int
    policy_digest: str
    bundle_digest: str
    verdict: str
    findings: tuple[Finding, ...]
    referenced_keys: tuple[str, ...]
    defined_keys: tuple[str, ...]
    deployment_keys: tuple[str, ...]
    mappings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "validation_report.v1",
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest,
            "bundle_digest": self.bundle_digest,
            "verdict": self.verdict,
            "findings": [item.as_dict() for item in self.findings],
            "references": {
                "keys": list(self.referenced_keys),
                "defined_keys": list(self.defined_keys),
                "deployment_keys": list(self.deployment_keys),
                "mapping_anchors": list(self.mappings),
            },
        }


def validate(project_dir: str, bundle: dict[str, Any], policy: dict[str, Any]) -> Report:
    scan = reference_scan.scan(project_dir)
    raw_findings: list[tuple[str, str]] = []
    standards_digest = bundle.get("standards_bundle_digest")
    expected_standards_digest = policy.get("standards_bundle_digest")
    if expected_standards_digest is not None and standards_digest != expected_standards_digest:
        raw_findings.append(("STANDARDS_BUNDLE_MISMATCH", "Design bundle is not bound to the staged standards bundle."))
    raw_findings.extend(design_binding.check(project_dir, bundle))
    raw_findings.extend(pom_policy.check(project_dir, policy))
    raw_findings.extend(project_policy.check(project_dir, policy))
    raw_findings.extend(property_policy.check(project_dir, bundle, policy, scan))
    if policy.get("project", {}).get("forbid_java_interop") and scan.java_interop:
        raw_findings.append(("JAVA_INTEROP", "Generated source contains Java interop."))
    expected_mappings = {item.get("id") for item in bundle.get("mappings", ()) if isinstance(item, dict)}
    if expected_mappings - set(scan.mappings):
        raw_findings.append(("MAPPING_ANCHOR_MISSING", "Approved mapping anchors are missing from DataWeave source."))
    findings = tuple(Finding(code, message) for code, message in sorted(set(raw_findings)))
    return Report(
        _policy_version(policy),
        _digest(policy),
        _digest(bundle),
        "pass" if not findings else "fail",
        findings,
        tuple(sorted(scan.properties | scan.secure_properties)),
        tuple(sorted(_defined_keys(project_dir))),
        tuple(sorted(str(item) for item in bundle.get("deployment_property_keys", ()) if isinstance(item, str))),
        tuple(sorted(scan.mappings)),
    )


def to_json(report: Report) -> str:
    return json.dumps(report.as_dict(), sort_keys=True, separators=(",", ":")) + "\n"


def _policy_version(policy: dict[str, Any]) -> int:
    value = policy.get("version", 1)
    return value if isinstance(value, int) and not isinstance(value, bool) else 1


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _defined_keys(project_dir: str) -> Iterable[str]:
    # Report data is intentionally derived without retaining property values.
    _, _, values = property_policy._configuration_values(project_dir)
    return {key for _, key, _ in values}
