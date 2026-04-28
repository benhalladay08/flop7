"""Tests for the CLI entry point."""

import pytest

from flop7 import __version__
from flop7.cli import main


def test_version_flag_prints_package_version(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["flop7", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"flop7 {__version__}"
