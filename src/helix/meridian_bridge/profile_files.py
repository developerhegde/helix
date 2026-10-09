"""Structural adapter for the Meridian-owned profile files (B1-015).

Pinned to one Meridian interface version. B1 does not import ``meridian``:
importing it applies a ``.env`` to the process environment, which the offline
doctor must never do. This adapter mirrors the pinned version's file shapes
(``meridian/tenant.py`` PROFILE_KEYS and ENVIRONMENT_KEYS, ``onboarding.py``
CREDENTIAL_KEYS) and is replaced by the contract-tested bridge in B2.
Problems name a path only; parser messages are dropped because they quote content.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

import yaml

MERIDIAN_INTERFACE_VERSION = "1.8.1"

TENANT_FILE = "tenant.yaml"
ENVIRONMENTS_FILE = "environments.yaml"
COMPARE_FILE = "compare.yaml"
DOTENV_FILE = ".env"
FILES = (TENANT_FILE, ENVIRONMENTS_FILE, COMPARE_FILE, DOTENV_FILE)

TENANT_KEYS = frozenset({
    "schema_version", "name", "captured_on", "naming", "environments",
    "business_groups", "business_group_ids", "root_org_name", "root_org_id",
    "session_token_lifetime_seconds", "mq_region", "config_dir_in_repo",
    "config_files", "deployment_properties", "secure_properties",
})
ENVIRONMENT_KEYS = frozenset({
    "key", "branch", "display", "rank", "is_production", "colour", "in_scope", "note",
    "runtime_app_name_suffix", "runtime_environment_name", "git_repo_config_name_prefix",
})
CREDENTIAL_KEYS = (
    "ANYPOINT_TOKEN", "ANYPOINT_PAT", "ANYPOINT_PASSWORD",
    "ANYPOINT_CLIENT_SECRET", "ANYPOINT_USERNAME", "ANYPOINT_CLIENT_ID",
)

_DOTENV_LINE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

Problem = Tuple[str, str]  # (path, message)


def parse_dotenv(text: str) -> Tuple[Dict[str, str], List[Problem]]:
    """Parse ``KEY=VALUE`` lines as data. Never reads or writes ``os.environ``."""
    values: Dict[str, str] = {}
    problems: List[Problem] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _DOTENV_LINE.match(line)
        if match is None:
            problems.append((f"{DOTENV_FILE}:line {number}", "Line is not KEY=VALUE."))
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[match.group(1)] = value
    return values, problems


def _schema_version(name: str, doc: Dict[str, Any], problems: List[Problem]) -> None:
    version = doc.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        problems.append((f"{name}:schema_version", "schema_version is missing or not 1."))


def _tenant(doc: Dict[str, Any], problems: List[Problem]) -> None:
    _schema_version(TENANT_FILE, doc, problems)
    for key in doc:
        if key not in TENANT_KEYS:
            problems.append((f"{TENANT_FILE}:{key}", "Key is not part of the pinned tenant profile."))
    envs = doc.get("environments")
    if envs is None:
        return
    if not isinstance(envs, list):
        problems.append((f"{TENANT_FILE}:environments", "environments is not a list."))
        return
    for i, env in enumerate(envs):
        where = f"{TENANT_FILE}:environments[{i}]"
        if not isinstance(env, dict) or not isinstance(env.get("key"), str):
            problems.append((where, "Environment entry is not a mapping with a key."))
            continue
        for key in env:
            if key not in ENVIRONMENT_KEYS:
                problems.append((f"{where}.{key}", "Key is not part of the pinned environment entry."))


def _environments(doc: Dict[str, Any], problems: List[Problem]) -> None:
    _schema_version(ENVIRONMENTS_FILE, doc, problems)
    patterns = doc.get("jar_patterns")
    if patterns is None:
        return
    if not isinstance(patterns, dict):
        problems.append((f"{ENVIRONMENTS_FILE}:jar_patterns", "jar_patterns is not a mapping."))
        return
    for name, entry in patterns.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("regex"), str):
            problems.append((f"{ENVIRONMENTS_FILE}:jar_patterns.{name}", "Pattern has no regex."))


def _compare(doc: Dict[str, Any], problems: List[Problem]) -> None:
    for key in ("keys", "severity"):
        if key in doc and not isinstance(doc[key], dict):
            problems.append((f"{COMPARE_FILE}:{key}", f"{key} is not a mapping."))


_CHECKS = {TENANT_FILE: _tenant, ENVIRONMENTS_FILE: _environments, COMPARE_FILE: _compare}


def parse_file(name: str, text: str) -> Tuple[Any, List[Problem]]:
    """Parse one Meridian file and check its structure. Returns (data, problems)."""
    if name == DOTENV_FILE:
        return parse_dotenv(text)
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return None, [(name, "File does not parse as YAML.")]
    if not isinstance(doc, dict):
        return None, [(name, "File is not a YAML mapping.")]
    problems: List[Problem] = []
    _CHECKS[name](doc, problems)
    return doc, problems
