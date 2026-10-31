"""Exercise configuration bootstrap in fresh processes without a database."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class SettingsEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.project = self.root / "project"
        self.config = self.project / "backend" / "config"
        self.config.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / "config" / "settings.py"
        self.settings = self.config / "settings.py"
        self.settings.write_text(source.read_text())
        self.key = "isolated-configuration-test-value"

    def run_settings(self, dotenv=None, environment=None):
        if dotenv is not None:
            (self.project / ".env").write_text(dotenv)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("DJANGO_", "ONBOARDING_", "POSTGRES_"))}
        env.update(environment or {})
        script = (
            "import json, runpy, sys; settings = runpy.run_path(sys.argv[1]); "
            "print(json.dumps({'debug': settings['DEBUG'], "
            "'configured_key_used': settings['SECRET_KEY'] == sys.argv[2]}))"
        )
        return subprocess.run(
            [sys.executable, "-c", script, str(self.settings), self.key],
            env=env, cwd=self.root, capture_output=True, text=True, check=False,
        )

    def assert_settings(self, result, *, debug, configured_key_used):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "debug": debug, "configured_key_used": configured_key_used,
        })

    def test_project_dotenv_loads_outside_project_directory(self):
        result = self.run_settings(f"DJANGO_DEBUG=True\nDJANGO_SECRET_KEY={self.key}\n")
        self.assert_settings(result, debug=True, configured_key_used=True)

    def test_shell_values_override_dotenv_including_false_debug(self):
        result = self.run_settings("DJANGO_DEBUG=True\nDJANGO_SECRET_KEY=file-value\n", {
            "DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": self.key,
        })
        self.assert_settings(result, debug=False, configured_key_used=True)

    def test_shell_false_debug_does_not_allow_missing_key(self):
        result = self.run_settings("DJANGO_DEBUG=True\n", {"DJANGO_DEBUG": "False"})
        self.assert_rejected(result)

    def test_production_requires_key_without_dotenv(self):
        self.assert_rejected(self.run_settings())

    def test_production_accepts_explicit_key_without_dotenv(self):
        self.assert_settings(self.run_settings(environment={"DJANGO_SECRET_KEY": self.key}),
                             debug=False, configured_key_used=True)

    def test_legacy_example_key_is_rejected_in_production(self):
        self.assert_rejected(self.run_settings(
            "DJANGO_DEBUG=False\n"
            "DJANGO_SECRET_KEY=kanban-secret-key-super-secure-jwt-2026-production\n"))

    def test_debug_can_be_explicitly_enabled_without_dotenv(self):
        self.assert_settings(self.run_settings(environment={"DJANGO_DEBUG": "True"}),
                             debug=True, configured_key_used=False)

    def test_parent_dotenv_is_not_discovered(self):
        (self.root / ".env").write_text(f"DJANGO_DEBUG=True\nDJANGO_SECRET_KEY={self.key}\n")
        self.assert_rejected(self.run_settings())

    def test_empty_shell_key_does_not_fall_back_to_file(self):
        self.assert_rejected(self.run_settings(f"DJANGO_SECRET_KEY={self.key}\n", {
            "DJANGO_SECRET_KEY": "", "DJANGO_DEBUG": "False",
        }))

    def assert_rejected(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY must be configured", result.stderr)


if __name__ == "__main__":
    unittest.main()
