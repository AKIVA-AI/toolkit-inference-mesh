"""Tests for Toolkit event logging enhancements."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.server.toolkit_event_log import (
    InferenceEvent,
    append_inference_event,
    estimate_cost_usd,
    set_cost_per_1k_tokens_usd,
    set_event_log_path,
    validate_event_log_path,
)

# ============================================================================
# Path Validation Tests
# ============================================================================


def test_validate_event_log_path_success(tmp_path: Path) -> None:
    """Test path validation succeeds within allowed directory."""
    log_path = tmp_path / "logs" / "events.jsonl"

    # Change cwd to tmp_path so logs/ is within cwd
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = validate_event_log_path(log_path)
        assert result.is_absolute()
    finally:
        os.chdir(old_cwd)


def test_validate_event_log_path_home_directory() -> None:
    """Test path validation allows .akiva in home directory."""
    log_path = Path.home() / ".akiva" / "events.jsonl"
    result = validate_event_log_path(log_path)
    assert result.is_absolute()
    assert ".akiva" in str(result)


def test_validate_event_log_path_outside_allowed() -> None:
    """Test path validation rejects paths outside allowed directories."""
    # Try /etc which should be rejected
    log_path = Path("/etc/events.jsonl")
    with pytest.raises(ValueError, match="must be within allowed directories"):
        validate_event_log_path(log_path)


# ============================================================================
# Cost Validation Tests
# ============================================================================


def test_set_cost_per_1k_tokens_valid() -> None:
    """Test setting valid cost per 1K tokens."""
    set_cost_per_1k_tokens_usd(0.01)
    cost = estimate_cost_usd(tokens_in=1000, tokens_out=500)
    assert cost == 0.015  # (1500 / 1000) * 0.01


def test_set_cost_per_1k_tokens_negative() -> None:
    """Test setting negative cost raises error."""
    with pytest.raises(ValueError, match="must be non-negative"):
        set_cost_per_1k_tokens_usd(-0.01)


def test_set_cost_per_1k_tokens_invalid_type() -> None:
    """Test setting invalid type raises error."""
    with pytest.raises(ValueError, match="Invalid cost value"):
        set_cost_per_1k_tokens_usd("not a number")  # type: ignore


def test_estimate_cost_usd_zero_cost() -> None:
    """Test cost estimation with zero cost."""
    set_cost_per_1k_tokens_usd(0.0)
    cost = estimate_cost_usd(tokens_in=1000, tokens_out=1000)
    assert cost == 0.0


def test_estimate_cost_usd_none_tokens() -> None:
    """Test cost estimation with None tokens."""
    set_cost_per_1k_tokens_usd(0.01)
    cost = estimate_cost_usd(tokens_in=None, tokens_out=None)
    assert cost == 0.0


def test_estimate_cost_usd_negative_tokens_ignored() -> None:
    """Test cost estimation ignores negative tokens."""
    set_cost_per_1k_tokens_usd(0.01)
    cost = estimate_cost_usd(tokens_in=-100, tokens_out=1000)
    assert cost == 0.01  # Only 1000 tokens counted


# ============================================================================
# InferenceEvent Schema Tests
# ============================================================================


def test_inference_event_valid() -> None:
    """Test valid inference event passes validation."""
    event = InferenceEvent(
        schema_version=1,
        created_ts=1234567890.0,
        request_id="req-123",
        model="gpt-4",
        latency_ms=150.5,
        cost_usd=0.001,
        success=True,
    )
    assert event.schema_version == 1
    assert event.request_id == "req-123"
    assert event.model == "gpt-4"


def test_inference_event_missing_required_fields() -> None:
    """Test inference event requires mandatory fields."""
    with pytest.raises(ValidationError):
        InferenceEvent(
            schema_version=1,
            created_ts=1234567890.0,
            # Missing request_id
            model="gpt-4",
            latency_ms=150.5,
            cost_usd=0.001,
            success=True,
        )


def test_inference_event_invalid_schema_version() -> None:
    """Test inference event rejects invalid schema version."""
    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        InferenceEvent(
            schema_version=0,
            created_ts=1234567890.0,
            request_id="req-123",
            model="gpt-4",
            latency_ms=150.5,
            cost_usd=0.001,
            success=True,
        )


def test_inference_event_negative_latency() -> None:
    """Test inference event rejects negative latency."""
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        InferenceEvent(
            schema_version=1,
            created_ts=1234567890.0,
            request_id="req-123",
            model="gpt-4",
            latency_ms=-10.0,
            cost_usd=0.001,
            success=True,
        )


def test_inference_event_negative_cost() -> None:
    """Test inference event rejects negative cost."""
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        InferenceEvent(
            schema_version=1,
            created_ts=1234567890.0,
            request_id="req-123",
            model="gpt-4",
            latency_ms=150.5,
            cost_usd=-0.001,
            success=True,
        )


def test_inference_event_empty_request_id() -> None:
    """Test inference event rejects empty request_id."""
    with pytest.raises(ValidationError, match="at least 1 character"):
        InferenceEvent(
            schema_version=1,
            created_ts=1234567890.0,
            request_id="",
            model="gpt-4",
            latency_ms=150.5,
            cost_usd=0.001,
            success=True,
        )


def test_inference_event_empty_model() -> None:
    """Test inference event rejects empty model."""
    with pytest.raises(ValidationError, match="at least 1 character"):
        InferenceEvent(
            schema_version=1,
            created_ts=1234567890.0,
            request_id="req-123",
            model="",
            latency_ms=150.5,
            cost_usd=0.001,
            success=True,
        )


def test_inference_event_negative_tokens() -> None:
    """Test inference event rejects negative token counts."""
    with pytest.raises(ValidationError):
        InferenceEvent(
            schema_version=1,
            created_ts=1234567890.0,
            request_id="req-123",
            model="gpt-4",
            latency_ms=150.5,
            cost_usd=0.001,
            success=True,
            tokens_in=-100,
        )


def test_inference_event_with_optional_fields() -> None:
    """Test inference event with all optional fields."""
    event = InferenceEvent(
        schema_version=1,
        created_ts=1234567890.0,
        request_id="req-123",
        tenant="acme-corp",
        project="chatbot",
        tier="premium",
        provider="parallax",
        model="gpt-4",
        latency_ms=150.5,
        cost_usd=0.001,
        success=True,
        error_type="",
        tokens_in=100,
        tokens_out=50,
        meta={"user_id": "u123"},
    )
    assert event.tenant == "acme-corp"
    assert event.tokens_in == 100
    assert event.meta == {"user_id": "u123"}


# ============================================================================
# append_inference_event Tests
# ============================================================================


def test_append_inference_event_success(tmp_path: Path) -> None:
    """Test appending valid inference event."""
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        log_path = tmp_path / "logs" / "events.jsonl"
        set_event_log_path(log_path)

        event = {
            "schema_version": 1,
            "created_ts": 1234567890.0,
            "request_id": "req-123",
            "model": "gpt-4",
            "latency_ms": 150.5,
            "cost_usd": 0.001,
            "success": True,
        }
        append_inference_event(event)

        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1
        logged = json.loads(lines[0])
        assert logged["request_id"] == "req-123"
        assert logged["model"] == "gpt-4"
    finally:
        os.chdir(old_cwd)
        set_event_log_path(None)


def test_append_inference_event_invalid_data(tmp_path: Path, caplog) -> None:
    """Test appending invalid event logs error but doesn't crash."""
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        log_path = tmp_path / "logs" / "events.jsonl"
        set_event_log_path(log_path)

        event = {
            "schema_version": 1,
            "created_ts": 1234567890.0,
            # Missing request_id
            "model": "gpt-4",
            "latency_ms": 150.5,
            "cost_usd": 0.001,
            "success": True,
        }
        append_inference_event(event)

        # Should not crash, but should log error
        # File should not be created or be empty
        if log_path.exists():
            assert log_path.read_text().strip() == ""
    finally:
        os.chdir(old_cwd)
        set_event_log_path(None)


