"""Tests for parallax_utils.request_metrics.get_request_metrics.

Covers:
- Normal JSON string chunks
- Bytes input auto-decoded
- SSE-prefixed data lines
- Missing or malformed usage fields
- Division by zero protection
- None returns on error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parallax_utils.request_metrics import get_request_metrics


def _make_chunk(prompt_tokens=100, completion_tokens=50, total_tokens=150):
    """Build a valid usage chunk dict."""
    return {
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
    }


class TestGetRequestMetrics:
    """Tests for get_request_metrics."""

    def test_dict_input_valid(self):
        chunk = _make_chunk()
        start = 1000.0
        first_token = 1000.5
        last_token = 1002.5
        tps, ttft, inp, out = get_request_metrics(chunk, start, first_token, last_token)
        # TPS = 50 / (2.5 - 0.5) = 25.0
        assert tps == pytest.approx(25.0)
        # TTFT = (0.5) * 1000 = 500
        assert ttft == 500
        assert inp == 100
        assert out == 50

    def test_json_string_input(self):
        chunk = json.dumps(_make_chunk())
        tps, ttft, inp, out = get_request_metrics(chunk, 0.0, 0.1, 1.1)
        assert tps == pytest.approx(50.0)
        assert ttft == 100
        assert inp == 100
        assert out == 50

    def test_bytes_input(self):
        chunk = json.dumps(_make_chunk()).encode("utf-8")
        tps, ttft, inp, out = get_request_metrics(chunk, 0.0, 0.1, 1.1)
        assert tps is not None
        assert inp == 100

    def test_sse_prefixed_data(self):
        """SSE streams prefix with 'data: '."""
        inner = json.dumps(_make_chunk())
        chunk = f"data: {inner}"
        tps, ttft, inp, out = get_request_metrics(chunk, 0.0, 0.1, 1.1)
        assert tps is not None
        assert inp == 100

    def test_malformed_json_returns_none(self):
        tps, ttft, inp, out = get_request_metrics("not-json", 0.0, 0.1, 1.1)
        assert tps is None
        assert ttft is None
        assert inp is None
        assert out is None

    def test_missing_usage_key_returns_none(self):
        chunk = {"no_usage": True}
        tps, ttft, inp, out = get_request_metrics(chunk, 0.0, 0.1, 1.1)
        assert tps is None

    def test_division_by_zero_returns_none(self):
        """If first_token_time == last_token_time, division by zero occurs."""
        chunk = _make_chunk()
        tps, ttft, inp, out = get_request_metrics(chunk, 0.0, 1.0, 1.0)
        assert tps is None

    def test_zero_completion_tokens(self):
        chunk = _make_chunk(completion_tokens=0)
        tps, ttft, inp, out = get_request_metrics(chunk, 0.0, 0.1, 1.1)
        assert tps == pytest.approx(0.0)

    def test_sse_with_whitespace(self):
        """SSE data with extra whitespace should still parse."""
        inner = json.dumps(_make_chunk())
        chunk = f"data:   {inner}"
        tps, ttft, inp, out = get_request_metrics(chunk, 0.0, 0.1, 1.1)
        assert tps is not None
