"""File-bound scans of Mule XML and DataWeave project sources."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import FrozenSet, Iterable


_PROPERTY = re.compile(r"\$\{(?:(secure)::)?([A-Za-z][A-Za-z0-9_.-]*)\}")
_DYNAMIC = re.compile(r"\$\{[^}]*[\[({]")
_MAPPING = re.compile(r"//\s*map:(MAP-[0-9]{3,})\b")


@dataclass(frozen=True)
class SourceScan:
    properties: FrozenSet[str]
    secure_properties: FrozenSet[str]
    mappings: FrozenSet[str]
    dynamic_references: tuple[str, ...]
    java_interop: tuple[str, ...]


def scan(project_dir: str) -> SourceScan:
    properties: set[str] = set()
    secure: set[str] = set()
    mappings: set[str] = set()
    dynamic: list[str] = []
    java: list[str] = []
    for path in _source_files(project_dir):
        text = _read(path)
        relative = _relative(project_dir, path)
        for match in _PROPERTY.finditer(text):
            (secure if match.group(1) else properties).add(match.group(2))
        if _DYNAMIC.search(text):
            dynamic.append(relative)
        mappings.update(_MAPPING.findall(text))
        if "java!" in text or "java::" in text:
            java.append(relative)
    return SourceScan(frozenset(properties), frozenset(secure), frozenset(mappings), tuple(sorted(dynamic)), tuple(sorted(java)))


def _source_files(project_dir: str) -> Iterable[str]:
    root = os.path.join(project_dir, "src", "main")
    if not os.path.isdir(root):
        return ()
    return tuple(os.path.join(folder, name) for folder, _, files in os.walk(root)
                 for name in files if name.endswith((".xml", ".dwl")))


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _relative(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace("\\", "/")
