"""Tests for TUI card-art build helpers."""

import pytest

from flop7.tui.components.build import ART_HEIGHT, parse_entries, wrap_in_border


def test_parse_entries_reads_comment_named_art_blocks(tmp_path):
    source = tmp_path / "numbers.txt"
    source.write_text("# A\none\ntwo\n# B\nthree\n", encoding="utf-8")

    assert parse_entries(source) == [
        ("A", ["one", "two"]),
        ("B", ["three"]),
    ]


def test_wrap_in_border_centers_valid_art():
    art = wrap_in_border("X", ["X"] * ART_HEIGHT)
    lines = art.splitlines()

    assert lines[0].startswith("╔")
    assert lines[-1].startswith("╚")
    assert len(lines) == 12


def test_wrap_in_border_rejects_wrong_height():
    with pytest.raises(ValueError, match="expected"):
        wrap_in_border("Bad", ["x"])


def test_wrap_in_border_rejects_too_wide_art():
    with pytest.raises(ValueError, match="exceeds"):
        wrap_in_border("Bad", ["x" * 16] * ART_HEIGHT)
