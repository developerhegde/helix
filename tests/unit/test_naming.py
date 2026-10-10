import unittest

from helix.naming import NamingInvalid, compile_contract


NAMING = {
    "schema_version": 1,
    "application": {
        "separator": "-",
        "repository": {"parts": ["prefix", "scope", "region", "name", "layer", "version"]},
        "deployed": {"parts": ["prefix", "scope", "region", "name", "layer", "version", "environment"]},
        "allowed": {
            "prefix": ["acme"],
            "scope": ["src", "run"],
            "region": ["glb", "euw"],
            "layer": ["exp", "prc", "sys"],
        },
        "version_pattern": "v[1-9][0-9]*",
        "name_pattern": "[a-z][a-z0-9-]{1,48}",
    },
    "environments": [
        {"key": "DEV", "suffix": "dev", "order": 10, "production": False},
        {"key": "SIT", "suffix": "sit", "order": 20, "production": False},
        {"key": "PROD", "suffix": "prod", "order": 90, "production": True},
    ],
    "configuration": {
        "directory": "src/main/resources/config",
        "base_file": "config.yaml",
        "environment_file": "config-{environment}.yaml",
        "secure_environment_file": "config-secure-{environment}.yaml",
        "test_directory": "src/test/resources/config",
        "test_file": "config-munit.yaml",
        "secure_test_file": "config-secure-munit.yaml",
    },
}


class NamingContractTest(unittest.TestCase):
    def test_renders_parses_and_scopes_environments(self):
        contract = compile_contract(NAMING)
        parts = {"prefix": "acme", "scope": "src", "region": "glb", "name": "order-sync", "layer": "prc", "version": "v1"}
        repository = contract.render_repository(parts)
        self.assertEqual(repository, "acme-src-glb-order-sync-prc-v1")
        self.assertEqual(dict(contract.parse_repository(repository)), parts)
        deployed = contract.render_deployed(parts, "DEV")
        parsed, environment = contract.parse_deployed(deployed)
        self.assertEqual((dict(parsed), environment), (parts, "DEV"))
        self.assertEqual(contract.allowed_environment_keys(), ("DEV", "SIT"))
        self.assertTrue(contract.is_production("PROD"))

    def test_configuration_paths_use_environment_suffixes(self):
        paths = compile_contract(NAMING).configuration_paths("SIT")
        self.assertEqual(paths.environment, "src/main/resources/config/config-sit.yaml")
        self.assertEqual(paths.secure_environment, "src/main/resources/config/config-secure-sit.yaml")
        self.assertEqual(paths.test, "src/test/resources/config/config-munit.yaml")

    def test_rejects_invalid_contract_and_names(self):
        invalid = {**NAMING, "environments": NAMING["environments"][:1]}
        with self.assertRaises(NamingInvalid):
            compile_contract(invalid)
        contract = compile_contract(NAMING)
        with self.assertRaises(NamingInvalid):
            contract.render_repository({"prefix": "other"})
        with self.assertRaises(NamingInvalid):
            contract.parse_deployed("acme-src-glb-order-sync-prc-v1-unknown")


if __name__ == "__main__":
    unittest.main()
