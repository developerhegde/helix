"""`helix stage` and the policy compiled from a standards bundle."""

import hashlib
import json
import os
import tempfile
import unittest

from helix.naming import load_contract
from helix.validation import contracts
from helix.validation.policy_compiler import PolicyCompileError, compile_policy
from tests.support import make_profile, run_cli
from tests.unit.test_naming_validation import CONTRACT
from tests.unit import test_standards_checks as checks  # the module, so its test class is not collected twice

CASES, POLICY = checks.CASES, checks.POLICY

STANDARDS = {
    "project": {"mule_runtime": "4.9.1", "java": 17, "group_id": "acme-org-id", "require_mule_artifact": True,
                "golden_parent": {"group_id": "example", "artifact_id": "helix-parent", "version": "1.0.0"},
                "allowed_plugins": ["org.mule.tools.maven:mule-maven-plugin"], "forbidden_paths": [".github/**"],
                "child_pom": dict.fromkeys(POLICY["maven"]["child_pom"], True)},
    "connectors": {"allowed": ["org.mule.connectors:mule-http-connector"]},
    "patterns": POLICY["patterns"],
    "api": {"apikit": "required"},
    "error_handling": {"handler_file": "error-handler.xml", "forbid_continue_on_any": True},
    "logging": {"style": "json_logger_module", "forbid_free_text_logger": True, "log_event_subflow": "log-event-subflow"},
    "testing": {"forbid_sleep": True, "ignored_needs_ticket": "[A-Z][A-Z0-9]+-[0-9]+", "suite_per_implementation": "-impl.xml"},
}


class StageTest(unittest.TestCase):
    def test_compiled_policy_switches_on_the_standards_checks(self):
        policy = compile_policy(STANDARDS, "a" * 64, CONTRACT)
        self.assertEqual(contracts.check_policy(policy), [])
        self.assertEqual(policy["testing"]["minimum_application_coverage"], 75)  # the default when the bundle is silent
        self.assertEqual(policy["configuration"]["marker_prefix"], "HELIX")
        project = checks.StandardsChecksTest("test_project_that_follows_the_standards_passes")
        self.assertEqual(project.codes(policy=policy), [])
        for code, path, old, new in CASES:
            if path.endswith(".dwl"):
                continue
            with self.subTest(code=code, change=new):
                self.assertIn(code, project.codes([(path, old, new)], policy=policy))

    def test_bundle_without_a_parent_pom_is_refused(self):
        with self.assertRaises(PolicyCompileError):
            compile_policy({"project": {"mule_runtime": "4.9.1"}}, "a" * 64, CONTRACT)

    def test_stage_writes_the_three_inputs_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, out = make_profile(tmp), os.path.join(tmp, "in", "validation")
            code, text, _ = run_cli("stage", "--profile", root, "--out-dir", out)
            self.assertEqual(code, 0)
            with open(os.path.join(out, "validation-policy.json"), encoding="utf-8") as handle:
                policy = json.load(handle)
            with open(os.path.join(out, "naming-contract.json"), encoding="utf-8") as handle:
                contract = load_contract(json.load(handle))
            with open(os.path.join(out, "standards-bundle.yaml"), "rb") as handle:
                standards_digest = hashlib.sha256(handle.read()).hexdigest()
            self.assertEqual(contracts.check_policy(policy), [])
            self.assertEqual((policy["standards_bundle_digest"], contract.digest), (standards_digest, CONTRACT.digest))
            self.assertIn(standards_digest[:12], text)
            self.assertEqual(run_cli("stage", "--profile", root, "--out-dir", out)[0], 2)  # never overwritten
            broken = make_profile(os.path.join(tmp, "broken"), lambda d: d.pop("naming"))
            self.assertEqual(run_cli("stage", "--profile", broken, "--out-dir", os.path.join(tmp, "other"))[0], 1)


if __name__ == "__main__":
    unittest.main()