def test_append_inference_event_no_path() -> None:
    """Test appending event with no path set does nothing."""
    set_event_log_path(None)
    event = {
        "schema_version": 1,
        "created_ts": 1234567890.0,
        "request_id": "req-123",
        "model": "gpt-4",
        "latency_ms": 150.5,
        "cost_usd": 0.001,
        "success": True,
    }
    append_inference_event(event)  # Should not crash


def test_append_inference_event_creates_parent_dir(tmp_path: Path) -> None:
    """Test appending event creates parent directories."""
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        log_path = tmp_path / "logs" / "nested" / "deep" / "events.jsonl"
        set_event_log_path(log_path)

        event = {
            "schema_version": 1,
            "created_ts": 1234567890.0,
            "request_id": "req-123",
            "model": "gpt-4",
            "latency_ms": 150.5,
            "cost_usd": 0.001,
            "success": True,
        }
        append_inference_event(event)

        assert log_path.exists()
        assert log_path.parent.exists()
    finally:
        os.chdir(old_cwd)
        set_event_log_path(None)


# ============================================================================
# set_event_log_path Tests
# ============================================================================


def test_set_event_log_path_none() -> None:
    """Test setting event log path to None disables logging."""
    set_event_log_path(None)
    # Should not crash


def test_set_event_log_path_invalid() -> None:
    """Test setting invalid event log path raises error."""
    with pytest.raises(ValueError, match="must be within allowed directories"):
        set_event_log_path(Path("/etc/passwd"))


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(tmp_path: Path) -> None:
    """Test full workflow: set path, set cost, append events."""
    import os

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        log_path = tmp_path / "logs" / "events.jsonl"
        set_event_log_path(log_path)
        set_cost_per_1k_tokens_usd(0.002)

        events = [
            {
                "schema_version": 1,
                "created_ts": 1234567890.0 + i,
                "request_id": f"req-{i}",
                "model": "gpt-4",
                "latency_ms": 100.0 + i * 10,
                "cost_usd": 0.001,
                "success": True,
                "tokens_in": 100,
                "tokens_out": 50,
            }
            for i in range(10)
        ]

        for event in events:
            append_inference_event(event)

        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 10

        for i, line in enumerate(lines):
            logged = json.loads(line)
            assert logged["request_id"] == f"req-{i}"
            assert logged["latency_ms"] == 100.0 + i * 10
    finally:
        os.chdir(old_cwd)
        set_event_log_path(None)
