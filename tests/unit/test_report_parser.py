import json
import os
import tempfile
import unittest

from helix.validation.report_parser import ReportParseError, parse


class ReportParserTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = self._tmp.name
        self._write("target/receipt.json", json.dumps({"schema": "mule_execution_receipt.v1", "exit_code": 0}))
        self._write("target/munit.xml", '<testsuite tests="3" failures="1" errors="0" />')
        self._write("target/coverage.json", json.dumps({"application_percent": 82.5}))

    def _write(self, relative, text):
        path = os.path.join(self.project, *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_parses_allowlisted_reports_into_value_free_evidence(self):
        evidence = parse(self.project, "target/receipt.json", munit_report="target/munit.xml",
                         coverage_report="target/coverage.json", output_path="target/evidence.json")
        self.assertEqual(evidence, {"schema": "mule_validation_evidence.v1", "maven": {"exit_code": 0},
                                    "munit": {"tests_run": 3, "failures": 1, "errors": 0},
                                    "coverage": {"application_percent": 82.5}})
        with open(os.path.join(self.project, "target", "evidence.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), evidence)

    def test_rejects_escape_missing_and_malformed_reports(self):
        with self.assertRaises(ReportParseError):
            parse(self.project, "../receipt.json", munit_report="target/munit.xml",
                  coverage_report="target/coverage.json", output_path="target/evidence.json")
        self._write("target/munit.xml", '<testsuite tests="many" failures="0" errors="0" />')
        with self.assertRaises(ReportParseError):
            parse(self.project, "target/receipt.json", munit_report="target/munit.xml",
                  coverage_report="target/coverage.json", output_path="target/evidence.json")


if __name__ == "__main__":
    unittest.main()
