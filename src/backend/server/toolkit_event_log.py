from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

_event_log_path: Path | None = None
_event_log_lock = Lock()
_cost_per_1k_tokens_usd: float = 0.0


class InferenceEvent(BaseModel):
    """Schema for inference event logs (v1)."""

    schema_version: int = Field(ge=1, le=1, description="Event schema version")
    created_ts: float = Field(gt=0, description="Event creation timestamp")
    request_id: str = Field(min_length=1, description="Unique request ID")
    tenant: str = Field(default="", description="Tenant identifier")
    project: str = Field(default="", description="Project identifier")
    tier: str = Field(default="", description="Service tier")
    provider: str = Field(default="parallax", description="Inference provider")
    model: str = Field(min_length=1, description="Model name")
    latency_ms: float = Field(ge=0, description="Request latency in milliseconds")
    cost_usd: float = Field(ge=0, description="Estimated cost in USD")
    success: bool = Field(description="Request success status")
    error_type: str = Field(default="", description="Error type if failed")
    tokens_in: int | None = Field(None, ge=0, description="Input tokens")
    tokens_out: int | None = Field(None, ge=0, description="Output tokens")
    meta: dict = Field(default_factory=dict, description="Additional metadata")

    @field_validator("request_id", "model")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


def validate_event_log_path(path: Path) -> Path:
    """Validate event log path to prevent path traversal.

    Args:
        path: Path to validate

    Returns:
        Validated absolute path

    Raises:
        ValueError: If path is unsafe or invalid
    """
    resolved = path.resolve()

    allowed_dirs = [
        Path.home() / ".akiva",
        Path("/var/log/akiva"),
        Path.cwd() / "logs",
    ]

    for allowed in allowed_dirs:
        try:
            resolved.relative_to(allowed.resolve())
            return resolved
        except ValueError:
            continue

    raise ValueError(
        f"Event log path must be within allowed directories: "
        f"{', '.join(str(d) for d in allowed_dirs)}"
    )


def set_event_log_path(path: Path | None) -> None:
    """Set the event log file path.

    Args:
        path: Path to event log file, or None to disable logging

    Raises:
        ValueError: If path is invalid or unsafe
    """
    global _event_log_path
    if path is None:
        _event_log_path = None
        return

    validated_path = validate_event_log_path(path)
    _event_log_path = validated_path
    logger.info(f"Event log path set to: {validated_path}")


def set_cost_per_1k_tokens_usd(cost: float) -> None:
    """Set cost per 1K tokens with validation.

    Args:
        cost: Cost per 1000 tokens in USD (must be >= 0)

    Raises:
        ValueError: If cost is negative or invalid
    """
    global _cost_per_1k_tokens_usd

    try:
        cost_value = float(cost)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid cost value: {cost}. Must be a number.") from e

    if cost_value < 0:
        raise ValueError(f"Cost must be non-negative, got: {cost_value}")

    if cost_value > 100.0:
        logger.warning(f"Unusually high cost per 1K tokens: ${cost_value}")

    _cost_per_1k_tokens_usd = cost_value
    logger.info(f"Cost per 1K tokens set to: ${cost_value:.4f}")


def estimate_cost_usd(*, tokens_in: int | None, tokens_out: int | None) -> float:
    """Estimate cost in USD based on token count.

    Args:
        tokens_in: Number of input tokens (None if unknown)
        tokens_out: Number of output tokens (None if unknown)

    Returns:
        Estimated cost in USD
    """
    if _cost_per_1k_tokens_usd <= 0:
        return 0.0
    total = 0
    if isinstance(tokens_in, int) and tokens_in >= 0:
        total += tokens_in
    if isinstance(tokens_out, int) and tokens_out >= 0:
        total += tokens_out
    return (total / 1000.0) * _cost_per_1k_tokens_usd


def append_inference_event(event: dict[str, Any]) -> None:
    """Append validated inference event to JSONL log file.

    Logs errors but does not raise exceptions to avoid
    disrupting the main inference flow.

    Args:
        event: Event data dictionary
    """
    if _event_log_path is None:
        return

    try:
        validated_event = InferenceEvent(**event)
        line = validated_event.model_dump_json(exclude_none=True) + "\n"

        with _event_log_lock:
            _event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with _event_log_path.open("a", encoding="utf-8") as f:
                f.write(line)

    except Exception as e:
        logger.error(
            f"Failed to log inference event for request {event.get('request_id', 'unknown')}: {e}",
            exc_info=True,
        )
