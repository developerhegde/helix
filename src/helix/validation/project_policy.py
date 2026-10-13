"""Generated project-tree policy checks."""

from __future__ import annotations

import fnmatch
import json
import os
from typing import Any, Mapping, Optional


def check(project_dir: str, policy: dict[str, Any], bundle: Optional[Mapping[str, Any]] = None) -> list[tuple[str, str]]:
    forbidden = tuple(policy.get("project", {}).get("forbidden_paths", ()))
    expected = policy.get("project", {}).get("mule_artifact")
    failures = _mule_artifact(project_dir, expected, bundle or {}) if isinstance(expected, dict) else []
    for folder, _, files in os.walk(project_dir):
        for name in files:
            relative = os.path.relpath(os.path.join(folder, name), project_dir).replace("\\", "/")
            if any(_matches(relative, pattern) for pattern in forbidden):
                failures.append(("FORBIDDEN_PROJECT_PATH", "Generated project contains a forbidden path."))
                return failures
    if policy.get("project", {}).get("forbid_java_interop"):
        java_root = os.path.join(project_dir, "src", "main", "java")
        if os.path.isdir(java_root):
            failures.append(("JAVA_SOURCE_UNLISTED", "Generated project contains Java source."))
    return failures


def _mule_artifact(project_dir: str, expected: Mapping[str, Any], bundle: Mapping[str, Any]) -> list[tuple[str, str]]:
    """mule-artifact.json states the approved runtime and Java version and hides every secret property."""
    try:
        with open(os.path.join(project_dir, "mule-artifact.json"), encoding="utf-8") as handle:
            artifact = json.load(handle)
    except (OSError, json.JSONDecodeError):
        artifact = None
    secrets = [item["key"] for item in bundle.get("keys", ())
               if isinstance(item, dict) and item.get("class") == "secret" and isinstance(item.get("key"), str)]
    hidden = artifact.get("secureProperties") if isinstance(artifact, dict) else None
    hidden = hidden if isinstance(hidden, list) else []
    minimum = str(expected.get("min_mule_version", ""))
    valid = (isinstance(artifact, dict)
             and str(artifact.get("minMuleVersion", "")).startswith(minimum)
             and ("java" not in expected or artifact.get("javaSpecificationVersions") == [str(expected["java"])])
             and all(key in hidden or f"secure::{key}" in hidden for key in secrets)
             and ("secure_key" not in expected or expected["secure_key"] in hidden))
    return [] if valid else [("MULE_ARTIFACT_INVALID", "mule-artifact.json is missing or departs from the approved runtime, Java version or secure properties.")]


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(path, pattern.replace("/**", "/*"))
