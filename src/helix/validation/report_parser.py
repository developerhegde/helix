"""Allowlisted parsers that turn Maven/MUnit reports into safe validation evidence."""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from typing import Any


class ReportParseError(ValueError):
    """An expected Maven, MUnit, or coverage report is unavailable or malformed."""


def parse(project_dir: str, receipt_path: str, *, munit_report: str,
          coverage_report: str, output_path: str) -> dict[str, Any]:
    """Produce value-free ``mule_validation_evidence.v1`` from fixed report files."""
    root = _absolute_directory(project_dir)
    receipt = _load_json(root, receipt_path, "execution receipt")
    if receipt.get("schema") != "mule_execution_receipt.v1" or not isinstance(receipt.get("exit_code"), int):
        raise ReportParseError("execution receipt is invalid")
    tests = _parse_testsuite(_path(root, munit_report))
    coverage = _parse_coverage(_path(root, coverage_report))
    evidence = {
        "schema": "mule_validation_evidence.v1",
        "maven": {"exit_code": receipt["exit_code"]},
        "munit": tests,
        "coverage": {"application_percent": coverage},
    }
    destination = _path(root, output_path)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(evidence, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
    return evidence


def _absolute_directory(path: str) -> str:
    if not os.path.isabs(path) or not os.path.isdir(path):
        raise ReportParseError("project directory must be absolute and readable")
    return os.path.realpath(path)


def _path(root: str, relative: str) -> str:
    if not isinstance(relative, str) or not relative or os.path.isabs(relative):
        raise ReportParseError("report path must be a non-empty relative path")
    path = os.path.realpath(os.path.join(root, *relative.replace("\\", "/").split("/")))
    if os.path.commonpath((root, path)) != root:
        raise ReportParseError("report path escapes the project directory")
    return path


def _load_json(root: str, relative: str, label: str) -> dict[str, Any]:
    try:
        with open(_path(root, relative), encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportParseError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise ReportParseError(f"{label} is invalid")
    return value


def _parse_testsuite(path: str) -> dict[str, int]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ReportParseError("MUnit report is unreadable") from exc
    suites = [root] if _local_name(root.tag) == "testsuite" else list(root.findall(".//testsuite"))
    if not suites:
        raise ReportParseError("MUnit report has no test suite")
    totals = {"tests_run": 0, "failures": 0, "errors": 0}
    for suite in suites:
        values = {key: suite.get(key, "0") for key in ("tests", "failures", "errors")}
        try:
            totals["tests_run"] += int(values["tests"])
            totals["failures"] += int(values["failures"])
            totals["errors"] += int(values["errors"])
        except ValueError as exc:
            raise ReportParseError("MUnit report counts are invalid") from exc
    if totals["tests_run"] < 0 or totals["failures"] < 0 or totals["errors"] < 0:
        raise ReportParseError("MUnit report counts are invalid")
    return totals


def _parse_coverage(path: str) -> float:
    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportParseError("coverage report is unreadable") from exc
    if not isinstance(value, dict):
        raise ReportParseError("coverage report is invalid")
    coverage = value.get("application_percent")
    if not isinstance(coverage, (int, float)) or isinstance(coverage, bool) or not 0 <= coverage <= 100:
        raise ReportParseError("coverage report percentage is invalid")
    return float(coverage)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
