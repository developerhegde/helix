"""Generated project-tree policy checks."""

from __future__ import annotations

import fnmatch
import os
from typing import Any


def check(project_dir: str, policy: dict[str, Any]) -> list[tuple[str, str]]:
    forbidden = tuple(policy.get("project", {}).get("forbidden_paths", ()))
    failures: list[tuple[str, str]] = []
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


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(path, pattern.replace("/**", "/*"))
