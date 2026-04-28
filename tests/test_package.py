"""Tests for package-level metadata."""

from importlib.metadata import version

import flop7


def test_package_version_comes_from_distribution_metadata():
    assert flop7.__version__ == version("flop7")
