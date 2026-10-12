import hashlib
import os
import shutil
import tempfile
import unittest

from helix.validation import validate
from helix.validation.report_parser import parse
from tests.unit.test_validation import POLICY


FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "acme-order-sapi")


class GoldenProjectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = os.path.join(self._tmp.name, "acme-order-sapi")
        shutil.copytree(FIXTURE, self.project)

    def _digest(self, relative):
        with open(os.path.join(self.project, *relative.split("/")), "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

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

    def test_checked_in_golden_project_passes(self):
        report = validate(self.project, self._bundle(), POLICY)
        self.assertEqual(report.verdict, "pass")
        self.assertEqual(report.maven_evidence, {"maven_exit_code": 0, "tests_run": 4,
                                                 "failures": 0, "errors": 0, "coverage_percent": 80.0})

    def test_fixture_reports_generate_evidence(self):
        evidence = parse(self.project, "target/maven-execution.json", munit_report="target/munit-results.xml",
                         coverage_report="target/coverage-summary.json",
                         output_path="target/helix-validation-evidence.json")
        self.assertEqual(evidence["munit"], {"tests_run": 4, "failures": 0, "errors": 0})
        self.assertEqual(validate(self.project, self._bundle(), POLICY).verdict, "pass")

    def test_fixture_mutations_prove_validator_checks(self):
        with open(os.path.join(self.project, "src", "main", "resources", "config", "config-dev.yaml"), "a", encoding="utf-8") as handle:
            handle.write("orders.extra: ${SET_SIT}\n")
        report = validate(self.project, self._bundle(), POLICY)
        self.assertIn("MARKER_POLICY_VIOLATION", [finding.code for finding in report.findings])


if __name__ == "__main__":
    unittest.main()
