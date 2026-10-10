import hashlib
import os
import tempfile
import unittest

import yaml

from helix.standards import StandardsInvalid, load


class StandardsBundleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = os.path.join(self._tmp.name, "bundle.yaml")
        self.data = {
            "schema": "client_standards_bundle.v1",
            "client_id": "acme-a",
            "version": "1.0.0",
            "approved": {"by": "architect@example.invalid", "at": "2026-10-09T10:00:00Z"},
            "project": {"mule_runtime": "4.9.1", "java": 17},
            "logging": {"style": "json_logger_module"},
        }
        self._write(self.data)

    def _write(self, value):
        with open(self.path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(value, handle, sort_keys=False)

    def _reference(self):
        with open(self.path, "rb") as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        return {"path": "bundle.yaml", "version": "1.0.0", "sha256": digest}

    def test_loads_approved_bundle_with_matching_digest(self):
        bundle = load(self._tmp.name, "acme-a", self._reference())
        self.assertEqual((bundle.client_id, bundle.version), ("acme-a", "1.0.0"))
        self.assertEqual(bundle.data["logging"]["style"], "json_logger_module")

    def test_refuses_tampered_or_unsafe_references(self):
        reference = self._reference()
        self._write({**self.data, "project": {"mule_runtime": "4.9.2", "java": 17}})
        with self.assertRaises(StandardsInvalid):
            load(self._tmp.name, "acme-a", reference)
        with self.assertRaises(StandardsInvalid):
            load(self._tmp.name, "acme-a", {**reference, "path": "../bundle.yaml"})

    def test_refuses_bundle_without_approval_or_expected_policy(self):
        value = {**self.data, "approved": {}, "logging": {"style": "plain"}}
        self._write(value)
        with self.assertRaises(StandardsInvalid):
            load(self._tmp.name, "acme-a", self._reference())


if __name__ == "__main__":
    unittest.main()
