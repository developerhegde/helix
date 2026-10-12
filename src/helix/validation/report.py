"""Stable public validation report and orchestrator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from ..naming import LAYOUT_DEPLOYMENT_PROPERTIES
from . import contracts, design_binding, evidence, naming_policy, pom_policy, project_policy, property_policy, reference_scan

# A required check that could not run; alone, these make the verdict incomplete rather than fail.
_UNAVAILABLE = frozenset({"MAVEN_EVIDENCE_MISSING", "MAVEN_EVIDENCE_INVALID"})


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
    maven_evidence: dict[str, Any] | None
    referenced_keys: tuple[str, ...]
    defined_keys: tuple[str, ...]
    deployment_keys: tuple[str, ...]
    mappings: tuple[str, ...]
    naming_contract_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "validation_report.v1",
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest,
            "bundle_digest": self.bundle_digest,
            "naming_contract_digest": self.naming_contract_digest,
            "verdict": self.verdict,
            "findings": [item.as_dict() for item in self.findings],
            "maven_evidence": self.maven_evidence,
            "references": {
                "keys": list(self.referenced_keys),
                "defined_keys": list(self.defined_keys),
                "deployment_keys": list(self.deployment_keys),
                "mapping_anchors": list(self.mappings),
            },
        }


def validate(project_dir: str, bundle: dict[str, Any], policy: dict[str, Any],
             naming: dict[str, Any] | None = None) -> Report:
    """Validate a generated project. ``naming`` is the staged ``naming_contract.v1``;
    when given, NAM-001 to NAM-007 run and the report records the proven digest."""
    scan = reference_scan.scan(project_dir)
    raw_findings: list[tuple[str, str]] = []
    bundle_contract_findings = contracts.check_bundle(bundle)
    policy_contract_findings = contracts.check_policy(policy)
    raw_findings.extend(bundle_contract_findings)
    raw_findings.extend(policy_contract_findings)
    if bundle_contract_findings or policy_contract_findings:
        findings = tuple(Finding(code, message) for code, message in sorted(set(raw_findings)))
        return Report(_policy_version(policy), _digest(policy), _digest(bundle), "fail", findings, None, (), (), (), ())
    standards_digest = bundle.get("standards_bundle_digest")
    expected_standards_digest = policy.get("standards_bundle_digest")
    if expected_standards_digest is not None and standards_digest != expected_standards_digest:
        raw_findings.append(("STANDARDS_BUNDLE_MISMATCH", "Design bundle is not bound to the staged standards bundle."))
    contract = None
    if naming is not None:
        contract, naming_findings = naming_policy.check(project_dir, bundle, policy, naming)
        raw_findings.extend(naming_findings)
    base_marks = contract is not None and contract.layout == LAYOUT_DEPLOYMENT_PROPERTIES
    raw_findings.extend(design_binding.check(project_dir, bundle))
    raw_findings.extend(pom_policy.check(project_dir, policy))
    raw_findings.extend(project_policy.check(project_dir, policy))
    raw_findings.extend(property_policy.check(project_dir, bundle, policy, scan, base_marks_allowed=base_marks))
    maven_evidence, evidence_findings = evidence.check(project_dir, policy)
    raw_findings.extend(evidence_findings)
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
        _verdict(findings),
        findings,
        ({"maven_exit_code": maven_evidence.maven_exit_code, "tests_run": maven_evidence.tests_run,
          "failures": maven_evidence.failures, "errors": maven_evidence.errors,
          "coverage_percent": maven_evidence.coverage_percent} if maven_evidence else None),
        tuple(sorted(scan.properties | scan.secure_properties)),
        tuple(sorted(_defined_keys(project_dir))),
        tuple(sorted(str(item) for item in bundle.get("deployment_property_keys", ()) if isinstance(item, str))),
        tuple(sorted(scan.mappings)),
        contract.digest if contract is not None else None,
    )


def _verdict(findings: Iterable[Finding]) -> str:
    codes = {item.code for item in findings}
    return "pass" if not codes else "incomplete" if codes <= _UNAVAILABLE else "fail"


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
