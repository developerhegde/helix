"""Structural contracts for staged standalone B2 validation inputs."""

from __future__ import annotations

from typing import Any


def check_bundle(bundle: Any) -> list[tuple[str, str]]:
    if not isinstance(bundle, dict) or bundle.get("schema") != "design_bundle.v1":
        return [("DESIGN_BUNDLE_INVALID", "Design bundle schema is invalid.")]
    findings: list[tuple[str, str]] = []
    for name in ("contract", "documents", "keys", "deployment_property_keys", "mappings"):
        if name not in bundle:
            findings.append(("DESIGN_BUNDLE_INVALID", "Design bundle is missing a required validation field."))
            break
    if not isinstance(bundle.get("keys", ()), list) or not isinstance(bundle.get("mappings", ()), list):
        findings.append(("DESIGN_BUNDLE_INVALID", "Design bundle key or mapping fields are invalid."))
    keys = bundle.get("keys", ())
    if isinstance(keys, list) and any(not isinstance(item, dict) or not isinstance(item.get("key"), str) for item in keys):
        findings.append(("DESIGN_BUNDLE_INVALID", "Design bundle holds an invalid property key entry."))
    return [findings[0]] if findings else []


def check_policy(policy: Any) -> list[tuple[str, str]]:
    if not isinstance(policy, dict) or policy.get("schema") != "validation_policy.v1":
        return [("VALIDATION_POLICY_INVALID", "Validation policy schema is invalid.")]
    if not isinstance(policy.get("version"), int) or isinstance(policy["version"], bool) or policy["version"] < 1:
        return [("VALIDATION_POLICY_INVALID", "Validation policy version is invalid.")]
    maven = policy.get("maven")
    project = policy.get("project")
    configuration = policy.get("configuration")
    if not isinstance(maven, dict) or not isinstance(project, dict) or not isinstance(configuration, dict):
        return [("VALIDATION_POLICY_INVALID", "Validation policy sections are incomplete.")]
    return []
