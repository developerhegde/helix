"""End to end, without Maven: the acme-b profile is staged, and the sample application that follows
the reference standard passes every built check; each departure from the standard is caught."""

import hashlib
import json
import os
import shutil
import tempfile
import unittest

from helix import product_identity as pid
from helix.profile.doctor import run_doctor
from helix.validation import validate
from tests.support import NOW, run_cli

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")
NAME = "acmeb-sapi-order-v1"
BOTH = ["DEV", "SIT"]
KEYS = [
    {"key": "erp.http.host", "class": "env_specific", "environments": BOTH},
    {"key": "erp.username", "class": "env_specific", "environments": BOTH},
    {"key": "erp.http.port", "class": "invariant"},
    {"key": "erp.http.base-path", "class": "invariant"},
    {"key": "erp.http.timeout-ms", "class": "invariant"},
    {"key": "erp.password", "class": "secret", "environments": BOTH},
    {"key": "http.host", "class": "invariant"},
    {"key": "http.port", "class": "deployment"},
    {"key": "api.id", "class": "deployment"},
    {"key": "secure.key", "class": "deployment"},
]
IMPL = "src/main/mule/orders-impl.xml"
DEPARTURES = [  # (expected code, file, text to find, replacement); a file that does not exist yet is created
    ("CONFIGURATION_PATH_MISMATCH", "src/main/resources/config-sit.yaml", None, "erp.http.host: ${HELIX_SET_SIT}\n"),
    ("MARKER_POLICY_VIOLATION", "src/main/resources/config.yaml", "erp.http.host: ${HELIX_SET_DEV}", "erp.http.host: acme-b-erp.example.invalid"),
    ("PLAINTEXT_SECRET", "src/main/resources/config-secure.yaml", "${HELIX_ENCRYPT_DEV}", "acme-b-plain-value"),
    ("NAME_PATTERN_VIOLATION", IMPL, 'variableName="orderId"', 'variableName="order_id"'),
    ("FREE_TEXT_LOGGER", IMPL, "<http:request ", '<logger message="free text"/><http:request '),
    ("PROPERTY_UNDEFINED", IMPL, 'path="/orders/{orderId}"', 'path="${erp.http.orders-path}"'),
    ("POM_VERSION_DECLARED", "pom.xml", "<artifactId>mule-http-connector</artifactId>", "<artifactId>mule-http-connector</artifactId><version>1.10.3</version>"),
    ("MULE_ARTIFACT_INVALID", "mule-artifact.json", ', "secure.key"', ""),
    ("MAPPING_ANCHOR_MISSING", "src/main/resources/dwl/orders/map-erp-order-to-order.dwl", "// map:MAP-001", "// mapping"),
    ("DESIGN_ARTEFACT_CHANGED", "docs/design/lld.md", "MAP-001", "MAP-002"),
    ("TEST_SUITE_MISSING", "src/test/munit/orders-impl-test-suite.xml", None, None),
    ("NAME_PATTERN_VIOLATION", "src/main/mule/order-api.xml", 'path="/api/v1/*"', 'path="/orders/*"'),
    ("GITIGNORE_INCOMPLETE", ".gitignore", "settings.xml\n", ""),
    ("LOG_LEVEL_FORBIDDEN", "src/main/resources/log4j2.xml", '<AsyncRoot level="INFO">', '<AsyncRoot level="TRACE">'),
    ("AUTODISCOVERY_MISSING", "src/main/mule/global.xml", 'apiId="${api.id}"', 'apiId="12345"'),
    ("CONNECTOR_LITERAL_VALUE", "src/main/mule/global.xml", 'host="${erp.http.host}"', 'host="erp.example.invalid"'),
    ("HTTP_TIMEOUT_MISSING", "src/main/mule/global.xml", ' responseTimeout="${erp.http.timeout-ms}"', ""),
    ("ERROR_MAPPING_MISMATCH", "src/main/mule/error-handler.xml", 'value="504"', 'value="500"'),
    ("ERROR_MAPPING_MISSING", "src/main/mule/error-handler.xml", 'type="HTTP:TIMEOUT"', 'type="HTTP:RETRY_EXHAUSTED"'),
    ("ERROR_ENVELOPE_MISSING", "src/main/mule/error-handler.xml", '<set-variable variableName="httpStatus" value="405" doc:name="Set status 405"/>', ""),
]


class GoldenStandardProjectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls.profile = shutil.copytree(os.path.join(FIXTURES, "acme-b"), os.path.join(cls._tmp.name, "acme-b"))
        staged = os.path.join(cls._tmp.name, "in", "validation")
        cls.stage_exit = run_cli("stage", "--profile", cls.profile, "--out-dir", staged)[0]
        with open(os.path.join(staged, "validation-policy.json"), encoding="utf-8") as handle:
            cls.policy = json.load(handle)
        with open(os.path.join(staged, "naming-contract.json"), encoding="utf-8") as handle:
            cls.naming = json.load(handle)

    def report(self, changes=()):
        project = shutil.copytree(os.path.join(FIXTURES, NAME), os.path.join(tempfile.mkdtemp(dir=self._tmp.name), NAME))

        def path(relative):
            return os.path.join(project, *relative.split("/"))

        def member(relative):
            with open(path(relative), "rb") as handle:
                return {"path": relative, "sha256": hashlib.sha256(handle.read()).hexdigest()}

        bundle = {  # approved before any change below, as gate two would bind it
            "schema": "design_bundle.v1", "status": "complete", "repo_name": NAME, "environments": BOTH,
            "standards_bundle_digest": self.policy["standards_bundle_digest"], "naming_contract_digest": self.naming["digest"],
            "applications": [{"role": "system", "layer": "sapi", "primary": True, "repository_name": NAME,
                              "parts": {"prefix": "acmeb", "layer": "sapi", "name": "order", "version": "v1"},
                              "deployed_names": {"DEV": NAME + "-dev", "SIT": NAME + "-sit"}}],
            "contract": member("src/main/resources/api/order-api.yaml"),
            "documents": {"hld": member("docs/design/hld.md"), "lld": member("docs/design/lld.md")},
            "keys": KEYS, "deployment_property_keys": ["api.id", "http.port", "secure.key"], "mappings": [{"id": "MAP-001"}],
        }
        os.makedirs(path("target"))
        with open(path(f"target/{pid.CANONICAL_ID}-validation-evidence.json"), "w", encoding="utf-8") as handle:
            json.dump({"schema": "mule_validation_evidence.v1", "maven": {"exit_code": 0},
                       "munit": {"tests_run": 1, "failures": 0, "errors": 0}, "coverage": {"application_percent": 80}}, handle)
        for relative, old, new in changes:
            if new is None:
                os.remove(path(relative))
                continue
            text = ""
            if old is not None:
                with open(path(relative), encoding="utf-8") as handle:
                    text = handle.read()
                self.assertIn(old, text)
            with open(path(relative), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text.replace(old, new) if old is not None else new)
        return validate(project, bundle, self.policy, self.naming)

    def test_profile_is_healthy_and_stages(self):
        self.assertEqual(run_doctor(self.profile, now=NOW).findings, ())
        self.assertEqual(self.stage_exit, 0)
        self.assertEqual(self.policy["maven"]["child_pom"]["forbid_versions"], True)

    def test_application_that_follows_the_standard_passes(self):
        report = self.report()
        self.assertEqual((report.verdict, [item.code for item in report.findings]), ("pass", []))
        self.assertEqual(report.naming_contract_digest, self.naming["digest"])

    def test_each_departure_from_the_standard_is_caught(self):
        for code, relative, old, new in DEPARTURES:
            with self.subTest(code=code):
                self.assertIn(code, [item.code for item in self.report([(relative, old, new)]).findings])

    def test_findings_name_the_offender_but_never_a_value(self):
        cases = {
            "PROPERTY_UNDEFINED": ([(IMPL, 'path="/orders/{orderId}"', 'path="${erp.http.orders-path}"')], "erp.http.orders-path"),
            "NAME_PATTERN_VIOLATION": ([(IMPL, 'variableName="orderId"', 'variableName="order_id"')], "orders-impl.xml: order_id"),
            "CONFIGURATION_PATH_MISMATCH": ([("src/main/resources/config-sit.yaml", None, "a.b: c\n")], "src/main/resources/config-sit.yaml"),
            "PLAINTEXT_SECRET": ([("src/main/resources/config-secure.yaml", "${HELIX_ENCRYPT_DEV}", "acme-b-plain-value")],
                                 "src/main/resources/config-secure.yaml: erp.password"),
        }
        for code, (changes, subject) in cases.items():
            with self.subTest(code=code):
                report = self.report(changes)
                self.assertIn((code, subject), [(item.code, item.subject) for item in report.findings])
                self.assertNotIn("acme-b-plain-value", json.dumps(report.as_dict()))


if __name__ == "__main__":
    unittest.main()
