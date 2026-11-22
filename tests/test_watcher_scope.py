"""Tests for watcher-aware entity names (issue #28).

Dependency-free: loads helpers.py by path, so Home Assistant is not needed.
Run from the repository root:  python -m unittest discover -s tests
"""

import importlib.util
import pathlib
import unittest

_HELPERS = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "wud_monitor"
    / "helpers.py"
)
_spec = importlib.util.spec_from_file_location("wud_helpers", _HELPERS)
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)


class WatcherScopeTest(unittest.TestCase):
    def test_default_watchers_have_no_scope(self):
        for watcher in ("local", "docker"):
            self.assertIsNone(helpers.watcher_scope({"watcher": watcher}))

    def test_missing_or_empty_watcher_is_default(self):
        self.assertIsNone(helpers.watcher_scope({}))
        self.assertIsNone(helpers.watcher_scope({"watcher": None}))
        self.assertIsNone(helpers.watcher_scope({"watcher": ""}))

    def test_custom_watcher_is_the_scope(self):
        self.assertEqual(helpers.watcher_scope({"watcher": "minecraft"}), "minecraft")

    def test_scoped_name_leaves_default_watchers_unchanged(self):
        self.assertEqual(helpers.scoped_name("Glances", {"watcher": "local"}), "Glances")
        self.assertEqual(helpers.scoped_name("Glances", {}), "Glances")

    def test_scoped_name_adds_custom_watcher(self):
        self.assertEqual(
            helpers.scoped_name("Glances", {"watcher": "minecraft"}),
            "Glances (minecraft)",
        )

    def test_same_container_on_two_watchers_gets_distinct_names(self):
        a = helpers.scoped_name("glances", {"watcher": "local"})
        b = helpers.scoped_name("glances", {"watcher": "minecraft"})
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
