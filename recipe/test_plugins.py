"""Regression checks for the SAC plugin loader on supported Python versions."""

import os
from pathlib import Path
import sys
import tempfile
import unittest

from pisces.commands.sac2db import get_plugins


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.previous_directory = Path.cwd()
        self.directory = tempfile.TemporaryDirectory()
        os.chdir(self.directory.name)
        Path("plugins").mkdir()

    def tearDown(self):
        for name in list(sys.modules):
            if name.startswith("_pisces_test_plugin"):
                sys.modules.pop(name, None)
        os.chdir(self.previous_directory)
        self.directory.cleanup()

    def test_no_plugins(self):
        self.assertEqual(get_plugins(None), [])
        self.assertEqual(get_plugins([]), [])

    def test_load_functions_in_order(self):
        Path("plugins/_pisces_test_plugin.py").write_text(
            "def first():\n    return 1\n"
            "def second():\n    return 2\n"
        )
        functions = get_plugins([
            "plugins/_pisces_test_plugin:second",
            "plugins/_pisces_test_plugin:first",
        ])
        self.assertEqual([function() for function in functions], [2, 1])

    def test_package_with_relative_import(self):
        package = Path("plugins/_pisces_test_plugin_package")
        package.mkdir()
        (package / "__init__.py").write_text("from .implementation import plugin\n")
        (package / "implementation.py").write_text(
            "def plugin():\n    return 42\n"
        )
        function, = get_plugins(["plugins/_pisces_test_plugin_package:plugin"])
        self.assertEqual(function(), 42)

    def test_invalid_specification(self):
        with self.assertRaisesRegex(ValueError, "Must specify plugin"):
            get_plugins(["invalid"])

    def test_missing_module(self):
        with self.assertRaises(ImportError):
            get_plugins(["plugins/_pisces_test_plugin_missing:plugin"])

    def test_missing_function(self):
        Path("plugins/_pisces_test_plugin.py").write_text("value = 1\n")
        with self.assertRaises(AttributeError):
            get_plugins(["plugins/_pisces_test_plugin:missing"])

    def test_failed_import_cleans_module_cache(self):
        Path("plugins/_pisces_test_plugin_broken.py").write_text(
            "raise RuntimeError('plugin failed')\n"
        )
        with self.assertRaisesRegex(RuntimeError, "plugin failed"):
            get_plugins(["plugins/_pisces_test_plugin_broken:plugin"])
        self.assertNotIn("_pisces_test_plugin_broken", sys.modules)


if __name__ == "__main__":
    unittest.main()
