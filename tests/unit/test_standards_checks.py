"""Standards checks in the validator: child POM rules, mule-artifact.json, names, structure, logging and MUnit suites."""

import hashlib
import json
import os
import tempfile
import unittest

from helix import product_identity as pid
from helix.validation import validate
from tests.unit.test_validation import POLICY as BASE

NAME = "acme-src-glb-order-sys-v1"
CORE = "http://www.mulesoft.org/schema/mule/core"
POLICY = {
    **BASE,
    "maven": {**BASE["maven"], "group_id": "acme-org-id", "allowed_connectors": ["org.mule.connectors:mule-http-connector"],
              "child_pom": {"forbid_versions": True, "forbid_profiles": True, "forbid_final_name": True,
                            "require_semver": True, "artifact_is_repository_name": True}},
    "project": {**BASE["project"], "mule_artifact": {"min_mule_version": "4.9", "java": "17", "secure_key": "secure.key"}},
    "patterns": {
        "implementation_flow": "[a-z]+(-[a-z0-9]+)+-flow", "sub_flow": "[a-z]+(-[a-z0-9]+)+-subflow",
        "connector_config": "[a-z0-9]+(-[a-z0-9]+)+-config", "property_key": r"[a-z][a-z0-9]*(\.[a-z][a-z0-9-]*)+",
        "flow_variable": "[a-z][A-Za-z0-9]*", "error_type": "APP:[A-Z][A-Z0-9_]*", "object_store": "[a-z0-9]+(-[a-z0-9]+)*-os",
        "feature_flag": r"feature\.[a-z0-9-]+\.enabled", "dataweave_script": r"dwl/[a-z0-9-]+/[a-z0-9-]+\.dwl",
        "dataweave_module": r"modules/[A-Z][A-Za-z0-9]*\.dwl"},
    "mule": {"error_handler_file": "error-handler.xml", "forbid_on_error_continue_any": True, "require_request_validation": True},
    "logging": {"forbid_free_text_logger": True, "log_event_subflow": "log-event-subflow"},
    "testing": {**BASE["testing"], "forbid_sleep": True, "ignored_needs_ticket": "[A-Z][A-Z0-9]+-[0-9]+",
                "suite_per_implementation": "-impl.xml"},
}
POM, ARTIFACT, IMPL = "pom.xml", "mule-artifact.json", "src/main/mule/orders-impl.xml"
HANDLER, SUITE = "src/main/mule/error-handler.xml", "src/test/munit/orders-impl-test-suite.xml"
SCRIPT = "src/main/resources/dwl/orders/map-order.dwl"
FILES = {
    POM: f"<project><parent><groupId>example</groupId><artifactId>helix-parent</artifactId><version>1.0.0</version></parent>"
         f"<groupId>acme-org-id</groupId><artifactId>{NAME}</artifactId><version>1.0.0</version>"
         "<properties><mule.version>4.9.1</mule.version></properties><build><plugins><plugin>"
         "<groupId>org.mule.tools.maven</groupId><artifactId>mule-maven-plugin</artifactId></plugin></plugins></build>"
         "<dependencies><dependency><groupId>org.mule.connectors</groupId><artifactId>mule-http-connector</artifactId>"
         "<classifier>mule-plugin</classifier></dependency></dependencies></project>",
    ARTIFACT: json.dumps({"minMuleVersion": "4.9.1", "javaSpecificationVersions": ["17"],
                          "secureProperties": ["secure::orders.password", "secure.key"]}),
    IMPL: f'<mule xmlns="{CORE}" xmlns:http="{CORE}/http" xmlns:apikit="{CORE}/mule-apikit" xmlns:os="{CORE}/os">'
          '<http:listener-config name="http-listener-config"/><apikit:config name="orders-config"/>'
          '<os:object-store name="erp-token-cache-os"/><flow name="orders-main"/>'
          '<flow name="get:\\orders:orders-config"><flow-ref name="get-orders-flow"/></flow><flow name="get-orders-flow">'
          '<set-variable variableName="orderId" value="${orders.base} ${orders.host} ${secure::orders.password}"/>'
          '<raise-error type="APP:ORDER_NOT_FOUND"/></flow>'
          '<sub-flow name="log-event-subflow"><logger message="event"/></sub-flow></mule>',
    HANDLER: f'<mule xmlns="{CORE}"><error-handler name="global-error-handler">'
             '<on-error-propagate type="APP:ORDER_NOT_FOUND"/></error-handler></mule>',
    SUITE: f'<mule xmlns="{CORE}" xmlns:munit="{CORE}/munit"><munit:test name="get-orders-flow-returns-orders-test" '
           'description="returns the orders"/></mule>',
    SCRIPT: "%dw 2.0\n---\n{ id: payload.id } // map:MAP-001\n",
    "src/main/resources/modules/OrderFunctions.dwl": "%dw 2.0\nfun id(x) = x\n",
    "src/main/resources/api/order.yaml": "openapi: 3.0.0\n",
    "docs/design/hld.md": "# HLD\n",
    "docs/design/lld.md": "# LLD\n",
    "src/main/resources/config/config.yaml": "orders.base: base\n",
    "src/main/resources/config/config-dev.yaml": "orders.host: ${SET_DEV}\norders.password: ${ENCRYPT_DEV}\n",
    f"target/{pid.CANONICAL_ID}-validation-evidence.json": json.dumps({
        "schema": "mule_validation_evidence.v1", "maven": {"exit_code": 0},
        "munit": {"tests_run": 4, "failures": 0, "errors": 0}, "coverage": {"application_percent": 80}}),
}
# (expected code, file, text to find, replacement); a replacement of None deletes the file
CASES = [
    ("POM_VERSION_DECLARED", POM, "<classifier>mule-plugin", "<version>1.2.3</version><classifier>mule-plugin"),
    ("POM_VERSION_RANGE", POM, "<classifier>mule-plugin", "<version>[1.0,2.0)</version><classifier>mule-plugin"),
    ("POM_PROFILE_DECLARED", POM, "<dependencies>", "<profiles/><dependencies>"),
    ("POM_FINAL_NAME_OVERRIDDEN", POM, "<build>", "<build><finalName>acme</finalName>"),
    ("POM_VERSION_NOT_SEMVER", POM, f"{NAME}</artifactId><version>1.0.0", f"{NAME}</artifactId><version>1.0"),
    ("POM_GROUP_MISMATCH", POM, "<groupId>acme-org-id", "<groupId>acme-other-id"),
    ("POM_ARTIFACT_MISMATCH", POM, f"<artifactId>{NAME}", "<artifactId>acme-other-v1"),
    ("POM_CONNECTOR_NOT_ALLOWED", POM, "mule-http-connector", "mule-acme-connector"),
    ("MULE_ARTIFACT_INVALID", ARTIFACT, '"secure::orders.password", ', ""),
    ("MULE_ARTIFACT_INVALID", ARTIFACT, '["17"]', '["11"]'),
    ("MULE_ARTIFACT_INVALID", ARTIFACT, None, None),
    ("NAME_PATTERN_VIOLATION", IMPL, 'name="get-orders-flow"', 'name="getOrders"'),
    ("NAME_PATTERN_VIOLATION", IMPL, 'variableName="orderId"', 'variableName="order_id"'),
    ("NAME_PATTERN_VIOLATION", IMPL, 'type="APP:ORDER_NOT_FOUND"/></flow>', 'type="ORDER_NOT_FOUND"/></flow>'),
    ("NAME_PATTERN_VIOLATION", IMPL, 'name="http-listener-config"', 'name="HttpListener"'),
    ("NAME_PATTERN_VIOLATION", IMPL, 'name="erp-token-cache-os"', 'name="tokens"'),
    ("NAME_PATTERN_VIOLATION", SCRIPT, "%dw", "%dw"),  # see test: the script is moved out of its resource folder
    ("ERROR_HANDLER_MISPLACED", IMPL, "<raise-error", "<error-handler/><raise-error"),
    ("ERROR_HANDLER_MISPLACED", HANDLER, None, None),
    ("ON_ERROR_CONTINUE_ANY", HANDLER, "<on-error-propagate", "<on-error-continue/><on-error-propagate"),
    ("APIKIT_VALIDATION_DISABLED", IMPL, '<apikit:config name="orders-config"', '<apikit:config disableValidations="true" name="orders-config"'),
    ("FREE_TEXT_LOGGER", IMPL, "<raise-error", '<logger message="free text"/><raise-error'),
    ("TEST_SLEEP", SUITE, "</mule>", "<munit:sleep/></mule>"),
    ("TEST_IGNORED_WITHOUT_TICKET", SUITE, 'description="returns', 'ignore="true" description="returns'),
    ("TEST_SUITE_MISSING", SUITE, None, None),
    ("MULE_XML_INVALID", IMPL, "</mule>", ""),
]


