import json
import os
import tempfile
import unittest
from unittest.mock import patch

from helix.validation.maven_runner import MavenRunError, run


class MavenRunnerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = self._tmp.name
        self.settings = os.path.join(self.project, "settings.xml")
        self.output = os.path.join(self.project, "target", "execution.json")
        with open(self.settings, "w", encoding="utf-8") as handle:
            handle.write("<settings />\n")

    def test_writes_value_free_execution_receipt(self):
        completed = type("Completed", (), {"returncode": 0, "stdout": b"build output", "stderr": b""})()
        with patch("helix.validation.maven_runner.subprocess.run", return_value=completed) as command:
            receipt = run(self.project, self.settings, self.output)
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["command"][-2:], ["clean", "test"])
        self.assertNotIn("build output", json.dumps(receipt))
        with open(self.output, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), receipt)
        self.assertEqual(command.call_args.kwargs["cwd"], self.project)
        self.assertLessEqual(set(command.call_args.kwargs["env"]), {"HOME", "JAVA_HOME", "LANG", "PATH", "TMPDIR"})

    def test_refuses_unsafe_or_incomplete_invocation(self):
        with self.assertRaises(MavenRunError):
            run("relative", self.settings, self.output)
        with self.assertRaises(MavenRunError):
            run(self.project, self.settings, self.output, goals=("--settings",))
        with self.assertRaises(MavenRunError):
            run(self.project, self.settings, "relative.json")


if __name__ == "__main__":
    unittest.main()
