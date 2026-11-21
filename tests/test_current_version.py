"""Tests for get_current_version (issue #26).

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

OCI = "org.opencontainers.image.version"


def container(tag=None, label=None, semver=True):
    data = {"labels": {}, "image": {"tag": {}}}
    if label is not None:
        data["labels"][OCI] = label
    if tag is not None:
        data["image"]["tag"] = {"value": tag, "semver": semver}
    return data


class CurrentVersionTest(unittest.TestCase):
    def check(self, expected, **kwargs):
        self.assertEqual(helpers.get_current_version(container(**kwargs)), expected)

    def test_label_inherited_from_base_image_is_ignored(self):
        self.check("9.0.4", tag="9.0.4", label="26.04")
        self.check("v3.2.0", tag="v3.2.0", label="24.04")

    def test_label_refining_a_truncated_tag_is_used(self):
        self.check("2026.2.4", tag="2026.2", label="2026.2.4")

    def test_label_equal_to_tag_ignoring_v_prefix(self):
        self.check("3.2.0", tag="v3.2.0", label="3.2.0")
        self.check("v3.2.0", tag="3.2.0", label="v3.2.0")

    def test_label_that_only_shares_digits_is_not_a_refinement(self):
        self.check("9.0", tag="9.0", label="9.01")

    def test_tag_without_a_version_falls_back_to_the_label(self):
        self.check("1.4.2", tag="latest", label="1.4.2", semver=False)

    def test_no_label_uses_the_tag(self):
        self.check("9.0.4", tag="9.0.4")

    def test_no_tag_uses_the_label(self):
        self.check("1.4.2", label="1.4.2")

    def test_nothing_known(self):
        self.check("unknown")
        self.assertEqual(helpers.get_current_version({}), "unknown")
        self.assertEqual(
            helpers.get_current_version({"labels": None, "image": None}), "unknown"
        )

    def test_prerelease_and_build_separators(self):
        self.check("1.2.3-rc1", tag="1.2.3", label="1.2.3-rc1")
        self.check("1.2.3+build5", tag="1.2.3", label="1.2.3+build5")


if __name__ == "__main__":
    unittest.main()
