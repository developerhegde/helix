"""Plaintext-secret tripwire (B1-009, B1-014).

Detection by key name and value shape. It is a tripwire, not proof of absence,
and it returns field paths only: a detected value is never returned or printed.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Mapping

REFERENCE_PREFIX = "vault://"

_SECRET_KEY = re.compile(r"password|passwd|pwd|secret|token|api_?key|private_?key|credential|passphrase", re.I)
_METADATA_KEY = re.compile(r"_expiry$", re.I)
_VALUE_SHAPES = (
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
)
_HIGH_ENTROPY = re.compile(r"^[A-Za-z0-9+/=_-]{40,}$")


def looks_secret(value: str) -> bool:
    if any(p.search(value) for p in _VALUE_SHAPES):
        return True
    v = value.strip()
    return bool(
        _HIGH_ENTROPY.match(v)
        and any(c.islower() for c in v)
        and any(c.isupper() for c in v)
        and any(c.isdigit() for c in v)
    )


def _secret_named(key: str) -> bool:
    return bool(_SECRET_KEY.search(key)) and not _METADATA_KEY.search(key)


def scan(data: Any, prefix: str = "") -> List[str]:
    """Field paths whose string value looks like a plaintext secret."""
    hits: List[str] = []

    def walk(node: Any, path: str, key: str) -> None:
        if isinstance(node, Mapping):
            for k, v in node.items():
                ks = str(k)
                walk(v, f"{path}.{ks}" if path else ks, ks)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", key)
        elif isinstance(node, str) and node.strip():
            named = _secret_named(key) and not node.startswith(REFERENCE_PREFIX)
            if named or looks_secret(node):
                hits.append(path)

    walk(data, prefix, "")
    return hits


def scan_dotenv(values: Mapping[str, str], credential_keys: Iterable[str]) -> List[str]:
    """Like ``scan`` for parsed ``.env`` pairs, plus Meridian's refused credential keys."""
    hits = scan(dict(values))
    for key in credential_keys:
        if values.get(key, "").strip() and key not in hits:
            hits.append(key)
    return hits
