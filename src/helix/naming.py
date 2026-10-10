"""Pure, standalone compiler for client application naming contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence


class NamingInvalid(ValueError):
    """The profile naming block does not satisfy naming_contract.v1."""


_PARTS = ("prefix", "scope", "region", "name", "layer", "version", "environment")
_FIXED_PARTS = ("prefix", "scope", "region", "layer")
_ENV_KEY = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
_ENV_SUFFIX = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
_FORBIDDEN_PATH = (".github/", ".gitlab-ci", ".mvn/", "mvnw", "src/main/resources/api/", "docs/")


@dataclass(frozen=True)
class Environment:
    key: str
    suffix: str
    order: int
    production: bool


@dataclass(frozen=True)
class ConfigurationPaths:
    base: str
    environment: str
    secure_environment: str
    test: str
    secure_test: str


@dataclass(frozen=True)
class NamingContract:
    separator: str
    repository_parts: tuple[str, ...]
    deployed_parts: tuple[str, ...]
    allowed: Mapping[str, tuple[str, ...]]
    name_pattern: str
    version_pattern: str
    environments: tuple[Environment, ...]
    configuration: Mapping[str, str]
    digest: str

    def allowed_environment_keys(self) -> tuple[str, ...]:
        return tuple(environment.key for environment in self.environments if not environment.production)

    def is_production(self, environment_key: str) -> bool:
        return self._environment(environment_key).production

    def render_repository(self, parts: Mapping[str, str]) -> str:
        return self._render(self.repository_parts, parts)

    def render_deployed(self, parts: Mapping[str, str], environment_key: str) -> str:
        values = dict(parts)
        values["environment"] = self._environment(environment_key).suffix
        return self._render(self.deployed_parts, values)

    def parse_repository(self, value: str) -> Mapping[str, str]:
        return self._parse(self.repository_parts, value)

    def parse_deployed(self, value: str) -> tuple[Mapping[str, str], str]:
        values = dict(self._parse(self.deployed_parts, value))
        suffix = values.pop("environment", None)
        matches = [environment.key for environment in self.environments if environment.suffix == suffix]
        if len(matches) != 1:
            raise NamingInvalid("deployed name has an unknown environment suffix")
        return MappingProxyType(values), matches[0]

    def configuration_paths(self, environment_key: str) -> ConfigurationPaths:
        environment = self._environment(environment_key)
        directory = self.configuration["directory"]
        test_directory = self.configuration["test_directory"]
        return ConfigurationPaths(
            base=_join(directory, self.configuration["base_file"]),
            environment=_join(directory, self.configuration["environment_file"].format(environment=environment.suffix)),
            secure_environment=_join(directory, self.configuration["secure_environment_file"].format(environment=environment.suffix)),
            test=_join(test_directory, self.configuration["test_file"]),
            secure_test=_join(test_directory, self.configuration["secure_test_file"]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "naming_contract.v1",
            "application": {
                "separator": self.separator,
                "repository_parts": list(self.repository_parts),
                "deployed_parts": list(self.deployed_parts),
                "allowed": {key: list(value) for key, value in self.allowed.items()},
                "name_pattern": self.name_pattern,
                "version_pattern": self.version_pattern,
            },
            "environments": [
                {"key": item.key, "suffix": item.suffix, "order": item.order, "production": item.production}
                for item in self.environments
            ],
            "configuration": dict(self.configuration),
        }

    def _environment(self, key: str) -> Environment:
        for environment in self.environments:
            if environment.key == key:
                return environment
        raise NamingInvalid("unknown environment key")

    def _render(self, expected: Sequence[str], parts: Mapping[str, str]) -> str:
        if set(parts) != set(expected):
            raise NamingInvalid("name parts do not match the configured form")
        values = []
        for part in expected:
            value = parts[part]
            self._validate_part(part, value)
            values.append(value)
        return self.separator.join(values)

    def _parse(self, expected: Sequence[str], value: str) -> Mapping[str, str]:
        if not isinstance(value, str):
            raise NamingInvalid("name must be text")
        values = value.split(self.separator)
        name_index = expected.index("name")
        if len(values) < len(expected):
            raise NamingInvalid("name has the wrong number of parts")
        name_width = len(values) - len(expected) + 1
        values = values[:name_index] + [self.separator.join(values[name_index:name_index + name_width])] + values[name_index + name_width:]
        parsed = dict(zip(expected, values))
        for part, item in parsed.items():
            self._validate_part(part, item)
        return MappingProxyType(parsed)

    def _validate_part(self, part: str, value: Any) -> None:
        if not isinstance(value, str) or not value:
            raise NamingInvalid("name part must be non-empty text")
        forbidden = ("/", "\\", " ", "\t", "\n", "${", "}")
        if any(token in value for token in forbidden) or (part != "name" and self.separator in value):
            raise NamingInvalid("name part has forbidden characters")
        if part in _FIXED_PARTS and value not in self.allowed[part]:
            raise NamingInvalid("name part is outside its allowlist")
        if part == "name" and re.fullmatch(self.name_pattern, value) is None:
            raise NamingInvalid("name part does not match name_pattern")
        if part == "version" and re.fullmatch(self.version_pattern, value) is None:
            raise NamingInvalid("version part does not match version_pattern")
        if part == "environment" and value not in {item.suffix for item in self.environments}:
            raise NamingInvalid("environment part is unknown")


def compile_contract(value: Any) -> NamingContract:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise NamingInvalid("naming.schema_version must be 1")
    application = _mapping(value, "application")
    separator = application.get("separator")
    if not isinstance(separator, str) or len(separator) != 1 or not separator.isprintable() or separator.isalnum() or separator in "/\\. ${}":
        raise NamingInvalid("application.separator is invalid")
    repository_parts = _parts(application, "repository")
    deployed_parts = _parts(application, "deployed")
    if "environment" in repository_parts or "environment" in deployed_parts[:-1]:
        raise NamingInvalid("environment part placement is invalid")
    allowed_value = _mapping(application, "allowed")
    allowed = {}
    for part in _FIXED_PARTS:
        entries = allowed_value.get(part)
        if not isinstance(entries, list) or not entries or not all(isinstance(item, str) and item for item in entries):
            raise NamingInvalid(f"application.allowed.{part} must be a non-empty text list")
        if len(entries) != len(set(entries)):
            raise NamingInvalid(f"application.allowed.{part} must be unique")
        allowed[part] = tuple(entries)
    name_pattern = _pattern(application, "name_pattern")
    version_pattern = _pattern(application, "version_pattern")
    environments = _environments(value.get("environments"))
    configuration = _configuration(value.get("configuration"))
    canonical = {
        "schema": "naming_contract.v1",
        "application": {
            "separator": separator,
            "repository_parts": list(repository_parts),
            "deployed_parts": list(deployed_parts),
            "allowed": {key: list(entries) for key, entries in allowed.items()},
            "name_pattern": name_pattern,
            "version_pattern": version_pattern,
        },
        "environments": [item.__dict__ for item in environments],
        "configuration": dict(configuration),
    }
    digest = hashlib.sha256(_canonical_json(canonical).encode("utf-8")).hexdigest()
    return NamingContract(separator, repository_parts, deployed_parts, MappingProxyType(allowed), name_pattern,
                          version_pattern, environments, MappingProxyType(configuration), digest)


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise NamingInvalid(f"{key} must be a mapping")
    return item


def _parts(application: Mapping[str, Any], key: str) -> tuple[str, ...]:
    form = _mapping(application, key)
    parts = form.get("parts")
    if not isinstance(parts, list) or not 2 <= len(parts) <= 8 or not all(item in _PARTS for item in parts):
        raise NamingInvalid(f"application.{key}.parts is invalid")
    if len(parts) != len(set(parts)) or "name" not in parts or "version" not in parts:
        raise NamingInvalid(f"application.{key}.parts must be unique and include name and version")
    return tuple(parts)


def _pattern(application: Mapping[str, Any], key: str) -> str:
    value = application.get(key)
    if not isinstance(value, str) or not value:
        raise NamingInvalid(f"application.{key} must be a pattern")
    try:
        re.compile(value)
    except re.error as exc:
        raise NamingInvalid(f"application.{key} is not a valid pattern") from exc
    return value


def _environments(value: Any) -> tuple[Environment, ...]:
    if not isinstance(value, list) or len(value) < 2:
        raise NamingInvalid("environments must contain at least two entries")
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise NamingInvalid("environment entry must be a mapping")
        key, suffix, order, production = item.get("key"), item.get("suffix"), item.get("order"), item.get("production")
        if not isinstance(key, str) or _ENV_KEY.fullmatch(key) is None:
            raise NamingInvalid("environment key is invalid")
        if not isinstance(suffix, str) or _ENV_SUFFIX.fullmatch(suffix) is None:
            raise NamingInvalid("environment suffix is invalid")
        if not isinstance(order, int) or isinstance(order, bool) or order < 0:
            raise NamingInvalid("environment order is invalid")
        if not isinstance(production, bool):
            raise NamingInvalid("environment production flag is invalid")
        result.append(Environment(key, suffix, order, production))
    if len({item.key for item in result}) != len(result) or len({item.suffix for item in result}) != len(result) or len({item.order for item in result}) != len(result):
        raise NamingInvalid("environment keys, suffixes, and orders must be unique")
    ordered = tuple(sorted(result, key=lambda item: item.order))
    if len([item for item in ordered if not item.production]) < 2:
        raise NamingInvalid("at least two non-production environments are required")
    return ordered


def _configuration(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise NamingInvalid("configuration must be a mapping")
    names = ("directory", "base_file", "environment_file", "secure_environment_file", "test_directory", "test_file", "secure_test_file")
    if set(value) != set(names) or not all(isinstance(value[name], str) and value[name] for name in names):
        raise NamingInvalid("configuration fields are incomplete")
    directory, test_directory = value["directory"], value["test_directory"]
    if not directory.startswith("src/main/resources/") or not test_directory.startswith("src/test/resources/"):
        raise NamingInvalid("configuration directories are outside resource roots")
    for name, path in value.items():
        path_for_validation = path.replace("{environment}", "environment")
        if (not _RELATIVE_PATH.fullmatch(path_for_validation) or path.startswith("/")
                or ".." in path.split("/") or "${" in path):
            raise NamingInvalid(f"configuration.{name} is not a safe relative path")
    for name in ("environment_file", "secure_environment_file"):
        if value[name].count("{environment}") != 1:
            raise NamingInvalid(f"configuration.{name} must contain one environment placeholder")
    for name in ("base_file", "test_file", "secure_test_file"):
        if "{environment}" in value[name]:
            raise NamingInvalid(f"configuration.{name} must not contain an environment placeholder")
    rendered = (_join(directory, value["environment_file"].format(environment="env")),
                _join(directory, value["secure_environment_file"].format(environment="env")))
    if rendered[0] == rendered[1] or any(path.startswith(prefix) for path in rendered for prefix in _FORBIDDEN_PATH):
        raise NamingInvalid("configuration paths conflict with protected paths")
    return {name: value[name].replace("\\", "/") for name in names}


def _join(directory: str, filename: str) -> str:
    return f"{directory.rstrip('/')}/{filename.lstrip('/')}"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
