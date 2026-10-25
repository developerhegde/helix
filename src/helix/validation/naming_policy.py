"""Naming, environment and configuration-path checks (NAM-001 to NAM-007).

Run against the staged ``naming_contract.v1``. Every path and name is derived
from the contract; nothing here trusts a path or name the bundle merely states.
"""

from __future__ import annotations

import os
import re
from typing import Any, Mapping, Optional, Sequence

from ..naming import LAYOUT_DEPLOYMENT_PROPERTIES, NamingContract, NamingInvalid, load_contract

_PROPERTY_SOURCE = re.compile(r'<(?:configuration-properties|secure-properties:config)\b[^>]*?\bfile\s*=\s*"([^"]*)"')
_PROPERTY_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_.-]*)\s*[:=]\s*(.*?)\s*$")
_MARK = re.compile(r"\$\{(?:([A-Z][A-Z0-9]*)_)?(SET|ENCRYPT)_([A-Z][A-Z0-9_]*)\}")
_RESOURCES = "src/main/resources/"
_CONFIG_SUFFIXES = (".yaml", ".yml", ".properties")

Findings = list[tuple[str, ...]]  # (code, message[, subject])


def check(project_dir: str, bundle: Mapping[str, Any], policy: Mapping[str, Any],
          staged: Any) -> tuple[Optional[NamingContract], Findings]:
    """Return the proven contract, or None, and the findings."""
    try:
        contract = load_contract(staged)  # NAM-001
    except NamingInvalid:
        return None, [("NAMING_CONTRACT_MISMATCH", "Staged naming contract is invalid.")]
    if bundle.get("naming_contract_digest") != contract.digest:
        return None, [("NAMING_CONTRACT_MISMATCH", "Design bundle is not bound to the staged naming contract.")]
    failures: Findings = []
    environments = _environments(bundle, contract, failures)
    _applications(bundle, contract, environments, failures)
    if environments:
        _configuration(project_dir, bundle, policy, contract, environments, failures)
    return contract, list(dict.fromkeys(failures))


def _environments(bundle: Mapping[str, Any], contract: NamingContract, failures: Findings) -> tuple[str, ...]:
    """NAM-004. Returns the bundle's environments that the contract allows, in the bundle's order."""
    named, valid = _names(bundle.get("environments"))
    if not valid or len(named) < 2 or len(set(named)) != len(named):
        failures.append(("DESIGN_BUNDLE_INVALID", "Design bundle must list at least two distinct environments."))
    used = set(named)
    for item in bundle.get("keys", ()):
        if isinstance(item, dict):
            used.update(_names(item.get("environments"))[0])
    for application in _dicts(bundle.get("applications")):
        deployed = application.get("deployed_names")
        used.update(key for key in (deployed if isinstance(deployed, dict) else ()) if isinstance(key, str))
    known = {environment.key for environment in contract.environments}
    allowed = contract.allowed_environment_keys()
    if used - known:
        failures.append(("NAMING_CONTRACT_MISMATCH", "Design bundle names an environment the naming contract does not define."))
    if any(key in known and key not in allowed for key in used):
        failures.append(("PRODUCTION_ENVIRONMENT_REFUSED", "Design bundle names a production environment."))
    return tuple(key for key in named if key in allowed)


def _names(value: Any) -> tuple[list[str], bool]:
    """The text entries of a list, and whether the value was a list of text only."""
    if value is None:
        return [], True
    if not isinstance(value, list):
        return [], False
    return [item for item in value if isinstance(item, str)], all(isinstance(item, str) for item in value)


def _applications(bundle: Mapping[str, Any], contract: NamingContract, environments: Sequence[str],
                  failures: Findings) -> None:
    """NAM-002, NAM-003 and NAM-007."""
    applications = bundle.get("applications")
    if (not isinstance(applications, list) or not applications
            or any(not isinstance(item, dict) for item in applications)
            or sum(item.get("primary") is True for item in applications) != 1):
        failures.append(("DESIGN_BUNDLE_INVALID", "Design bundle must list its applications with exactly one primary."))
        return
    names = []
    for application in applications:
        parts, name = application.get("parts"), application.get("repository_name")
        try:
            repository = _subset(parts, contract.repository_parts)
            if contract.render_repository(repository) != name or dict(contract.parse_repository(name)) != repository:
                raise NamingInvalid("repository name does not round-trip")
        except NamingInvalid:
            failures.append(("NAME_UNPARSED", "An application repository name does not render and parse under the naming contract.",
                             name if isinstance(name, str) else ""))
            continue
        names.append(name.lower())
        if application.get("primary") is True and bundle.get("repo_name", name) != name:
            failures.append(("NAME_UNPARSED", "The bundle's repository name is not its primary application's."))
        deployed = application.get("deployed_names")
        for key in environments:
            try:
                base = _subset(parts, [part for part in contract.deployed_parts if part != "environment"])
                expected = contract.render_deployed(base, key)
                if not isinstance(deployed, dict) or deployed.get(key) != expected:
                    raise NamingInvalid("deployed name differs from the rendered name")
                if "environment" in contract.deployed_parts:
                    parsed, parsed_key = contract.parse_deployed(expected)
                    if dict(parsed) != base or parsed_key != key:
                        raise NamingInvalid("deployed name does not round-trip")
            except NamingInvalid:
                failures.append(("DEPLOYED_NAME_UNPARSED", "A deployed name does not render and parse under the naming contract.", key))
    if len(set(names)) != len(names):
        failures.append(("APPLICATION_NAME_COLLISION", "Two applications share a repository name."))


