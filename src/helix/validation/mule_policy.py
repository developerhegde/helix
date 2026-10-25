"""Mule source checks taken from the client standards: names, structure, logging and MUnit suites.

Every check is switched on by a field of the staged ``validation_policy.v1``; a policy
without the field skips the check. A finding names the file and element at fault, never a value.
"""

from __future__ import annotations

import fnmatch
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable, Mapping

Findings = list[tuple[str, ...]]  # (code, message[, subject])

_MAIN, _TESTS, _RESOURCES = "src/main/mule", "src/test/munit", "src/main/resources"
_GENERATED_FLOW = re.compile(r":|-(?:main|console)$")  # APIkit's generated and scaffolded flows keep their names
_KEY_CLASSES = ("invariant", "env_specific", "secret")
_NAMED = {  # pattern name -> (element local name, attribute, message)
    "implementation_flow": ("flow", "name", "An implementation flow name does not match the standard."),
    "sub_flow": ("sub-flow", "name", "A sub-flow name does not match the standard."),
    "flow_variable": ("set-variable", "variableName", "A flow variable name does not match the standard."),
    "error_type": ("raise-error", "type", "A raised error type does not match the standard."),
    "object_store": ("object-store", "name", "An Object Store name does not match the standard."),
    "listener_path": ("listener", "path", "An HTTP listener path does not match the standard."),
}
_PLACEHOLDER = re.compile(r"\$\{[^}]+\}")
_FROM_PROPERTIES = ("host", "port", "username", "password", "url", "basePath")  # never literal on a connection


