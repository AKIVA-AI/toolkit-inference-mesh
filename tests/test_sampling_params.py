"""Tests for parallax.server.sampling.sampling_params.SamplingParams.

Covers:
- Default initialization values
- Temperature=0 greedy sampling special case
- Stop token IDs conversion to set
- Verify method: valid and invalid ranges for all parameters
- Edge cases: boundary values
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parallax.server.sampling.sampling_params import SamplingParams

# ============================================================================
# Initialization Tests
# ============================================================================


class TestSamplingParamsInit:
    """Tests for SamplingParams initialization."""

    def test_default_values(self):
        sp = SamplingParams()
        assert sp.max_new_tokens == 128
        assert sp.min_new_tokens == 0
        assert sp.temperature == 1.0
        assert sp.top_p == 1.0
        assert sp.min_p == 0.0
        assert sp.top_k == -1
        assert sp.stop_token_ids is None
        assert sp.ignore_eos is False
        assert sp.stop_strs is None
        assert sp.repetition_penalty == 1.0
        assert sp.presence_penalty == 0.0
        assert sp.frequency_penalty == 0.0
        assert sp.json_schema is None

    def test_custom_values(self):
        sp = SamplingParams(
            max_new_tokens=256,
            min_new_tokens=10,
            temperature=0.7,
            top_p=0.9,
            min_p=0.05,
            top_k=50,
            stop_token_ids=[0, 1, 2],
            ignore_eos=True,
            stop_strs=["<end>"],
            repetition_penalty=1.2,
            presence_penalty=0.5,
            frequency_penalty=-0.5,
            json_schema='{"type": "string"}',
        )
        assert sp.max_new_tokens == 256
        assert sp.temperature == 0.7
        assert sp.stop_token_ids == {0, 1, 2}
        assert sp.stop_strs == ["<end>"]
        assert sp.json_schema == '{"type": "string"}'

    def test_temperature_zero_greedy(self):
        """Temperature=0 triggers greedy sampling (temp=1.0, top_k=1)."""
        sp = SamplingParams(temperature=0.0)
        assert sp.temperature == 1.0
        assert sp.top_k == 1

    def test_stop_token_ids_converted_to_set(self):
        sp = SamplingParams(stop_token_ids=[1, 2, 3])
        assert isinstance(sp.stop_token_ids, set)
        assert sp.stop_token_ids == {1, 2, 3}

    def test_stop_token_ids_none(self):
        sp = SamplingParams(stop_token_ids=None)
        assert sp.stop_token_ids is None

    def test_stop_token_ids_empty_list_is_none(self):
        sp = SamplingParams(stop_token_ids=[])
        # Empty list is falsy, so stop_token_ids stays None
        assert sp.stop_token_ids is None

    def test_stop_strs_string_type(self):
        sp = SamplingParams(stop_strs="stop")
        assert sp.stop_strs == "stop"

    def test_stop_strs_list_type(self):
        sp = SamplingParams(stop_strs=["stop1", "stop2"])
        assert sp.stop_strs == ["stop1", "stop2"]


# ============================================================================
# Verify Tests
# ============================================================================


class TestSamplingParamsVerify:
    """Tests for the verify() validation method."""

    def test_verify_valid_defaults_with_min_p_set(self):
        """Default min_p=0.0 is outside verify range (0, 1]; set to valid value."""
        sp = SamplingParams(min_p=0.5)
        sp.verify()  # Should not raise

    def test_verify_valid_custom(self):
        sp = SamplingParams(
            temperature=0.5,
            top_p=0.9,
            min_p=0.1,
            frequency_penalty=1.0,
            presence_penalty=1.0,
            repetition_penalty=1.5,
        )
        sp.verify()  # Should not raise

    def test_verify_default_min_p_fails(self):
        """Default min_p=0.0 is invalid for verify()."""
        sp = SamplingParams()
        with pytest.raises(ValueError, match="min_p must be in"):
            sp.verify()

    def test_verify_negative_temperature(self):
        sp = SamplingParams(temperature=-0.1, min_p=0.5)
        with pytest.raises(ValueError, match="temperature must be non-negetive"):
            sp.verify()

    def test_verify_top_p_zero(self):
        sp = SamplingParams(top_p=0.0, min_p=0.5)
        with pytest.raises(ValueError, match="top_p must be in"):
            sp.verify()

    def test_verify_top_p_above_one(self):
        sp = SamplingParams(top_p=1.5, min_p=0.5)
        with pytest.raises(ValueError, match="top_p must be in"):
            sp.verify()

    def test_verify_min_p_zero(self):
        sp = SamplingParams()
        sp.min_p = 0.0
        with pytest.raises(ValueError, match="min_p must be in"):
            sp.verify()

    def test_verify_min_p_above_one(self):
        sp = SamplingParams()
        sp.min_p = 1.5
        with pytest.raises(ValueError, match="min_p must be in"):
            sp.verify()

    def test_verify_frequency_penalty_too_low(self):
        sp = SamplingParams(frequency_penalty=-2.5, min_p=0.5)
        with pytest.raises(ValueError, match="frequency_penalty must be in"):
            sp.verify()

    def test_verify_frequency_penalty_too_high(self):
        sp = SamplingParams(frequency_penalty=2.5, min_p=0.5)
        with pytest.raises(ValueError, match="frequency_penalty must be in"):
            sp.verify()

    def test_verify_presence_penalty_too_low(self):
        sp = SamplingParams(presence_penalty=-2.5, min_p=0.5)
        with pytest.raises(ValueError, match="presence_penalty must be in"):
            sp.verify()

    def test_verify_presence_penalty_too_high(self):
        sp = SamplingParams(presence_penalty=2.5, min_p=0.5)
        with pytest.raises(ValueError, match="presence_penalty must be in"):
            sp.verify()

    def test_verify_repetition_penalty_negative(self):
        sp = SamplingParams(repetition_penalty=-0.1, min_p=0.5)
        with pytest.raises(ValueError, match="repetition_penalty must be in"):
            sp.verify()

    def test_verify_repetition_penalty_too_high(self):
        sp = SamplingParams(repetition_penalty=2.5, min_p=0.5)
        with pytest.raises(ValueError, match="repetition_penalty must be in"):
            sp.verify()

    def test_verify_boundary_values_valid(self):
        """Boundary values at limits should pass verification."""
        sp = SamplingParams(
            temperature=0.0,  # becomes greedy (1.0)
            top_p=1.0,
            min_p=0.5,
            frequency_penalty=-2.0,
            presence_penalty=2.0,
            repetition_penalty=0.0,
        )
        sp.verify()
