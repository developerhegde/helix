"""Guards: the doctor is offline and read-only (test 11); Helix is standalone and rename-safe."""

import ast
import os
import sys
import tempfile
import unittest

import yaml

from helix import product_identity as pid
from helix.profile.doctor import REQUIRED_FILES
from tests.support import make_profile, run_cli

_WATCHED = ("open", "subprocess.Popen", "os.system", "os.posix_spawn", "os.exec")
_EVENTS = None


def _audit(event, args):
    if _EVENTS is not None and (event.startswith("socket.") or event.startswith(_WATCHED)):
        _EVENTS.append((event, args[0] if args else None))


sys.addaudithook(_audit)


class OfflineGuard(unittest.TestCase):
    def test_no_network_no_vault_no_env_import(self):
        global _EVENTS
        with tempfile.TemporaryDirectory() as tmp:
            root = make_profile(tmp, env_extra="ACME_SENTINEL_VAR=acme-sentinel\n")
            self.assertEqual(run_cli("doctor", "--profile", root)[0], 0)  # warm imports
            _EVENTS = []
            try:
                code, _, _ = run_cli("doctor", "--profile", root, "--format", "json")
            finally:
                events, _EVENTS = _EVENTS, None
            self.assertEqual(code, 0)
            self.assertEqual([e for e in events if e[0] != "open"], [])  # no socket, no subprocess
            opened = {os.path.realpath(p) for e, p in events if isinstance(p, str)}
            allowed = {os.path.realpath(os.path.join(root, n)) for n in REQUIRED_FILES}
            with open(os.path.join(root, pid.PROFILE_FILENAME)) as handle:
                reference = yaml.safe_load(handle)["standards"]
            allowed.add(os.path.realpath(os.path.join(root, reference["path"])))
            self.assertEqual(opened, allowed)  # exactly the approved profile inputs: no vault store or other file
            self.assertNotIn("ACME_SENTINEL_VAR", os.environ)


class ProductNameGuard(unittest.TestCase):
    def test_no_product_literal_outside_identity_manifest(self):
        offenders = []
        for path in _sources():
            if path != os.path.abspath(pid.__file__):
                with open(path) as handle:
                    tree = ast.parse(handle.read())
                docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                              if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                              and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                            and id(node) not in docstrings and pid.CANONICAL_ID in node.value.lower()):
                        offenders.append(f"{path}:{node.lineno}")
        self.assertEqual(offenders, [])


class StandaloneGuard(unittest.TestCase):
    def test_no_meridian_reference_in_source_or_packaging(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(pid.__file__))))
        offenders = []
        for path in _sources() + [os.path.join(root, "pyproject.toml")]:
            with open(path) as handle:
                if "meridian" in handle.read().lower():
                    offenders.append(path)
        self.assertEqual(offenders, [])


def _sources():
    package = os.path.dirname(os.path.abspath(pid.__file__))
    return sorted(os.path.join(folder, name) for folder, _, files in os.walk(package)
                  for name in files if name.endswith(".py"))


if __name__ == "__main__":
    unittest.main()
