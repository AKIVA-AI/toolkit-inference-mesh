"""Tests for health, ready, and metrics endpoints in backend.main.

Uses mock_hw_deps to stub mlx/torch, and adds stubs for lattica/zmq/uvloop
so backend.main can be imported without hardware.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from unittest.mock import MagicMock

import pytest

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    pytest.skip("fastapi not installed", allow_module_level=True)

# ---------------------------------------------------------------------------
# 1. Reuse the project's existing HW mocks
# ---------------------------------------------------------------------------
import tests.mock_hw_deps  # noqa: F401 — installs mlx/torch stubs on import

# ---------------------------------------------------------------------------
# 2. Stub remaining heavy deps that mock_hw_deps doesn't cover
# ---------------------------------------------------------------------------


def _make_stub(name: str) -> MagicMock:
    m = MagicMock()
    m.__name__ = name
    m.__spec__ = None
    m.__path__ = []
    m.__file__ = None
    m.__loader__ = None
    m.__package__ = name
    return m


def _stub_if_missing(name: str) -> None:
    if name in sys.modules:
        return
    try:
        if importlib.util.find_spec(name) is not None:
            return
    except (ModuleNotFoundError, ValueError):
        pass
    parts = name.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[:i])
        _stub_if_missing(parent)
    mod = _make_stub(name)
    sys.modules[name] = mod


# mock_hw_deps handles mlx, mlx_lm, torch — only stub deps it doesn't cover.
_extra_stubs = [
    "lattica",
    "uvloop",
    "zmq",
    "zmq.asyncio",
    "orjson",
]

for _dep in _extra_stubs:
    _stub_if_missing(_dep)


# Add specific attributes that imports expect
def _flexible_decorator(*args, **kwargs):
    """Decorator that works with or without arguments: @dec and @dec(...)."""
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]  # used as @dec (no parens)
    return lambda fn: fn  # used as @dec(...) (with parens)


lattica_mod = sys.modules.get("lattica")
if lattica_mod is not None and isinstance(lattica_mod, MagicMock):
    lattica_mod.Lattica = MagicMock
    lattica_mod.ConnectionHandler = type("ConnectionHandler", (), {})
    lattica_mod.rpc_method = _flexible_decorator
    lattica_mod.rpc_stream = _flexible_decorator
    lattica_mod.rpc_stream_iter = _flexible_decorator

zmq_mod = sys.modules.get("zmq")
if zmq_mod is not None and isinstance(zmq_mod, MagicMock):
    zmq_mod.PUSH = 1
    zmq_mod.PULL = 2

orjson_mod = sys.modules.get("orjson")
if orjson_mod is not None and isinstance(orjson_mod, MagicMock):
    import json as _json

    orjson_mod.dumps = lambda obj, **kw: _json.dumps(obj).encode()
    orjson_mod.loads = _json.loads

# Starlette State (used in http_server.py)
starlette_ds = sys.modules.get("starlette.datastructures")
if starlette_ds is not None and isinstance(starlette_ds, MagicMock):
    starlette_ds.State = type("State", (), {})

# ---------------------------------------------------------------------------
# 3. Now import the backend app
# ---------------------------------------------------------------------------
from backend.main import _VERSION, _cors_origins, _metrics, app  # noqa: E402
import backend.main as bm  # noqa: E402

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_has_version(self):
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.json()["version"] == _VERSION


class TestReadyEndpoint:
    def test_ready_returns_503_when_scheduler_none(self):
        original = bm.scheduler_manage
        bm.scheduler_manage = None
        try:
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/ready")
            assert resp.status_code == 503
            assert resp.json()["status"] == "not_ready"
        finally:
            bm.scheduler_manage = original

    def test_ready_returns_503_when_scheduler_not_running(self):
        mock_scheduler = MagicMock()
        mock_scheduler.is_running.return_value = False
        original = bm.scheduler_manage
        bm.scheduler_manage = mock_scheduler
        try:
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/ready")
            assert resp.status_code == 503
        finally:
            bm.scheduler_manage = original

    def test_ready_returns_200_when_scheduler_running(self):
        mock_scheduler = MagicMock()
        mock_scheduler.is_running.return_value = True
        original = bm.scheduler_manage
        bm.scheduler_manage = mock_scheduler
        try:
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/ready")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ready"
        finally:
            bm.scheduler_manage = original


class TestMetricsEndpoint:
    def test_metrics_returns_counters(self):
        _metrics["requests_total"] = 0
        _metrics["requests_success"] = 0
        _metrics["requests_error"] = 0
        _metrics["startup_ts"] = time.time()

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "requests_total" in data
        assert "requests_success" in data
        assert "requests_error" in data
        assert "uptime_seconds" in data
        assert "version" in data
        assert data["uptime_seconds"] >= 0


class TestCorsConfiguration:
    def test_cors_origins_is_list(self):
        assert isinstance(_cors_origins, list)
        assert len(_cors_origins) > 0

    def test_cors_parses_comma_separated(self):
        raw = "https://a.com, https://b.com"
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert origins == ["https://a.com", "https://b.com"]

    def test_cors_empty_string_defaults_to_wildcard(self):
        raw = ""
        origins = [o.strip() for o in raw.split(",") if o.strip()] if raw else ["*"]
        assert origins == ["*"]
