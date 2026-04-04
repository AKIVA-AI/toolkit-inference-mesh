"""Tests for SharedState inter-process communication utilities."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parallax.utils.shared_state import SharedState


class TestSharedStateInit:
    """Tests for SharedState initialization."""

    def test_init_with_none_creates_manager_dict(self):
        """When initialized with None, SharedState creates a new Manager().dict()."""
        with patch("parallax.utils.shared_state.multiprocessing.Manager") as mock_mgr:
            mock_dict = MagicMock()
            mock_mgr.return_value.dict.return_value = mock_dict
            state = SharedState(manager_dict=None)
            assert state._dict is mock_dict
            mock_mgr.return_value.dict.assert_called_once()

    def test_init_with_dict(self):
        """When initialized with a regular dict, wraps it directly."""
        d = {"key": "value"}
        state = SharedState(manager_dict=d)
        assert state._dict is d

    def test_init_with_shared_state(self):
        """When initialized with another SharedState, uses its underlying dict."""
        inner = {"key": "value"}
        s1 = SharedState(manager_dict=inner)
        s2 = SharedState(manager_dict=s1)
        assert s2._dict is inner


class TestSharedStateDictInterface:
    """Tests for dict-like access on SharedState."""

    def setup_method(self):
        self.d: Dict[str, Any] = {}
        self.state = SharedState(manager_dict=self.d)

    def test_get_existing_key(self):
        self.d["foo"] = 42
        assert self.state.get("foo") == 42

    def test_get_missing_key_returns_default(self):
        assert self.state.get("missing") is None
        assert self.state.get("missing", "fallback") == "fallback"

    def test_set(self):
        self.state.set("bar", 99)
        assert self.d["bar"] == 99

    def test_update(self):
        self.state.update(a=1, b=2)
        assert self.d["a"] == 1
        assert self.d["b"] == 2

    def test_getitem(self):
        self.d["x"] = "hello"
        assert self.state["x"] == "hello"

    def test_setitem(self):
        self.state["y"] = "world"
        assert self.d["y"] == "world"

    def test_contains(self):
        self.d["exists"] = True
        assert "exists" in self.state
        assert "missing" not in self.state

    def test_dict_property(self):
        assert self.state.dict is self.d


class TestSharedStateMetrics:
    """Tests for metrics-related methods."""

    def setup_method(self):
        metrics_dict = {"current_requests": 0, "layer_latency_ms": None, "_last_update_ts": 0.0}
        self.d: Dict[str, Any] = {"metrics": metrics_dict}
        self.state = SharedState(manager_dict=self.d)

    def test_get_metrics_returns_copy(self):
        result = self.state.get_metrics()
        assert result["current_requests"] == 0
        assert result["layer_latency_ms"] is None

    def test_get_metrics_empty(self):
        state = SharedState(manager_dict={})
        assert state.get_metrics() == {}

    def test_update_metrics_current_requests(self):
        self.state.update_metrics(current_requests=5)
        assert self.d["metrics"]["current_requests"] == 5

    def test_update_metrics_latency_initial(self):
        self.state.update_metrics(layer_latency_ms_sample=10.0)
        assert self.d["metrics"]["layer_latency_ms"] == 10.0

    def test_update_metrics_latency_ewma(self):
        self.d["metrics"]["layer_latency_ms"] = 10.0
        self.state.update_metrics(layer_latency_ms_sample=20.0, ewma_alpha=0.5)
        expected = 0.5 * 10.0 + 0.5 * 20.0
        assert abs(self.d["metrics"]["layer_latency_ms"] - expected) < 1e-6

    def test_update_metrics_sets_timestamp(self):
        before = time.time()
        self.state.update_metrics(current_requests=1)
        after = time.time()
        ts = self.d["metrics"]["_last_update_ts"]
        assert before <= ts <= after

    def test_update_metrics_raises_without_metrics_key(self):
        state = SharedState(manager_dict={})
        with pytest.raises(RuntimeError, match="metrics not initialized"):
            state.update_metrics(current_requests=1)


class TestSharedStateModelInfo:
    """Tests for model info and status methods."""

    def setup_method(self):
        self.d: Dict[str, Any] = {
            "model_name": "llama-7b",
            "block_start_index": 0,
            "block_end_index": 16,
            "tp_size": 2,
            "_layer_allocation_changed": True,
            "status": "running",
        }
        self.state = SharedState(manager_dict=self.d)

    def test_get_model_info(self):
        info = self.state.get_model_info()
        assert info["model_name"] == "llama-7b"
        assert info["block_start_index"] == 0
        assert info["block_end_index"] == 16
        assert info["tp_size"] == 2
        assert info["_layer_allocation_changed"] is True

    def test_get_layer_allocation_changed(self):
        assert self.state.get_layer_allocation_changed() is True

    def test_get_layer_allocation_changed_default(self):
        state = SharedState(manager_dict={})
        assert state.get_layer_allocation_changed() is False

    def test_get_status(self):
        assert self.state.get_status() == "running"

    def test_set_status(self):
        self.state.set_status("idle")
        assert self.d["status"] == "idle"

    def test_get_status_none(self):
        state = SharedState(manager_dict={})
        assert state.get_status() is None


class TestSharedStateCreate:
    """Tests for the class factory method."""

    def test_create_returns_shared_state(self):
        state = SharedState.create()
        assert isinstance(state, SharedState)

    def test_create_has_defaults(self):
        state = SharedState.create()
        assert state.get("block_start_index") is None
        assert state.get("block_end_index") is None
        assert state.get("model_name") is None
        assert state.get("tp_size") is None
        assert state.get("_layer_allocation_changed") is False
        assert state.get("status") is None

    def test_create_has_metrics(self):
        state = SharedState.create()
        metrics = state.get_metrics()
        assert metrics["current_requests"] == 0
        assert metrics["layer_latency_ms"] is None
        assert metrics["_last_update_ts"] == 0.0
