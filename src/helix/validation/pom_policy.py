"""Offline Maven POM policy checks."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Mapping, Optional

_SEMVER = re.compile(r"\d+\.\d+\.\d+(?:-SNAPSHOT)?")


def check(project_dir: str, policy: dict[str, Any], bundle: Optional[Mapping[str, Any]] = None) -> list[tuple[str, str]]:
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
    child_pom = policy.get("maven", {}).get("child_pom")
    parent_pins = isinstance(child_pom, dict) and child_pom.get("forbid_versions")
    if runtime and not parent_pins and runtime not in _text_content(root):
        failures.append(("POM_RUNTIME_MISSING", "POM does not declare the approved Mule runtime."))
    failures.extend(_child_rules(root, ns, policy.get("maven", {}), bundle or {}))
    return failures


def _child_rules(root: ET.Element, ns: str, maven: Mapping[str, Any], bundle: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Rules from the client standards. The version-range rule always runs; the rest are switched on by the policy."""
    failures: list[tuple[str, str]] = []
    local = lambda element: element.tag.rsplit("}", 1)[-1]
    versions = [(element.text or "").strip() for element in root.iter() if local(element) == "version"]
    if any(value in ("LATEST", "RELEASE") or any(mark in value for mark in "[(,") for value in versions):
        failures.append(("POM_VERSION_RANGE", "POM uses a version range, LATEST or RELEASE."))
    child = maven.get("child_pom") if isinstance(maven.get("child_pom"), dict) else {}
    pinned = [element for element in root.iter() if local(element) in ("dependency", "plugin")
              and any(local(item) == "version" for item in element)]
    if child.get("forbid_versions") and pinned:
        failures.append(("POM_VERSION_DECLARED", "POM pins a dependency or plugin version that belongs in the parent."))
    if child.get("forbid_profiles") and any(local(element) == "profiles" for element in root.iter()):
        failures.append(("POM_PROFILE_DECLARED", "POM declares Maven profiles."))
    if child.get("forbid_final_name") and any(local(element) == "finalName" for element in root.iter()):
        failures.append(("POM_FINAL_NAME_OVERRIDDEN", "POM overrides finalName."))
    if child.get("require_semver") and _SEMVER.fullmatch(_text(root, ns, "version") or "") is None:
        failures.append(("POM_VERSION_NOT_SEMVER", "POM version is not MAJOR.MINOR.PATCH."))
    if child.get("artifact_is_repository_name") and _text(root, ns, "artifactId") != bundle.get("repo_name"):
        failures.append(("POM_ARTIFACT_MISMATCH", "POM artifactId is not the approved repository name."))
    if maven.get("group_id") is not None and _text(root, ns, "groupId") != maven["group_id"]:
        failures.append(("POM_GROUP_MISMATCH", "POM groupId is not the approved organisation or business-group id."))
    connectors = maven.get("allowed_connectors")
    if isinstance(connectors, list):
        used = {f"{_text(element, ns, 'groupId')}:{_text(element, ns, 'artifactId')}" for element in root.iter()
                if local(element) == "dependency" and _text(element, ns, "classifier") == "mule-plugin"}
        if used - set(connectors):
            failures.append(("POM_CONNECTOR_NOT_ALLOWED", "POM declares a connector that is not approved."))
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