def check(project_dir: str, bundle: Mapping[str, Any], policy: Mapping[str, Any]) -> Findings:
    patterns, mule, logging, testing = (_section(policy, name) for name in ("patterns", "mule", "logging", "testing"))
    failures: Findings = []
    try:
        compiled = {name: re.compile(text) for name, text in patterns.items() if isinstance(text, str)}
        ticket = re.compile(testing["ignored_needs_ticket"]) if isinstance(testing.get("ignored_needs_ticket"), str) else None
    except re.error:
        return [("VALIDATION_POLICY_INVALID", "Validation policy holds an invalid pattern.")]

    suffix = testing.get("suite_per_implementation")
    suffix = suffix if isinstance(suffix, str) and suffix else None
    check_tests = bool(testing.get("forbid_sleep") or ticket or suffix)
    if not (patterns or mule or logging or check_tests):
        return []  # no standards check is switched on, so no file is read
    documents = _parse(project_dir, _MAIN, failures)
    elements = [(name, element) for name, root in documents for element in root.iter()]

    def bad(pattern: str, values: Iterable[str], message: str) -> None:
        for value in values if pattern in compiled else ():
            if compiled[pattern].fullmatch(value.split(": ", 1)[-1]) is None:
                failures.append(("NAME_PATTERN_VIOLATION", message, value))

    for pattern, (local, attribute, message) in _NAMED.items():
        values = [f"{name}: {element.get(attribute, '')}" for name, element in elements
                  if _local(element.tag) == local and attribute in element.attrib]
        if pattern == "implementation_flow":
            values = [value for value in values if not _GENERATED_FLOW.search(value.split(": ", 1)[-1])]
        bad(pattern, values, message)
    configs = [f"{name}: {element.get('name', '')}" for name, element in elements
               if (_local(element.tag) == "config" or _local(element.tag).endswith("-config")) and "name" in element.attrib
               and "apikit" not in element.tag]  # the router is named for its API, not for a system and connector
    bad("connector_config", configs, "A connector configuration name does not match the standard.")
    keys = [item["key"] for item in bundle.get("keys", ())
            if isinstance(item, dict) and isinstance(item.get("key"), str) and item.get("class") in _KEY_CLASSES]
    bad("property_key", keys, "A property key does not match the standard.")
    bad("feature_flag", [key for key in keys if key.startswith("feature.")], "A feature flag key does not match the standard.")
    bad("mule_file", [name for name, _ in documents], "A Mule configuration file name does not match the standard.")
    for pattern, folder, message in (("dataweave_script", "dwl", "A DataWeave script path does not match the standard."),
                                     ("dataweave_module", "modules", "A DataWeave module path does not match the standard.")):
        bad(pattern, _relative_files(project_dir, f"{_RESOURCES}/{folder}", ".dwl", _RESOURCES), message)

    handler_file = mule.get("error_handler_file")
    if isinstance(handler_file, str):
        in_flow = any(_local(child.tag) == "error-handler" for _, element in elements
                      if _local(element.tag) in ("flow", "sub-flow") for child in element)
        global_handlers = [name for name, root in documents for child in root if _local(child.tag) == "error-handler"]
        if in_flow or global_handlers != [handler_file]:
            failures.append(("ERROR_HANDLER_MISPLACED", "Error handling is not one global handler in the standard's file."))
    if mule.get("forbid_on_error_continue_any") and any(
            _local(element.tag) == "on-error-continue" and "ANY" in re.split(r"[,\s]+", element.get("type", "ANY"))
            for _, element in elements):
        failures.append(("ON_ERROR_CONTINUE_ANY", "An on-error-continue handles every error type."))
    if mule.get("require_request_validation"):
        routers = [element for _, element in elements if _local(element.tag) == "config" and "apikit" in element.tag]
        if len(routers) > 1:
            failures.append(("APIKIT_ROUTER_NOT_SINGLE", "More than one APIkit router is configured."))
        if any(router.get("disableValidations", "false").lower() == "true" for router in routers):
            failures.append(("APIKIT_VALIDATION_DISABLED", "APIkit request validation is switched off."))
    if mule.get("api_properties"):  # STD-API-06
        if not any(_local(element.tag) == "autodiscovery" and _PLACEHOLDER.fullmatch(element.get("apiId", ""))
                   for _, element in elements):
            failures.append(("AUTODISCOVERY_MISSING", "API autodiscovery is missing or its apiId is not a property."))
        for name, element in elements:
            if (_local(element.tag) == "flow" and element.get("name", "").endswith("-console")
                    and not _PLACEHOLDER.fullmatch(element.get("initialState", ""))):
                failures.append(("CONSOLE_STATE_HARDCODED", "The API console's state is not a property.", f"{name}: {element.get('name')}"))
    if mule.get("connector_values_from_properties"):  # STD-CON-02
        for name, element in elements:
            local = _local(element.tag)
            if local.endswith("connection") or local.endswith("-config") or local.endswith("-authentication"):
                for attribute in _FROM_PROPERTIES:
                    value = element.get(attribute)
                    if value is not None and not _PLACEHOLDER.fullmatch(value):
                        failures.append(("CONNECTOR_LITERAL_VALUE", "A connection value is written literally instead of read from a property.",
                                         f"{name}: {local}@{attribute}"))
    if mule.get("require_http_timeouts"):  # STD-CON-03
        for name, element in elements:
            if _local(element.tag) == "request-config" and not _PLACEHOLDER.fullmatch(element.get("responseTimeout", "")):
                failures.append(("HTTP_TIMEOUT_MISSING", "An HTTP requester has no response timeout from a property.",
                                 f"{name}: {element.get('name', '')}"))
    failures.extend(_error_handling(project_dir, documents, mule))
    log4j2 = logging.get("log4j2")
    if isinstance(log4j2, dict):  # STD-LOG-04
        failures.extend(_log_levels(project_dir, log4j2))
    if logging.get("forbid_free_text_logger"):
        allowed = logging.get("log_event_subflow")
        loggers = sum(_local(element.tag) == "logger" for _, element in elements)
        permitted = sum(_local(inner.tag) == "logger" for _, element in elements
                        if _local(element.tag) == "sub-flow" and element.get("name") == allowed for inner in element.iter())
        if loggers > permitted:
            failures.append(("FREE_TEXT_LOGGER", "A free-text logger is used outside the approved logging path."))

    suites = _parse(project_dir, _TESTS, failures) if check_tests else []
    tests = [element for _, root in suites for element in root.iter()]
    if testing.get("forbid_sleep") and any(_local(element.tag) == "sleep" for element in tests):
        failures.append(("TEST_SLEEP", "An MUnit test sleeps."))
    if ticket is not None and any(_local(element.tag) == "test" and element.get("ignore", "").lower() == "true"
                                  and not ticket.search(element.get("description", "")) for element in tests):
        failures.append(("TEST_IGNORED_WITHOUT_TICKET", "An MUnit test is ignored without a ticket reference."))
    if suffix:
        present = {name for name, _ in suites}
        if any(name.endswith(suffix) and f"{name[:-len('.xml')]}-test-suite.xml" not in present for name, _ in documents):
            failures.append(("TEST_SUITE_MISSING", "An implementation file has no MUnit suite."))
    return list(dict.fromkeys(failures))


