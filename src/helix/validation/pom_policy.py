"""Offline Maven POM policy checks."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any


def check(project_dir: str, policy: dict[str, Any]) -> list[tuple[str, str]]:
    path = os.path.join(project_dir, "pom.xml")
    if not os.path.isfile(path):
        return [("POM_MISSING", "pom.xml is missing.")]
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return [("POM_INVALID", "pom.xml is not well-formed XML.")]
    ns = _namespace(root.tag)
    failures: list[tuple[str, str]] = []
    parent = root.find(_tag(ns, "parent"))
    expected_parent = policy.get("maven", {}).get("golden_parent")
    if expected_parent:
        values = {name: _text(parent, ns, name) for name in ("groupId", "artifactId", "version")}
        if values != expected_parent:
            failures.append(("POM_PARENT_MISMATCH", "POM parent does not match the approved golden parent."))
    if root.find(_tag(ns, "repositories")) is not None or root.find(_tag(ns, "pluginRepositories")) is not None:
        failures.append(("POM_REPOSITORY_DECLARED", "Project repositories are not allowed."))
    allowed = set(policy.get("maven", {}).get("allowed_plugins", ()))
    for plugin in root.findall(".//" + _tag(ns, "plugin")):
        coordinate = f"{_text(plugin, ns, 'groupId') or 'org.apache.maven.plugins'}:{_text(plugin, ns, 'artifactId') or ''}"
        if coordinate not in allowed:
            failures.append(("POM_PLUGIN_NOT_ALLOWED", "POM declares an unapproved plugin."))
            break
    runtime = policy.get("maven", {}).get("mule_runtime")
    if runtime and runtime not in _text_content(root):
        failures.append(("POM_RUNTIME_MISSING", "POM does not declare the approved Mule runtime."))
    return failures


def _namespace(tag: str) -> str:
    return tag[1:tag.index("}")] if tag.startswith("{") else ""


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}" if namespace else name


def _text(node: ET.Element | None, namespace: str, name: str) -> str | None:
    if node is None:
        return None
    child = node.find(_tag(namespace, name))
    return child.text.strip() if child is not None and child.text else None


def _text_content(root: ET.Element) -> str:
    return " ".join(item.strip() for item in root.itertext() if item.strip())