class StandardsChecksTest(unittest.TestCase):
    def codes(self, changes=(), policy=POLICY, moved=None):
        with tempfile.TemporaryDirectory() as project:
            files = dict(FILES)
            for path, old, new in changes:
                if old is None:
                    del files[path]
                else:
                    self.assertIn(old, files[path])
                    files[path] = files[path].replace(old, new)
            if moved:
                files[moved[1]] = files.pop(moved[0])
            digests = {}
            for relative, text in files.items():
                path = os.path.join(project, *relative.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
                digests[relative] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            member = lambda path: {"path": path, "sha256": digests[path]}
            bundle = {
                "schema": "design_bundle.v1", "standards_bundle_digest": "a" * 64, "repo_name": NAME,
                "contract": member("src/main/resources/api/order.yaml"),
                "documents": {"hld": member("docs/design/hld.md"), "lld": member("docs/design/lld.md")},
                "keys": [{"key": "orders.base", "class": "invariant"},
                         {"key": "orders.host", "class": "env_specific", "environments": ["DEV"]},
                         {"key": "orders.password", "class": "secret", "environments": ["DEV"]}],
                "deployment_property_keys": [], "mappings": [{"id": "MAP-001"}],
            }
            return [item.code for item in validate(project, bundle, policy).findings]

    def test_project_that_follows_the_standards_passes(self):
        self.assertEqual(self.codes(), [])

    def test_each_departure_is_reported(self):
        for code, path, old, new in CASES:
            with self.subTest(code=code, change=new):
                moved = (SCRIPT, "src/main/resources/dwl/map-order.dwl") if path == SCRIPT else None
                self.assertIn(code, self.codes([] if moved else [(path, old, new)], moved=moved))

    def test_checks_are_off_without_their_policy_field(self):
        changes = [(path, old, new) for code, path, old, new in CASES
                   if code in ("POM_PROFILE_DECLARED", "FREE_TEXT_LOGGER", "TEST_SLEEP")]
        self.assertEqual(self.codes(changes, policy=BASE), [])


if __name__ == "__main__":
    unittest.main()
