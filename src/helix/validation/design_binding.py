"""Approved design-bundle integrity checks."""

from __future__ import annotations

import hashlib
import os
from typing import Any


def check(project_dir: str, bundle: dict[str, Any]) -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    contract = bundle.get("contract")
    documents = bundle.get("documents", {})
    members = []
    if isinstance(contract, dict):
        members.append(contract)
    if isinstance(documents, dict):
        members.extend(item for item in documents.values() if isinstance(item, dict))
    for member in members:
        path, digest = member.get("path"), member.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            failures.append(("DESIGN_BUNDLE_INVALID", "Design bundle member is incomplete."))
            continue
        actual_path = os.path.join(project_dir, *path.split("/"))
        if not os.path.isfile(actual_path) or _sha256(actual_path) != digest:
            failures.append(("DESIGN_ARTEFACT_CHANGED", "Approved design artefact does not match its digest."))
    return list(dict.fromkeys(failures))


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
