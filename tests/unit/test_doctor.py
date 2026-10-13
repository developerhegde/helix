import hashlib
import json
import os
import tempfile
import unittest
from datetime import timedelta

import yaml

from helix import product_identity as pid
from helix.profile.doctor import run_doctor
from helix.profile.loader import ProfileInvalid, load_profile
from helix.profile.policy import DEFAULT_POLICY, ProviderPolicy
from tests.support import NOW, make_profile, run_cli

FAKE_SECRET = "sk-ant-acmeFAKE0123456789abcdefFAKE"


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def profile(self, mutate=None, env_extra=""):
        tmp = tempfile.mkdtemp(dir=self._tmp.name)
        return make_profile(tmp, mutate, env_extra)

    def ids(self, root, **kw):
        return [f.id for f in run_doctor(root, now=NOW, **kw).findings]

    def paths(self, root, rule):
        return [f.path for f in run_doctor(root, now=NOW).findings if f.id == rule]

    # 1
    def test_complete_profile_is_healthy(self):
        root = self.profile()
        code, out, _ = run_cli("doctor", "--profile", root, "--format", "json")
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual((result["status"], result["findings"], result["client_id"]), ("healthy", [], "acme-a"))
        self.assertEqual(load_profile(root, now=NOW).client_id, "acme-a")

    # 2
    def test_missing_profile_file(self):
        root = self.profile()
        os.remove(os.path.join(root, pid.PROFILE_FILENAME))
        self.assertEqual([(f.id, f.path) for f in run_doctor(root, now=NOW).findings],
                         [("B1-001", pid.PROFILE_FILENAME)])
        self.assertEqual(run_cli("doctor", "--profile", root)[0], 1)

    # 3
    def test_each_section_omitted(self):
        expected = {"schema_version": "B1-002", "client_id": "B1-003", "model_route": "B1-004",
                    "data_handling": "B1-005", "jira": "B1-007", "github": "B1-008", "vault": "B1-009",
                    "anypoint": "B1-010", "design": "B1-013", "gates": "B1-013", "naming": "B1-015", "standards": "B1-016"}
        for section, rule in expected.items():
            with self.subTest(section):
                root = self.profile(lambda d: d.pop(section))
                self.assertEqual(set(self.ids(root)), {rule})
                with self.assertRaises(ProfileInvalid):
                    load_profile(root, now=NOW)

    # 4
    def test_production_like_environments(self):
        for env in ("prod", "PROD", "Production", "acme-prod", "acme-PRD"):
            with self.subTest(env):
                root = self.profile(lambda d: d["anypoint"]["environments"].append(env))
                self.assertEqual(self.paths(root, "B1-011"), ["anypoint.environments[2]"])
        self.assertEqual(self.ids(self.profile(lambda d: d["anypoint"]["environments"].append("acme-product"))), [])

    # 5 and --strict
    def test_expiry(self):
        def at(delta):
            return self.profile(lambda d: d["anypoint"].update(secret_expiry=(NOW + delta).isoformat()))

        expired = run_doctor(at(timedelta(days=-1)), now=NOW).findings
        self.assertEqual([(f.id, f.severity) for f in expired], [("B1-012", "error")])
        soon = at(timedelta(days=10))
        self.assertEqual([(f.id, f.severity) for f in run_doctor(soon, now=NOW).findings], [("B1-012", "warning")])
        self.assertEqual(run_cli("doctor", "--profile", soon)[0], 0)
        self.assertEqual(run_cli("doctor", "--profile", soon, "--strict")[0], 1)
        self.assertEqual(self.ids(at(timedelta(days=31))), [])
        self.assertEqual(self.paths(self.profile(lambda d: d["anypoint"].update(secret_expiry="soon")), "B1-010"),
                         ["anypoint.secret_expiry"])

    # 6
    def test_forbidden_route_and_residency(self):
        region = self.profile(lambda d: d["model_route"].update(region="us-east-1"))
        self.assertIn("model_route.region", self.paths(region, "B1-005"))
        model = self.profile(lambda d: d["model_route"]["phases"].update(design="claude-fable-5-1"))
        self.assertEqual(self.paths(model, "B1-005"), ["model_route.phases.design"])
        no_zdr = DEFAULT_POLICY.__class__(**{**DEFAULT_POLICY.__dict__, "providers": {
            **DEFAULT_POLICY.providers, "anthropic": ProviderPolicy(False, ("api.anthropic.com",))}})
        self.assertEqual(self.ids(self.profile(), policy=no_zdr), ["B1-005"])
        host = self.profile(lambda d: d["data_handling"]["allowed_hosts"].extend(["acme.example.invalid", "http://x"]))
        self.assertEqual(self.paths(host, "B1-006"), ["data_handling.allowed_hosts[1]", "data_handling.allowed_hosts[2]"])

    # 7
    def test_plaintext_secret_is_never_echoed(self):
        root = self.profile(lambda d: d["jira"].update(api_token="acme-plain-value", cloud_id=FAKE_SECRET))
        self.assertEqual(self.paths(root, "B1-014"), ["jira.cloud_id", "jira.api_token"])
        for fmt in ("text", "json"):
            code, out, err = run_cli("doctor", "--profile", root, "--format", fmt)
            self.assertEqual(code, 1)
            self.assertNotIn(FAKE_SECRET, out + err)
            self.assertNotIn("acmeFAKE", out + err)

    # 8
    def test_allowed_bots_missing_either_identity(self):
        for bot in ("acme-jira-bot", "acme-github-bot"):
            with self.subTest(bot):
                root = self.profile(lambda d: d["github"]["allowed_bots"].remove(bot))
                self.assertEqual(self.paths(root, "B1-008"), ["github.allowed_bots"])

    def test_invalid_naming_contract(self):
        root = self.profile(lambda d: d["naming"]["environments"].pop(1))
        self.assertEqual(self.paths(root, "B1-015"), ["naming"])
        with self.assertRaises(ProfileInvalid):
            load_profile(root, now=NOW)

    def test_standards_bundle_must_match_approved_reference(self):
        root = self.profile(lambda d: d["standards"].update(sha256="0" * 64))
        self.assertEqual(self.paths(root, "B1-016"), ["standards"])
        with self.assertRaises(ProfileInvalid):
            load_profile(root, now=NOW)

    # 9
    def test_invalid_caps(self):
        cases = {"run_cap_usd": 0, "phase_cap_usd": -1}
        for key, value in cases.items():
            with self.subTest(key):
                root = self.profile(lambda d: d["model_route"].update({key: value}))
                self.assertEqual(self.paths(root, "B1-004"), [f"model_route.{key}"])
        root = self.profile(lambda d: d["model_route"].update(run_cap_usd="ten", phase_cap_usd=True))
        self.assertEqual(self.paths(root, "B1-004"), ["model_route.run_cap_usd", "model_route.phase_cap_usd"])
        root = self.profile(lambda d: d["model_route"].update(phase_cap_usd=171))
        self.assertEqual(self.paths(root, "B1-004"), ["model_route.phase_cap_usd"])

    # 10
    def test_output_contract_and_exit_codes(self):
        healthy = self.profile()
        text = run_cli("doctor", "--profile", healthy)[1]
        self.assertEqual(text, run_cli("doctor", "--profile", healthy)[1])
        self.assertTrue(text.startswith(f"{pid.CANONICAL_ID} doctor: client acme-a, policy 1, status healthy\n"))

        broken = self.profile(lambda d: d["model_route"].update(phase_cap_usd=500))
        code, out, _ = run_cli("doctor", "--profile", broken, "--format", "json")
        result = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(list(result), ["schema_version", "client_id", "policy_version", "status",
                                        "findings", "deferred_checks"])
        self.assertEqual(list(result["findings"][0]), ["id", "severity", "path", "message", "remediation"])
        self.assertEqual((result["schema_version"], result["policy_version"], result["status"]), (1, "1", "error"))

        for argv in (("doctor",), ("doctor", "--profile", "relative/acme-a"),
                     ("doctor", "--profile", os.path.join(self._tmp.name, "absent")),
                     ("doctor", "--profile", healthy, "--format", "xml"), ()):
            with self.subTest(argv):
                self.assertEqual(run_cli(*argv)[0], 2)

        os.environ[pid.PROFILE_ENV_VAR] = healthy
        self.addCleanup(os.environ.pop, pid.PROFILE_ENV_VAR, None)
        self.assertEqual(run_cli("doctor")[0], 0)

    def test_directory_name_and_unknown_keys(self):
        root = self.profile(lambda d: d.update(acme_extra=1))
        findings = run_doctor(root, now=NOW).findings
        self.assertEqual([(f.id, f.severity, f.path) for f in findings], [("B1-018", "warning", "acme_extra")])
        self.assertEqual(run_cli("doctor", "--profile", root)[0], 0)
        self.assertEqual(run_cli("doctor", "--profile", root, "--strict")[0], 1)
        renamed = os.path.join(os.path.dirname(self.profile()), "acme-other")
        os.rename(os.path.join(os.path.dirname(renamed), "acme-a"), renamed)
        self.assertEqual(self.ids(renamed), ["B1-017"])

    def rebundle(self, change, files=()):
        """A profile whose standards bundle was changed and re-pinned by its new digest."""
        root = self.profile()
        standards = os.path.join(root, "standards")
        for name, text in files:
            with open(os.path.join(standards, name), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        with open(os.path.join(standards, "bundle.yaml"), encoding="utf-8") as handle:
            bundle = yaml.safe_load(handle)
        change(bundle)
        raw = yaml.safe_dump(bundle, sort_keys=False).encode("utf-8")
        with open(os.path.join(standards, "bundle.yaml"), "wb") as handle:
            handle.write(raw)
        path = os.path.join(root, pid.PROFILE_FILENAME)
        with open(path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        doc["standards"]["sha256"] = hashlib.sha256(raw).hexdigest()
        with open(path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(doc, handle, sort_keys=False)
        return root

    def test_references_stay_inside_the_vault_scope(self):
        for reference in ("vault://acme-b/profile/jira-webhook", "vault://acme-a/profile/../acme-b/jira-webhook",
                          "vault://acme-a/profile"):
            with self.subTest(reference):
                root = self.profile(lambda d: d["jira"].update(webhook_secret_ref=reference))
                self.assertEqual(self.paths(root, "B1-009"), ["jira.webhook_secret_ref"])

    def test_profile_agrees_with_the_standards_bundle(self):
        self.assertEqual(self.paths(self.profile(lambda d: d["design"].update(logging="acme-text-logger")), "B1-019"),
                         ["design.logging"])
        root = self.rebundle(lambda b: b.update(api={"default_contract": "raml10"},
                                                configuration={"layout": "deployment_properties"}))
        self.assertEqual(self.paths(root, "B1-019"), ["design.contract_format", "naming.configuration.layout"])
        self.assertEqual(self.ids(self.rebundle(lambda b: b.update(api={"default_contract": "oas30"}))), [])

    def test_platform_names_follow_the_anypoint_allow_list(self):
        unknown = self.profile(lambda d: d["naming"]["environments"][0].update(platform_name="acme-unlisted"))
        self.assertEqual(self.paths(unknown, "B1-020"), ["naming.environments[0].platform_name"])
        production = self.profile(lambda d: d["naming"]["environments"][2].update(platform_name="acme-sandbox"))
        self.assertEqual(self.paths(production, "B1-020"), ["naming.environments[2].platform_name"])

    def test_bundle_lists_other_client_files_by_digest(self):
        text = "acme-denied-token\n"
        entry = {"path": "denylist.txt", "purpose": "denylist", "sha256": hashlib.sha256(text.encode()).hexdigest()}
        listed = (("denylist.txt", text),)
        self.assertEqual(self.ids(self.rebundle(lambda b: b.update(files=[entry]), listed)), [])
        for bad in ({**entry, "sha256": "0" * 64}, {**entry, "path": "../" + pid.PROFILE_FILENAME},
                    {**entry, "purpose": "acme-other"}, {**entry, "path": "absent.txt"}):
            with self.subTest(bad):
                self.assertEqual(self.ids(self.rebundle(lambda b: b.update(files=[bad]), listed)), ["B1-016"])

    def test_every_independent_defect_in_one_run(self):
        def breakage(d):
            d["client_id"] = "Acme_A"
            d["model_route"]["phase_cap_usd"] = 999
            d["data_handling"]["allowed_hosts"] = []
            d["jira"]["project_key"] = "acme"
            d["github"]["repositories"] = []
            d["vault"]["scope"] = FAKE_SECRET
            d["anypoint"]["environments"].append("prod")
            d["anypoint"]["secret_expiry"] = "2020-01-01T00:00:00Z"
            d["gates"]["merge"] = []

        ids = self.ids(self.profile(breakage))
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(set(ids), {"B1-003", "B1-004", "B1-006", "B1-007", "B1-008", "B1-009",
                                    "B1-011", "B1-012", "B1-013", "B1-014"})


if __name__ == "__main__":
    unittest.main()
