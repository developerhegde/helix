"""Versioned, immutable client standards-bundle loading and validation."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

import yaml


class StandardsInvalid(ValueError):
    """A client standards reference or bundle is unsafe or malformed."""


@dataclass(frozen=True)
class StandardsBundle:
    client_id: str
    version: str
    digest: str
    data: Mapping[str, Any]


def load(profile_dir: str, client_id: str, reference: Any) -> StandardsBundle:
    """Load a local, approved standards bundle named by a profile reference."""
    if not isinstance(reference, dict):
        raise StandardsInvalid("standards reference must be a mapping")
    path = reference.get("path")
    version = reference.get("version")
    expected_digest = reference.get("sha256")
    if not isinstance(path, str) or not _safe_relative(path):
        raise StandardsInvalid("standards path is not a safe relative path")
    if not isinstance(version, str) or not version:
        raise StandardsInvalid("standards version is missing")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64 or any(c not in "0123456789abcdef" for c in expected_digest):
        raise StandardsInvalid("standards digest is invalid")
    bundle_path = _join(profile_dir, path)
    try:
        with open(bundle_path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise StandardsInvalid("standards bundle cannot be read") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_digest:
        raise StandardsInvalid("standards bundle digest does not match")
    try:
        value = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise StandardsInvalid("standards bundle is not UTF-8 YAML") from exc
    _validate_bundle(value, client_id, version)
    return StandardsBundle(client_id, version, digest, MappingProxyType(value))


def _validate_bundle(value: Any, client_id: str, version: str) -> None:
    if not isinstance(value, dict) or value.get("schema") != "client_standards_bundle.v1":
        raise StandardsInvalid("standards bundle schema is unsupported")
    if value.get("client_id") != client_id or value.get("version") != version:
        raise StandardsInvalid("standards bundle client or version does not match the profile")
    approved = value.get("approved")
    if not isinstance(approved, dict) or not isinstance(approved.get("by"), str) or not approved["by"].strip() or not approved.get("at"):
        raise StandardsInvalid("standards bundle lacks approval metadata")
    project = value.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("mule_runtime"), str) or not isinstance(project.get("java"), int):
        raise StandardsInvalid("standards bundle project baseline is incomplete")
    logging = value.get("logging")
    if not isinstance(logging, dict) or logging.get("style") != "json_logger_module":
        raise StandardsInvalid("standards bundle logging policy is unsupported")


def _safe_relative(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return bool(normalized and not normalized.startswith("/") and ".." not in normalized.split("/") and "${" not in normalized)


def _join(root: str, relative: str) -> str:
    path = os.path.realpath(os.path.join(root, *relative.replace("\\", "/").split("/")))
    if os.path.commonpath((os.path.realpath(root), path)) != os.path.realpath(root):
        raise StandardsInvalid("standards path escapes the profile directory")
    return path
