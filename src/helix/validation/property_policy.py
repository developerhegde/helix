"""Property, configuration file, marker, and plaintext-secret policy checks."""

from __future__ import annotations

import os
import re
from typing import Any

from ..profile.secrets import looks_secret
from .reference_scan import SourceScan

_MARKER = re.compile(r"\$\{(?:[A-Z][A-Z0-9]*_)?(SET|ENCRYPT)_([A-Z][A-Z0-9_]*)\}")
_PROPERTY_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_.-]*)\s*[:=]\s*(.*?)\s*$")


def check(project_dir: str, bundle: dict[str, Any], policy: dict[str, Any], scan: SourceScan) -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    configuration = policy.get("configuration", {})
    allowed_sources = tuple(configuration.get("allowed_property_sources", ()))
    properties = _bundle_properties(bundle)
    expected = set(properties)
    deployment = set(bundle.get("deployment_property_keys", ()))
    defined, markers, secret_values = _configuration_values(project_dir)
    code = set(scan.properties) | set(scan.secure_properties)
    if scan.dynamic_references:
        failures.append(("DYNAMIC_PROPERTY_REFERENCE", "Generated source contains an unverifiable dynamic property reference."))
    if code - defined - deployment:
        failures.append(("PROPERTY_UNDEFINED", "Generated source references a property not defined or declared for deployment."))
    if expected - code:
        failures.append(("PROPERTY_UNUSED", "Approved design keys are not referenced by generated source."))
    for key in deployment:
        if key in defined:
            failures.append(("DEPLOYMENT_PROPERTY_WRITTEN", "A deployment property is written into generated configuration."))
    expected_marker = _expected_markers(properties)
    for key, allowed in expected_marker.items():
        if markers.get(key) not in allowed:
            failures.append(("MARKER_POLICY_VIOLATION", "Configuration is missing an approved environment marker."))
    for key, marker in markers.items():
        allowed = expected_marker.get(key, set())
        if marker not in allowed:
            failures.append(("MARKER_POLICY_VIOLATION", "Configuration contains an unexpected environment marker."))
    for path, key, value in secret_values:
        if _is_base_or_test(path, allowed_sources) and _MARKER.search(value):
            failures.append(("MARKER_POLICY_VIOLATION", "Base or test configuration contains an environment marker."))
        if ("secret" in key.lower() or "password" in key.lower() or "token" in key.lower()) and value and not _MARKER.search(value) and looks_secret(value):
            failures.append(("PLAINTEXT_SECRET", "Configuration contains a plaintext secret-shaped value."))
    return _unique(failures)


def _bundle_properties(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["key"]: item for item in bundle.get("keys", ()) if isinstance(item, dict) and isinstance(item.get("key"), str)}


def _expected_markers(properties: dict[str, dict[str, Any]]) -> dict[str, set[tuple[str, str]]]:
    result: dict[str, set[tuple[str, str]]] = {}
    for key, item in properties.items():
        kind = "ENCRYPT" if item.get("class") == "secret" else "SET"
        if item.get("class") in ("env_specific", "secret"):
            result[key] = {(kind, environment) for environment in item.get("environments", ())}
    return result


def _configuration_values(project_dir: str) -> tuple[set[str], dict[str, tuple[str, str]], list[tuple[str, str, str]]]:
    defined: set[str] = set()
    markers: dict[str, tuple[str, str]] = {}
    values: list[tuple[str, str, str]] = []
    for folder, _, files in os.walk(project_dir):
        for name in files:
            if not name.endswith((".yaml", ".yml", ".properties")):
                continue
            path = os.path.join(folder, name)
            relative = os.path.relpath(path, project_dir).replace("\\", "/")
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    match = _PROPERTY_LINE.match(line)
                    if not match:
                        continue
                    key, value = match.groups()
                    defined.add(key)
                    marker = _MARKER.fullmatch(value)
                    if marker:
                        markers[key] = (marker.group(1), marker.group(2))
                    values.append((relative, key, value))
    return defined, markers, values


def _is_base_or_test(path: str, allowed_sources: tuple[str, ...]) -> bool:
    return path.startswith("src/test/") or path in allowed_sources


def _unique(values: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return list(dict.fromkeys(values))
