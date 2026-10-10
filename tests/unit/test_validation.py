import hashlib
import json
import os
import tempfile
import unittest

from helix.validation import validate
from tests.support import run_cli


POLICY = {
    "schema": "validation_policy.v1",
    "version": 1,
    "maven": {
        "golden_parent": {"groupId": "example", "artifactId": "helix-parent", "version": "1.0.0"},
        "allowed_plugins": ["org.mule.tools.maven:mule-maven-plugin"],
        "mule_runtime": "4.9.1",
    },
    "project": {
        "forbidden_paths": [".github/**", ".mvn/**", "mvnw*"],
        "forbid_java_interop": True,
    },
    "configuration": {"allowed_property_sources": ["src/main/resources/config/config.yaml"]},
}


class ValidationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = self._tmp.name
        self._write("pom.xml", """<project><parent><groupId>example</groupId><artifactId>helix-parent</artifactId><version>1.0.0</version></parent><properties><mule.version>4.9.1</mule.version></properties><build><plugins><plugin><groupId>org.mule.tools.maven</groupId><artifactId>mule-maven-plugin</artifactId></plugin></plugins></build></project>""")
        self._write("src/main/resources/api/order.yaml", "openapi: 3.0.0\n")
        self._write("docs/design/hld.md", "# HLD\n")
        self._write("docs/design/lld.md", "# LLD\n")
        self._write("src/main/resources/config/config.yaml", "orders.base: base\n")
        self._write("src/main/resources/config/config-dev.yaml", "orders.host: ${SET_DEV}\norders.password: ${ENCRYPT_DEV}\n")
        self._write("src/main/mule/order.xml", "<mule>${orders.base} ${orders.host} ${secure::orders.password} ${env}</mule>\n")
        self._write("src/main/resources/dwl/order.dwl", "%dw 2.0\n---\n{ id: payload.id } // map:MAP-001\n")

    def _write(self, relative, text):
        path = os.path.join(self.project, *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _bundle(self):
        member = lambda path: {"path": path, "sha256": self._digest(path)}
        return {
            "schema": "design_bundle.v1",
            "standards_bundle_digest": "a" * 64,
            "contract": member("src/main/resources/api/order.yaml"),
            "documents": {"hld": member("docs/design/hld.md"), "lld": member("docs/design/lld.md")},
            "keys": [
                {"key": "orders.base", "class": "invariant"},
                {"key": "orders.host", "class": "env_specific", "environments": ["DEV"]},
                {"key": "orders.password", "class": "secret", "environments": ["DEV"]},
                {"key": "env", "class": "deployment"},
            ],
            "deployment_property_keys": ["env"],
            "mappings": [{"id": "MAP-001"}],
        }

    def _digest(self, relative):
        with open(os.path.join(self.project, *relative.split("/")), "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

    def test_golden_project_passes(self):
        report = validate(self.project, self._bundle(), POLICY)
        self.assertEqual(report.verdict, "pass")
        self.assertEqual(report.referenced_keys, ("env", "orders.base", "orders.host", "orders.password"))
        self.assertEqual(report.mappings, ("MAP-001",))

    def test_cli_emits_deterministic_json(self):
        bundle_path = os.path.join(self.project, "bundle.json")
        policy_path = os.path.join(self.project, "policy.json")
        with open(bundle_path, "w", encoding="utf-8") as handle:
            json.dump(self._bundle(), handle)
        with open(policy_path, "w", encoding="utf-8") as handle:
            json.dump(POLICY, handle)
        code, output, _ = run_cli("validate", "--project", self.project, "--bundle", bundle_path,
                                  "--policy", policy_path, "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["verdict"], "pass")

    def test_standards_digest_must_match_staged_policy(self):
        policy = {**POLICY, "standards_bundle_digest": "b" * 64}
        report = validate(self.project, self._bundle(), policy)
        self.assertEqual([item.code for item in report.findings], ["STANDARDS_BUNDLE_MISMATCH"])

    def test_policy_and_source_failures_are_reported(self):
        self._write(".github/workflows/build.yml", "name: forbidden\n")
        self._write("src/main/resources/dwl/order.dwl", "%dw 2.0\n---\njava!::typeOf(payload)\n")
        report = validate(self.project, self._bundle(), POLICY)
        self.assertEqual(report.verdict, "fail")
        self.assertEqual([item.code for item in report.findings], ["FORBIDDEN_PROJECT_PATH", "JAVA_INTEROP", "MAPPING_ANCHOR_MISSING"])

    def test_property_and_design_tampering_fail(self):
        bundle = self._bundle()
        self._write("src/main/resources/config/config-dev.yaml", "orders.host: https://example.test\norders.password: sk-ant-acmeFAKE0123456789abcdefFAKE\n")
        self._write("docs/design/hld.md", "# changed\n")
        report = validate(self.project, bundle, POLICY)
        codes = [item.code for item in report.findings]
        self.assertIn("DESIGN_ARTEFACT_CHANGED", codes)
        self.assertIn("MARKER_POLICY_VIOLATION", codes)
        self.assertIn("PLAINTEXT_SECRET", codes)


if __name__ == "__main__":
    unittest.main()
