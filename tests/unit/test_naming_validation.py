"""NAM-001 to NAM-007, the incomplete verdict, and the `verify` command."""

import copy
import hashlib
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from helix import product_identity as pid
from helix.naming import compile_contract
from helix.validation import validate
from tests.support import FIXTURE, run_cli
from tests.unit.test_validation import POLICY as BASE_POLICY

with open(os.path.join(FIXTURE, pid.PROFILE_FILENAME), encoding="utf-8") as _handle:
    CONTRACT = compile_contract(yaml.safe_load(_handle)["naming"])
POLICY = {**BASE_POLICY, "configuration": {**BASE_POLICY["configuration"], "environment_selector": "env",
                                           "marker_prefix": "HELIX"}}
PARTS = {"prefix": "acme", "scope": "src", "region": "glb", "name": "order", "layer": "sys", "version": "v1"}
NAME = "acme-src-glb-order-sys-v1"
CONFIG = "src/main/resources/config/"
EVIDENCE = f"target/{pid.CANONICAL_ID}-validation-evidence.json"
FILES = {
    "pom.xml": "<project><parent><groupId>example</groupId><artifactId>helix-parent</artifactId><version>1.0.0</version></parent>"
               "<properties><mule.version>4.9.1</mule.version></properties><build><plugins><plugin>"
               "<groupId>org.mule.tools.maven</groupId><artifactId>mule-maven-plugin</artifactId></plugin></plugins></build></project>",
    "src/main/resources/api/order.yaml": "openapi: 3.0.0\n",
    "docs/design/hld.md": "# HLD\n",
    "docs/design/lld.md": "# LLD\n",
    CONFIG + "config.yaml": "orders.base: base\n",
    CONFIG + "config-dev.yaml": "orders.host: ${HELIX_SET_DEV}\n",
    CONFIG + "config-sit.yaml": "orders.host: ${HELIX_SET_SIT}\n",
    CONFIG + "config-secure-dev.yaml": "orders.password: ${HELIX_ENCRYPT_DEV}\n",
    CONFIG + "config-secure-sit.yaml": "orders.password: ${HELIX_ENCRYPT_SIT}\n",
    "src/main/mule/global.xml": '<mule><configuration-properties file="config/config.yaml"/>'
                                '<configuration-properties file="config/config-${env}.yaml"/>'
                                '<secure-properties:config file="config/config-secure-${env}.yaml" key="${secure.key}"/></mule>\n',
    "src/main/mule/order.xml": "<mule>${orders.base} ${orders.host} ${secure::orders.password}</mule>\n",
    "src/main/resources/dwl/order.dwl": "%dw 2.0\n---\n{ id: payload.id } // map:MAP-001\n",
    EVIDENCE: json.dumps({"schema": "mule_validation_evidence.v1", "maven": {"exit_code": 0},
                          "munit": {"tests_run": 4, "failures": 0, "errors": 0},
                          "coverage": {"application_percent": 80}}),
}


class NamingValidationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = os.path.join(self._tmp.name, "project")
        for relative, text in FILES.items():
            self.write(relative, text)

    def write(self, relative, text):
        path = os.path.join(self.project, *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def bundle(self):
        def member(path):
            with open(os.path.join(self.project, *path.split("/")), "rb") as handle:
                return {"path": path, "sha256": hashlib.sha256(handle.read()).hexdigest()}
        both = ["DEV", "SIT"]
        return {
            "schema": "design_bundle.v1", "standards_bundle_digest": "a" * 64,
            "naming_contract_digest": CONTRACT.digest, "environments": both, "repo_name": NAME,
            "applications": [{"role": "system", "primary": True, "parts": dict(PARTS), "repository_name": NAME,
                              "deployed_names": {"DEV": NAME + "-dev", "SIT": NAME + "-sit"}}],
            "contract": member("src/main/resources/api/order.yaml"),
            "documents": {"hld": member("docs/design/hld.md"), "lld": member("docs/design/lld.md")},
            "keys": [{"key": "orders.base", "class": "invariant"},
                     {"key": "orders.host", "class": "env_specific", "environments": both},
                     {"key": "orders.password", "class": "secret", "environments": both},
                     {"key": "env", "class": "deployment"}, {"key": "secure.key", "class": "deployment"}],
            "deployment_property_keys": ["env", "secure.key"], "mappings": [{"id": "MAP-001"}],
        }

    def codes(self, bundle=None, naming=None, policy=POLICY):
        report = validate(self.project, bundle or self.bundle(), policy, naming or CONTRACT.to_staged())
        return [item.code for item in report.findings]

    def test_golden_project_passes_with_naming(self):
        report = validate(self.project, self.bundle(), POLICY, CONTRACT.to_staged())
        self.assertEqual((report.verdict, report.findings), ("pass", ()))
        self.assertEqual(report.as_dict()["naming_contract_digest"], CONTRACT.digest)

    def test_contract_binding(self):  # NAM-001
        self.assertEqual(self.codes({**self.bundle(), "naming_contract_digest": "0" * 64}), ["NAMING_CONTRACT_MISMATCH"])
        tampered = copy.deepcopy(CONTRACT.to_staged())
        tampered["environments"][0]["suffix"] = "acme"
        self.assertEqual(self.codes(naming=tampered), ["NAMING_CONTRACT_MISMATCH"])

    def test_application_names(self):  # NAM-002, NAM-003, NAM-007
        bundle = self.bundle()
        bundle["applications"][0]["repository_name"] = "acme-src-glb-order-sys-1"
        self.assertEqual(self.codes(bundle), ["NAME_UNPARSED"])
        bundle = self.bundle()
        bundle["applications"][0]["deployed_names"]["SIT"] = NAME + "-dev"
        self.assertEqual(self.codes(bundle), ["DEPLOYED_NAME_UNPARSED"])
        bundle = self.bundle()
        bundle["applications"].append({**bundle["applications"][0], "primary": False})
        self.assertEqual(self.codes(bundle), ["APPLICATION_NAME_COLLISION"])

    def test_production_environment_is_refused(self):  # NAM-004
        bundle = self.bundle()
        bundle["environments"] = ["DEV", "PROD"]
        self.assertIn("PRODUCTION_ENVIRONMENT_REFUSED", self.codes(bundle))

    def test_configuration_paths(self):  # NAM-005
        os.remove(os.path.join(self.project, *(CONFIG + "config-sit.yaml").split("/")))
        self.assertIn("CONFIGURATION_PATH_MISMATCH", self.codes())
        self.write(CONFIG + "config-sit.yaml", FILES[CONFIG + "config-sit.yaml"])
        self.write(CONFIG + "config-prod.yaml", "")
        self.assertEqual(self.codes(), ["CONFIGURATION_PATH_MISMATCH"])
        os.remove(os.path.join(self.project, *(CONFIG + "config-prod.yaml").split("/")))
        self.write("src/main/mule/global.xml", FILES["src/main/mule/global.xml"].replace("config/config.yaml", "other/config.yaml"))
        self.assertEqual(self.codes(), ["CONFIGURATION_PATH_MISMATCH"])

    def test_marks_and_secrets(self):  # NAM-006 and the secret rules
        self.write(CONFIG + "config-sit.yaml", "orders.host: ${HELIX_SET_DEV}\n")
        self.assertEqual(self.codes(), ["MARKER_POLICY_VIOLATION"])
        self.write(CONFIG + "config-sit.yaml", "orders.host: ${SET_SIT}\n")  # wrong prefix
        self.assertEqual(self.codes(), ["MARKER_POLICY_VIOLATION"])
        self.write(CONFIG + "config-sit.yaml", FILES[CONFIG + "config-sit.yaml"])
        self.write(CONFIG + "config-secure-sit.yaml", "orders.password: acme-plain-value\n")
        self.assertEqual(self.codes(), ["MARKER_POLICY_VIOLATION", "PLAINTEXT_SECRET"])

    def test_missing_evidence_is_incomplete(self):
        os.remove(os.path.join(self.project, *EVIDENCE.split("/")))
        report = validate(self.project, self.bundle(), POLICY, CONTRACT.to_staged())
        self.assertEqual((report.verdict, [item.code for item in report.findings]), ("incomplete", ["MAVEN_EVIDENCE_MISSING"]))

    def test_verify_command(self):
        inputs = {"bundle": self.bundle(), "policy": POLICY, "naming-contract": CONTRACT.to_staged()}
        argv = ["verify", "--project", self.project, "--format", "json"]
        for name, value in inputs.items():
            path = os.path.join(self._tmp.name, name + ".json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(value, handle)
            argv += ["--" + name, path]
        settings = os.path.join(self._tmp.name, "settings.xml")
        with open(settings, "w", encoding="utf-8") as handle:
            handle.write("<settings />\n")
        self.assertEqual(run_cli(*argv)[0], 2)  # --settings is required
        argv += ["--settings", settings]

        def maven(*_, **__):
            self.write("target/munit-results.xml", '<testsuite tests="4" failures="0" errors="0"/>')
            self.write("target/coverage-summary.json", '{"application_percent": 80}')
            return type("Completed", (), {"returncode": 0, "stdout": b"", "stderr": b""})()

        with patch("helix.validation.maven_runner.subprocess.run", side_effect=maven):
            code, output, _ = run_cli(*argv)
        self.assertEqual((code, json.loads(output)["verdict"]), (0, "pass"))
        # Maven cannot start: the earlier evidence must not be reused.
        with patch("helix.validation.maven_runner.subprocess.run", side_effect=FileNotFoundError):
            code, output, _ = run_cli(*argv)
        self.assertEqual((code, json.loads(output)["verdict"]), (1, "incomplete"))


if __name__ == "__main__":
    unittest.main()
