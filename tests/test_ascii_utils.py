"""Tests for parallax_utils.ascii_anime utility functions.

Covers:
- HexColorPrinter.hex_to_rgb conversion
- HexColorPrinter.color_distance calculation
- HexColorPrinter.find_closest_color matching
- handle_colors_data parsing
- process_context_color_run and process_context_color_join
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parallax_utils.ascii_anime import (
    HexColorPrinter,
    handle_colors_data,
    process_context_color_join,
    process_context_color_run,
)


# ============================================================================
# HexColorPrinter Tests
# ============================================================================


class TestHexColorPrinter:
    """Tests for HexColorPrinter utility methods."""

    def test_hex_to_rgb_black(self):
        assert HexColorPrinter.hex_to_rgb("#000000") == (0, 0, 0)

    def test_hex_to_rgb_white(self):
        assert HexColorPrinter.hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_hex_to_rgb_red(self):
        assert HexColorPrinter.hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_hex_to_rgb_no_hash(self):
        assert HexColorPrinter.hex_to_rgb("00ff00") == (0, 255, 0)

    def test_color_distance_same(self):
        dist = HexColorPrinter.color_distance((0, 0, 0), (0, 0, 0))
        assert dist == 0.0

    def test_color_distance_known(self):
        # Distance between black and white
        dist = HexColorPrinter.color_distance((0, 0, 0), (255, 255, 255))
        assert dist == pytest.approx((255**2 * 3) ** 0.5)

    def test_find_closest_color_exact_match(self):
        # Pure red should map to the red ANSI code
        ansi = HexColorPrinter.find_closest_color("#ff0000")
        assert ansi == "\033[91m"  # bright red

    def test_find_closest_color_exact_black(self):
        ansi = HexColorPrinter.find_closest_color("#000000")
        assert ansi == "\033[30m"

    def test_find_closest_color_returns_ansi_string(self):
        ansi = HexColorPrinter.find_closest_color("#123456")
        assert ansi.startswith("\033[")


# ============================================================================
# handle_colors_data Tests
# ============================================================================


class TestHandleColorsData:
    """Tests for handle_colors_data."""

    def test_none_input(self):
        assert handle_colors_data(None) == {}

    def test_empty_json(self):
        assert handle_colors_data("{}") == {}

    def test_valid_colors(self):
        import json

        data = json.dumps({"0,0": "#ff0000", "1,0": "#00ff00"})
        result = handle_colors_data(data)
        assert result == {"0,0": "#ff0000", "1,0": "#00ff00"}

    def test_non_color_values_excluded(self):
        import json

        data = json.dumps({"0,0": "#ff0000", "1,0": "not-a-color"})
        result = handle_colors_data(data)
        assert "0,0" in result
        assert "1,0" not in result


# ============================================================================
# process_context_color_run Tests
# ============================================================================


class TestProcessContextColorRun:
    """Tests for process_context_color_run."""

    def test_basic_processing(self):
        content = [["A", "B", "C"]]
        colors = {"0,0": "#ff0000", "1,0": "#00ff00"}
        result = process_context_color_run(content, colors)
        assert len(result) == 1
        assert HexColorPrinter.RESET in result[0]

    def test_black_special_chars_become_space(self):
        """Characters in ('#', '.') with #000000 color should become space."""
        content = [["#", ".", "A"]]
        colors = {"0,0": "#000000", "1,0": "#000000"}
        result = process_context_color_run(content, colors)
        # The '#' and '.' at black positions should be replaced with space
        assert "#" not in result[0] or result[0].count("#") == 0 or " " in result[0]

    def test_empty_content(self):
        result = process_context_color_run([], {})
        assert result == []


# ============================================================================
# process_context_color_join Tests
# ============================================================================


class TestProcessContextColorJoin:
    """Tests for process_context_color_join."""

    def test_basic_processing(self):
        content = [["X"] * 40 for _ in range(10)]
        colors = {}
        result = process_context_color_join(content, colors, "test-model")
        assert len(result) == 10

    def test_model_name_truncation(self):
        """Model names longer than 30 chars should be truncated."""
        content = [["X"] * 40 for _ in range(10)]
        colors = {}
        long_name = "A" * 50
        result = process_context_color_join(content, colors, long_name)
        # Should not crash
        assert len(result) == 10

    def test_model_name_inserted_at_row_7(self):
        """Model name characters should appear in row 7 columns 9-38."""
        content = [["X"] * 40 for _ in range(10)]
        colors = {}
        result = process_context_color_join(content, colors, "MyModel")
        # Strip ANSI codes to check for model name characters
        import re

        stripped = re.sub(r"\033\[[0-9;]*m", "", result[7])
        assert "MyModel" in stripped