def _configuration(project_dir: str, bundle: Mapping[str, Any], policy: Mapping[str, Any],
                   contract: NamingContract, environments: Sequence[str], failures: Findings) -> None:
    """NAM-005 (files and property sources) and NAM-006 (marks), for either layout.

    ``cells`` maps each expected file to the marks it must hold: key -> (kind, environment).
    A key that is absent from a file's cells must not hold a mark there.
    """
    keys = {item["key"]: item for item in bundle.get("keys", ())
            if isinstance(item, dict) and isinstance(item.get("key"), str)}

    def owed(kind: str, environment: Optional[str] = None) -> set[str]:
        return {key for key, item in keys.items() if item.get("class") == kind
                and (environment is None or environment in (item.get("environments") or ()))}

    configuration = policy.get("configuration", {})
    first = contract.configuration_paths(environments[0])
    cells: dict[str, dict[str, tuple[str, str]]] = {}
    exact = set()  # files that hold their owed keys and nothing else
    if contract.layout == LAYOUT_DEPLOYMENT_PROPERTIES:
        # One base and one secure file. Their marks are the lowest environment's defaults;
        # every other environment's value is supplied at deployment, so every key is owed everywhere.
        lowest = next(key for key in contract.allowed_environment_keys() if key in environments)
        cells[first.base] = {key: ("SET", lowest) for key in owed("env_specific")}
        if owed("secret"):
            cells[first.secure] = {key: ("ENCRYPT", lowest) for key in owed("secret")}
            exact.add(first.secure)
        if any(set(keys[key].get("environments") or ()) != set(environments)
               for key in owed("env_specific") | owed("secret")):
            failures.append(("KEY_ENVIRONMENTS_UNEVEN", "An environment-specific or secret key is not owed in every environment."))
        sources, selector, suffixes = set(cells) | {first.secure}, None, []
    else:
        cells[first.base] = {}
        sources = {first.base}
        for key in environments:
            paths = contract.configuration_paths(key)
            cells[paths.environment] = {name: ("SET", key) for name in owed("env_specific", key)}
            exact.add(paths.environment)
            if owed("secret", key):
                cells[paths.secure_environment] = {name: ("ENCRYPT", key) for name in owed("secret", key)}
                exact.add(paths.secure_environment)
        for key in contract.allowed_environment_keys():
            paths = contract.configuration_paths(key)
            sources.update((paths.environment, paths.secure_environment))
        selector = "${" + str(configuration.get("environment_selector", "env")) + "}"
        suffixes = [item.suffix for item in contract.environments if not item.production]

    present = _config_files(project_dir, contract.configuration["directory"])
    for path in sorted(set(cells) - present):
        failures.append(("CONFIGURATION_PATH_MISMATCH", "A configuration file the naming contract requires is missing.", path))
    for path in sorted(present - set(cells)):
        failures.append(("CONFIGURATION_PATH_MISMATCH", "A configuration file sits at a path the naming contract does not render.", path))

    for value in _property_sources(project_dir):
        rendered = [value.replace(selector, suffix) for suffix in suffixes] if selector and selector in value else [value]
        if any("${" in item or _RESOURCES + item not in sources for item in rendered):
            failures.append(("CONFIGURATION_PATH_MISMATCH", "Mule configuration loads a property source outside the naming contract.", value))
            break

    prefix = configuration.get("marker_prefix")
    for path, owed_cells in cells.items():
        if path not in present:
            continue
        values = _values(project_dir, path)
        missing = set(owed_cells) - set(values)
        extra = set(values) - set(owed_cells) if path in exact else set()
        wrong = [name for name, value in values.items() if name in owed_cells
                 and not _is_mark(value, prefix, *owed_cells[name])]
        stray = [name for name, value in values.items() if name not in owed_cells and _MARK.search(value)]
        for key in sorted(missing | extra | set(wrong) | set(stray)):
            failures.append(("MARKER_POLICY_VIOLATION", "A configuration file does not hold exactly its owed marks.", f"{path}: {key}"))
    for path in (first.test, first.secure_test):
        if os.path.isfile(_absolute(project_dir, path)) and any(_MARK.search(v) for v in _values(project_dir, path).values()):
            failures.append(("MARKER_POLICY_VIOLATION", "Test configuration contains an environment marker.", path))


def _is_mark(value: str, prefix: Any, kind: str, environment: str) -> bool:
    match = _MARK.fullmatch(value)
    return bool(match and match.group(2) == kind and match.group(3) == environment
                and (prefix is None or match.group(1) == prefix))


def _subset(parts: Any, names: Sequence[str]) -> dict[str, str]:
    if not isinstance(parts, dict) or any(name not in parts for name in names):
        raise NamingInvalid("application parts are incomplete")
    return {name: parts[name] for name in names}


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _absolute(project_dir: str, relative: str) -> str:
    return os.path.join(project_dir, *relative.split("/"))


def _config_files(project_dir: str, directory: str) -> set[str]:
    """Configuration files directly in the directory; sub-folders (the API contract, scripts) are not property files."""
    folder = _absolute(project_dir, directory)
    names = os.listdir(folder) if os.path.isdir(folder) else ()
    return {f"{directory.rstrip('/')}/{name}" for name in names
            if name.endswith(_CONFIG_SUFFIXES) and os.path.isfile(os.path.join(folder, name))}


def _values(project_dir: str, relative: str) -> dict[str, str]:
    values: dict[str, str] = {}
    with open(_absolute(project_dir, relative), encoding="utf-8") as handle:
        for line in handle:
            match = _PROPERTY_LINE.match(line)
            if match:
                value = match.group(2)
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[match.group(1)] = value
    return values


def _property_sources(project_dir: str) -> list[str]:
    sources = []
    for folder, _, files in os.walk(os.path.join(project_dir, "src", "main", "mule")):
        for name in sorted(files):
            if name.endswith(".xml"):
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    sources.extend(_PROPERTY_SOURCE.findall(handle.read()))
    return sources
