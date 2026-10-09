"""Offline, read-only profile doctor: rules B1-001 to B1-014 in stable order.

Reads only the profile file in the directory it is given. It makes no network
call, resolves no vault reference, reads no ``.env``, and never puts a profile
value into a finding.
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .. import product_identity as pid
from . import secrets
from .policy import DEFAULT_POLICY, Policy

PROFILE_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 1
REQUIRED_FILES = (pid.PROFILE_FILENAME,)
DEFERRED_CHECKS = ("vault", "jira", "github", "anypoint", "nexus", "model_route")

PROVIDERS = ("anthropic", "bedrock", "vertex")
PHASES = ("intake", "design", "build", "test")
JIRA_STATUSES = ("needs_info", "requirement_review", "design_review")
DESIGN_KEYS = ("contract_format", "governance_ruleset", "logging")
GATES = ("requirement", "design", "merge", "deploy")

CLIENT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+$")
VAULT_REF_RE = re.compile(r"^vault://[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+$")
VAULT_PROVIDER_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VAULT_SCOPE_RE = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
HOST_RE = re.compile(rf"^(?:https://)?({_LABEL}(?:\.{_LABEL})+)$")

REMEDIATION = {
    "B1-001": f"Add {pid.PROFILE_FILENAME} to the profile directory.",
    "B1-002": f"Write {pid.PROFILE_FILENAME} as a YAML mapping with schema_version: {PROFILE_SCHEMA_VERSION}.",
    "B1-003": "Set client_id to lowercase letters and digits joined by single hyphens.",
    "B1-004": "Set provider, region, a model per phase, and positive caps with phase_cap_usd not above run_cap_usd.",
    "B1-005": "Use a permitted region, and a provider and models the policy table allows under the data-handling rules.",
    "B1-006": "List only HTTPS host names the policy table approves for the configured provider and region.",
    "B1-007": "Set the Jira cloud id, project key, bot account, webhook secret vault reference and the three statuses.",
    "B1-008": "Set the GitHub organisation, bot account and repositories, and list both bot identities in allowed_bots.",
    "B1-009": "Set the vault provider and scope as opaque identifiers, never as secret values.",
    "B1-010": "Set the business group, connected-app vault reference, environments and an ISO-8601 secret expiry.",
    "B1-011": "Remove production-like environments; only non-production environments are allowed.",
    "B1-012": "Rotate the connected-app secret and update its expiry metadata.",
    "B1-013": "Set the design defaults and at least one owner for each gate.",
    "B1-014": "Remove the value, keep it in the vault, and leave only a vault:// reference in the profile.",
}


class OperationalError(Exception):
    """The doctor cannot run: invalid invocation or an unusable profile path (exit 2)."""


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    path: str
    message: str
    remediation: str

    def as_dict(self) -> Dict[str, str]:
        return {"id": self.id, "severity": self.severity, "path": self.path,
                "message": self.message, "remediation": self.remediation}


@dataclass(frozen=True)
class Report:
    client_id: Optional[str]
    policy_version: str
    findings: Tuple[Finding, ...]

    @property
    def errors(self) -> int:
        return sum(f.severity == "error" for f in self.findings)

    @property
    def warnings(self) -> int:
        return sum(f.severity == "warning" for f in self.findings)

    @property
    def status(self) -> str:
        return "error" if self.errors else "warning" if self.warnings else "healthy"

    def exit_code(self, strict: bool = False) -> int:
        return 1 if self.errors or (strict and self.warnings) else 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "client_id": self.client_id,
            "policy_version": self.policy_version,
            "status": self.status,
            "findings": [f.as_dict() for f in self.findings],
            "deferred_checks": list(DEFERRED_CHECKS),
        }


class _Collector:
    def __init__(self) -> None:
        self.findings: List[Finding] = []

    def add(self, rule: str, path: str, message: str, severity: str = "error") -> None:
        self.findings.append(Finding(rule, severity, path, message, REMEDIATION[rule]))

    def section(self, rule: str, doc: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        value = doc.get(name)
        if isinstance(value, dict):
            return value
        self.add(rule, name, "Section is missing or not a mapping.")
        return None

    def text(self, rule: str, sec: Dict[str, Any], where: str, key: str,
             pattern: Optional["re.Pattern[str]"] = None) -> Optional[str]:
        value = sec.get(key)
        if isinstance(value, str) and value.strip() and (pattern is None or pattern.fullmatch(value)):
            return value
        self.add(rule, f"{where}.{key}", "Value is missing or malformed.")
        return None

    def strings(self, rule: str, sec: Dict[str, Any], where: str, key: str) -> Optional[List[str]]:
        value = sec.get(key)
        if isinstance(value, list) and value and all(isinstance(v, str) and v.strip() for v in value):
            return value
        self.add(rule, f"{where}.{key}", "List is missing, empty, or holds a non-text entry.")
        return None

    def positive(self, rule: str, sec: Dict[str, Any], where: str, key: str) -> Optional[float]:
        value = sec.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value < float("inf"):
            return float(value)
        self.add(rule, f"{where}.{key}", "Cap is missing or not a positive number.")
        return None


def _profile_root(path: str) -> str:
    if not os.path.isabs(path):
        raise OperationalError("profile path must be absolute")
    if not os.path.isdir(path) or not os.access(path, os.R_OK | os.X_OK):
        raise OperationalError("profile path is not a readable directory")
    return path


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise OperationalError("a profile file could not be read") from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _expiry(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, date):
        moment = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        try:
            moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _parse_profile(text: Optional[str], c: _Collector) -> Optional[Dict[str, Any]]:
    """B1-002. Returns the mapping (for the secret scan) even when the version is wrong."""
    if text is None:
        c.add("B1-002", pid.PROFILE_FILENAME, "File is not UTF-8 text.")
        return None
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        c.add("B1-002", pid.PROFILE_FILENAME, "File does not parse as YAML.")
        return None
    if not isinstance(doc, dict):
        c.add("B1-002", pid.PROFILE_FILENAME, "File is not a YAML mapping.")
        return None
    version = doc.get("schema_version")
    if isinstance(version, bool) or version != PROFILE_SCHEMA_VERSION:
        c.add("B1-002", "schema_version", "schema_version is missing or unsupported.")
    return doc


def _check_profile(doc: Dict[str, Any], c: _Collector, policy: Policy, now: datetime) -> Optional[str]:
    """B1-003 to B1-013. Returns the client id when it is valid."""
    value = doc.get("client_id")
    client_id = value if isinstance(value, str) and CLIENT_ID_RE.fullmatch(value) else None
    if client_id is None:
        c.add("B1-003", "client_id", "client_id is missing or malformed.")

    # B1-004 model route
    provider = region = None
    phases: Dict[str, Any] = {}
    route = c.section("B1-004", doc, "model_route")
    if route is not None:
        if route.get("provider") in PROVIDERS:
            provider = route["provider"]
        else:
            c.add("B1-004", "model_route.provider", "Provider is missing or not anthropic, bedrock or vertex.")
        region = c.text("B1-004", route, "model_route", "region")
        if isinstance(route.get("phases"), dict):
            phases = route["phases"]
            for phase in PHASES:
                c.text("B1-004", phases, "model_route.phases", phase)
        else:
            c.add("B1-004", "model_route.phases", "Phase models are missing or not a mapping.")
        run_cap = c.positive("B1-004", route, "model_route", "run_cap_usd")
        phase_cap = c.positive("B1-004", route, "model_route", "phase_cap_usd")
        if run_cap is not None and phase_cap is not None and phase_cap > run_cap:
            c.add("B1-004", "model_route.phase_cap_usd", "Phase cap exceeds the run cap.")

    # B1-005 data handling against the route
    handling = c.section("B1-005", doc, "data_handling")
    if handling is not None:
        permitted = c.strings("B1-005", handling, "data_handling", "permitted_regions")
        zdr = handling.get("zero_data_retention_required")
        if not isinstance(zdr, bool):
            c.add("B1-005", "data_handling.zero_data_retention_required", "Value is missing or not true/false.")
        if region is not None and permitted is not None and region not in permitted:
            c.add("B1-005", "model_route.region", "Model route region is not a permitted region.")
        if provider is not None:
            entry = policy.providers.get(provider)
            if entry is None:
                c.add("B1-005", "model_route.provider", "Provider is not in the local policy table.")
            elif zdr is True:
                if not entry.zero_data_retention:
                    c.add("B1-005", "model_route.provider",
                          "Provider is not compatible with zero data retention under the policy table.")
                for phase in PHASES:
                    model = phases.get(phase)
                    if isinstance(model, str) and policy.requires_retention(model):
                        c.add("B1-005", f"model_route.phases.{phase}",
                              "Model requires data retention, which zero data retention forbids.")

        # B1-006 allowed hosts
        hosts = handling.get("allowed_hosts")
        if not isinstance(hosts, list) or not hosts:
            c.add("B1-006", "data_handling.allowed_hosts", "Allowed hosts list is missing or empty.")
        else:
            approved = policy.approved_hosts(provider, region) if provider and region else None
            for i, host in enumerate(hosts):
                match = HOST_RE.fullmatch(host) if isinstance(host, str) else None
                if match is None:
                    c.add("B1-006", f"data_handling.allowed_hosts[{i}]", "Entry is not a valid HTTPS host name.")
                elif approved is not None and match.group(1) not in approved:
                    c.add("B1-006", f"data_handling.allowed_hosts[{i}]",
                          "Host is not approved by the policy table for this provider and region.")

    # B1-007 Jira
    jira_bot = None
    jira = c.section("B1-007", doc, "jira")
    if jira is not None:
        c.text("B1-007", jira, "jira", "cloud_id")
        c.text("B1-007", jira, "jira", "project_key", PROJECT_KEY_RE)
        c.text("B1-007", jira, "jira", "webhook_secret_ref", VAULT_REF_RE)
        jira_bot = c.text("B1-007", jira, "jira", "bot_account_id")
        statuses = jira.get("statuses")
        if isinstance(statuses, dict):
            for status in JIRA_STATUSES:
                c.text("B1-007", statuses, "jira.statuses", status)
        else:
            c.add("B1-007", "jira.statuses", "Statuses are missing or not a mapping.")

    # B1-008 GitHub
    github = c.section("B1-008", doc, "github")
    if github is not None:
        c.text("B1-008", github, "github", "organisation")
        github_bot = c.text("B1-008", github, "github", "bot_account")
        c.strings("B1-008", github, "github", "repositories")
        allowed = c.strings("B1-008", github, "github", "allowed_bots")
        if allowed is not None:
            if jira_bot is not None and jira_bot not in allowed:
                c.add("B1-008", "github.allowed_bots", "allowed_bots does not list the Jira bot identity.")
            if github_bot is not None and github_bot not in allowed:
                c.add("B1-008", "github.allowed_bots", "allowed_bots does not list the GitHub bot identity.")

    # B1-009 vault
    vault = c.section("B1-009", doc, "vault")
    if vault is not None:
        for key, pattern in (("provider", VAULT_PROVIDER_RE), ("scope", VAULT_SCOPE_RE)):
            value = c.text("B1-009", vault, "vault", key, pattern)
            if value is not None and secrets.looks_secret(value):
                c.add("B1-009", f"vault.{key}", "Value looks like a secret, not an opaque identifier.")

    # B1-010 to B1-012 Anypoint
    anypoint = c.section("B1-010", doc, "anypoint")
    if anypoint is not None:
        c.text("B1-010", anypoint, "anypoint", "business_group_id")
        c.text("B1-010", anypoint, "anypoint", "connected_app_ref", VAULT_REF_RE)
        environments = c.strings("B1-010", anypoint, "anypoint", "environments")
        expiry = _expiry(anypoint.get("secret_expiry"))
        if expiry is None:
            c.add("B1-010", "anypoint.secret_expiry", "Secret expiry is missing or not an ISO-8601 timestamp.")
        for i, env in enumerate(environments or ()):
            if policy.is_production_like(env):
                c.add("B1-011", f"anypoint.environments[{i}]", "Environment is production-like.")
        if expiry is not None:
            if expiry <= now:
                c.add("B1-012", "anypoint.secret_expiry", "Connected-app secret has expired.")
            elif expiry - now <= timedelta(days=policy.expiry_warning_days):
                c.add("B1-012", "anypoint.secret_expiry",
                      f"Connected-app secret expires within {policy.expiry_warning_days} days.", "warning")

    # B1-013 design defaults and gate owners
    design = c.section("B1-013", doc, "design")
    if design is not None:
        for key in DESIGN_KEYS:
            c.text("B1-013", design, "design", key)
    gates = c.section("B1-013", doc, "gates")
    if gates is not None:
        for gate in GATES:
            c.strings("B1-013", gates, "gates", gate)

    return client_id


def evaluate(profile_dir: str, *, now: Optional[datetime] = None,
             policy: Policy = DEFAULT_POLICY) -> Tuple[Report, Optional[Dict[str, Any]]]:
    """Run every rule. Returns the report and the parsed profile mapping, if any."""
    root = _profile_root(profile_dir)
    now = now or datetime.now(timezone.utc)
    c = _Collector()

    texts: Dict[str, Optional[str]] = {}
    for name in REQUIRED_FILES:  # B1-001
        path = os.path.join(root, name)
        try:
            regular = stat.S_ISREG(os.lstat(path).st_mode)
        except FileNotFoundError:
            regular = False
        if regular:
            texts[name] = _read(path)
        else:
            c.add("B1-001", name, "Required file is missing or is not a regular file.")

    doc = _parse_profile(texts[pid.PROFILE_FILENAME], c) if pid.PROFILE_FILENAME in texts else None
    supported = doc is not None and not any(f.id == "B1-002" for f in c.findings)
    client_id = _check_profile(doc, c, policy, now) if supported else None

    # B1-014 plaintext secrets; paths only, never values
    for path in secrets.scan(doc) if doc is not None else ():
        c.add("B1-014", path, "Field holds what looks like a plaintext secret.")

    return Report(client_id, policy.version, tuple(c.findings)), doc if supported else None


def run_doctor(profile_dir: str, *, now: Optional[datetime] = None, policy: Policy = DEFAULT_POLICY) -> Report:
    return evaluate(profile_dir, now=now, policy=policy)[0]