def _error_handling(project_dir: str, documents: list[tuple[str, ET.Element]], mule: Mapping[str, Any]) -> Findings:
    """STD-ERR-06 to 08: every branch of the global handler sets the status and renders the shared envelope,
    and error types map to statuses as the standard's table says."""
    script, mappings = mule.get("error_envelope_script"), mule.get("error_mappings")
    if not isinstance(script, str) and not isinstance(mappings, list):
        return []
    failures: Findings = []
    branches = []  # (file, types, status, renders the envelope)
    for name, root in documents:
        for handler in root:
            if _local(handler.tag) != "error-handler":
                continue
            for branch in handler:
                if _local(branch.tag) not in ("on-error-propagate", "on-error-continue"):
                    continue
                status = next((item.get("value") for item in branch.iter() if _local(item.tag) == "set-variable"
                               and item.get("variableName") == "httpStatus"), None)
                renders = any(_local(item.tag) == "set-payload" and item.get("resource") == script for item in branch.iter())
                types = [part.strip() for part in branch.get("type", "ANY").split(",") if part.strip()]
                branches.append((name, types, status, renders))
    if isinstance(script, str):
        if not os.path.isfile(os.path.join(project_dir, *_RESOURCES.split("/"), *script.split("/"))):
            failures.append(("ERROR_ENVELOPE_MISSING", "The shared error-envelope script is missing.", script))
        for name, types, status, renders in branches:
            if status is None or not renders:
                failures.append(("ERROR_ENVELOPE_MISSING", "An error branch does not set the status and render the shared envelope.",
                                 f"{name}: {', '.join(types)}"))
    rows = [([str(item) for item in row.get("types", [])], str(row.get("status"))) for row in mappings or ()
            if isinstance(row, dict) and isinstance(row.get("types"), list)]
    handled = [error_type for _, types, _, _ in branches for error_type in types]
    # Mule refuses a handler for an error type that cannot occur, so a row is owed only when one of its types can:
    # ANY and wildcard namespaces always, a connector's types when its namespace is used, APP types when raised.
    elements = [element for _, root in documents for element in root.iter()]
    used = {element.tag[1:].split("}", 1)[0].rsplit("/", 1)[-1] for element in elements if element.tag.startswith("{")}
    raised = {element.get(attribute, "") for element in elements for attribute in ("type", "targetType")
              if _local(element.tag) in ("raise-error", "error-mapping")}

    def can_occur(pattern: str) -> bool:
        namespace = pattern.split(":", 1)[0]
        if pattern == "ANY" or namespace == "*":
            return True
        if namespace == "APP":
            return any(fnmatch.fnmatchcase(error_type, pattern) for error_type in raised)
        return any(namespace.lower() in uri for uri in used)

    for patterns, _ in rows:
        if any(can_occur(pattern) for pattern in patterns) and not any(
                fnmatch.fnmatchcase(error_type, pattern) for pattern in patterns for error_type in handled):
            failures.append(("ERROR_MAPPING_MISSING", "An error type of the standard's table has no handler branch.", ", ".join(patterns)))
    for name, types, status, _ in branches:
        for error_type in types:
            row = next((row for row in rows if any(fnmatch.fnmatchcase(error_type, pattern) for pattern in row[0])), None)
            if row is not None and status != row[1]:
                failures.append(("ERROR_MAPPING_MISMATCH", "An error branch sets a status other than the standard's table.",
                                 f"{name}: {error_type}"))
    return failures


def _log_levels(project_dir: str, rules: Mapping[str, Any]) -> Findings:
    path = os.path.join(project_dir, *_RESOURCES.split("/"), "log4j2.xml")
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return [("LOG_LEVEL_FORBIDDEN", "log4j2.xml is missing or not well-formed.", "log4j2.xml")]
    failures: Findings = []
    allowed = {str(level).upper() for level in rules.get("root_levels", ())}
    for element in root.iter():
        level = element.get("level")
        if level is None:
            continue
        if rules.get("forbid_trace") and level.upper() == "TRACE":
            failures.append(("LOG_LEVEL_FORBIDDEN", "A logger is set to TRACE.", f"log4j2.xml: {_local(element.tag)}"))
        if (_local(element.tag) in ("Root", "AsyncRoot") and allowed and level.upper() not in allowed
                and not _PLACEHOLDER.fullmatch(level)):
            failures.append(("LOG_LEVEL_FORBIDDEN", "The root logger level is not an approved level.", f"log4j2.xml: {_local(element.tag)}"))
    return failures


def _section(policy: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = policy.get(name)
    return value if isinstance(value, dict) else {}


def _local(tag: Any) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _relative_files(project_dir: str, folder: str, suffix: str, base: str) -> list[str]:
    root = os.path.join(project_dir, *folder.split("/"))
    start = os.path.join(project_dir, *base.split("/"))
    return sorted(os.path.relpath(os.path.join(directory, name), start).replace("\\", "/")
                  for directory, _, files in os.walk(root) for name in files if name.endswith(suffix))


def _parse(project_dir: str, folder: str, failures: Findings) -> list[tuple[str, ET.Element]]:
    """Every XML file under the folder as (file name, root); a malformed file is a finding."""
    documents = []
    root = os.path.join(project_dir, *folder.split("/"))
    for directory, _, files in sorted(os.walk(root)):
        for name in sorted(files):
            if not name.endswith(".xml"):
                continue
            try:
                documents.append((name, ET.parse(os.path.join(directory, name)).getroot()))
            except ET.ParseError:
                failures.append(("MULE_XML_INVALID", "A Mule XML file is not well-formed."))
    return documents
