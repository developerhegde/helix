"""Compile an attempt's ``validation_policy.v1`` from the approved standards bundle and the naming contract.

The bundle states the client's standards; the policy is the same facts in the shape the
validator reads. A standards check is switched on only by a field the bundle carries.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .. import product_identity as pid
from ..naming import NamingContract

_CHILD_POM = ("forbid_versions", "forbid_profiles", "forbid_final_name", "require_semver", "artifact_is_repository_name")
_TESTING = ("forbid_sleep", "ignored_needs_ticket", "suite_per_implementation")
DEFAULT_COVERAGE = 75  # docs/mulesoft-development-standards.md; a bundle may raise it


class PolicyCompileError(ValueError):
    """The standards bundle cannot be turned into a validation policy."""


def compile_policy(standards: Mapping[str, Any], standards_digest: str, contract: NamingContract) -> dict[str, Any]:
    project = _section(standards, "project")
    parent, runtime = project.get("golden_parent"), project.get("mule_runtime")
    if (not isinstance(parent, dict) or not isinstance(runtime, str) or not runtime
            or not all(isinstance(parent.get(name), str) and parent[name] for name in ("group_id", "artifact_id", "version"))):
        raise PolicyCompileError("standards bundle names no parent POM or runtime")
    maven: dict[str, Any] = {
        "golden_parent": {"groupId": parent["group_id"], "artifactId": parent["artifact_id"], "version": parent["version"]},
        "allowed_plugins": _strings(project.get("allowed_plugins")),
        "mule_runtime": runtime,
    }
    child = {name: True for name in _CHILD_POM if _section(project, "child_pom").get(name) is True}
    if child:
        maven["child_pom"] = child
    if isinstance(project.get("group_id"), str):
        maven["group_id"] = project["group_id"]
    connectors = _strings(_section(standards, "connectors").get("allowed"))
    if connectors:
        maven["allowed_connectors"] = connectors

    configured = _section(standards, "configuration")
    secure_key = _text(configured.get("secure_property_key"), "secure.key")
    tree: dict[str, Any] = {"forbidden_paths": _strings(project.get("forbidden_paths")),
                            "forbid_java_interop": project.get("forbid_java_interop") is not False}
    if isinstance(project.get("gitignore_required"), list):
        tree["gitignore_required"] = _strings(project["gitignore_required"])
    if project.get("require_mule_artifact") is True:
        tree["mule_artifact"] = {"min_mule_version": ".".join(runtime.split(".")[:2]),
                                 "java": str(project.get("java", "")), "secure_key": secure_key}

    tested = _section(standards, "testing")
    coverage = tested.get("minimum_application_coverage", DEFAULT_COVERAGE)
    if isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or not 0 <= coverage <= 100:
        raise PolicyCompileError("standards bundle coverage minimum is not a percentage")
    policy: dict[str, Any] = {
        "schema": "validation_policy.v1",
        "version": 1,
        "standards_bundle_digest": standards_digest,
        "maven": maven,
        "project": tree,
        "configuration": {
            "allowed_property_sources": [contract.configuration_paths(contract.allowed_environment_keys()[0]).base],
            "environment_selector": _text(configured.get("environment_selector"), "env"),
            "secure_property_key": secure_key,
            "marker_prefix": _text(configured.get("marker_prefix"), pid.CANONICAL_ID.upper()),
        },
        "testing": {"minimum_application_coverage": coverage, **{name: tested[name] for name in _TESTING if name in tested}},
    }

    patterns = {name: text for name, text in _section(standards, "patterns").items() if isinstance(text, str)}
    try:
        for text in (*patterns.values(), str(tested.get("ignored_needs_ticket", ""))):
            re.compile(text)
    except re.error as exc:
        raise PolicyCompileError("standards bundle holds an invalid pattern") from exc
    if patterns:
        policy["patterns"] = patterns
    errors, mule = _section(standards, "error_handling"), {}
    if isinstance(errors.get("handler_file"), str):
        mule["error_handler_file"] = errors["handler_file"]
    if errors.get("forbid_continue_on_any") is True:
        mule["forbid_on_error_continue_any"] = True
    if _section(standards, "api").get("apikit") == "required":
        mule["require_request_validation"] = True
    if _section(standards, "api").get("autodiscovery") == "required":
        mule["api_properties"] = True
    connector_rules = _section(standards, "connectors")
    for name in ("values_from_properties", "require_http_timeouts"):
        if connector_rules.get(name) is True:
            mule["connector_values_from_properties" if name == "values_from_properties" else name] = True
    if isinstance(errors.get("envelope_script"), str):
        mule["error_envelope_script"] = errors["envelope_script"]
    if isinstance(errors.get("mappings"), list):
        mule["error_mappings"] = [row for row in errors["mappings"] if isinstance(row, dict)]
    if mule:
        policy["mule"] = mule
    logging, rules = _section(standards, "logging"), {}
    if logging.get("forbid_free_text_logger") is True:
        rules["forbid_free_text_logger"] = True
        if isinstance(logging.get("log_event_subflow"), str):
            rules["log_event_subflow"] = logging["log_event_subflow"]
    if logging.get("forbid_trace") is True or isinstance(logging.get("root_levels"), list):
        rules["log4j2"] = {"forbid_trace": logging.get("forbid_trace") is True, "root_levels": _strings(logging.get("root_levels"))}
    if rules:
        policy["logging"] = rules
    return policy


def _section(source: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = source.get(name)
    return value if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _text(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value else default
