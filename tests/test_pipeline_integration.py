"""Integration tests for the scheduler -> request pipeline execution path.

These tests exercise the full scheduler lifecycle: enqueue, admit, batch,
complete — verifying end-to-end behavior without hardware dependencies.
"""

from __future__ import annotations

import sys
import types
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _ensure_mlx_stub():
    """Inject a minimal `mlx.core` stub when mlx is unavailable.

    `parallax.server.scheduler` imports `parallax.server.cache_manager`, which
    imports `mlx.core`. These pipeline tests only exercise scheduler batching
    logic (no tensor math), so a no-op stub lets them run headlessly on any OS.
    """
    try:
        spec = importlib.util.find_spec("mlx")
    except (ImportError, ValueError, AttributeError):
        spec = None
    if spec is not None:
        return
    if "mlx" in sys.modules and "mlx.core" in sys.modules:
        return
    mlx = types.ModuleType("mlx")
    mlx_core = types.ModuleType("mlx.core")
    # Minimal dtype sentinels referenced at import/annotation/class-def time.
    for name in (
        "bfloat16",
        "float32",
        "float16",
        "int32",
        "int64",
        "uint32",
        "bool_",
        "Dtype",
        "array",
    ):
        setattr(mlx_core, name, type(name, (), {}))

    def _not_impl(*args, **kwargs):
        raise NotImplementedError("mlx is not available in this environment")

    for fn in (
        "zeros",
        "concatenate",
        "get_active_memory",
        "eval",
    ):
        setattr(mlx_core, fn, _not_impl)
    mlx.core = mlx_core
    sys.modules["mlx"] = mlx
    sys.modules["mlx.core"] = mlx_core


_ensure_mlx_stub()

from parallax.server.request import InitialRequest, Request, RequestStatus  # noqa: E402
from parallax.server.scheduler import Scheduler  # noqa: E402


class FakeCacheManager:
    """Minimal cache manager stub that always succeeds."""

    def __init__(self, allow: bool = True, max_reqs: int = 100):
        self.allow = allow
        self.max_reqs = max_reqs
        self._reqs: set[str] = set()

    def has_request(self, request_id: str) -> bool:
        return request_id in self._reqs

    def allocate_request(self, request_id: str, num_tokens: int) -> bool:
        if not self.allow or len(self._reqs) >= self.max_reqs:
            return False
        self._reqs.add(request_id)
        return True

    def free_request(self, request_id: str) -> None:
        self._reqs.discard(request_id)


def _make_initial(rid: str, prompt_len: int = 10) -> InitialRequest:
    return InitialRequest(request_id=rid, input_ids=list(range(prompt_len)))


def _make_scheduler(cache, max_batch_size=8, max_num_tokens_per_batch=10000) -> Scheduler:
    return Scheduler(
        max_batch_size=max_batch_size,
        max_num_tokens_per_batch=max_num_tokens_per_batch,
        micro_batch_ratio=1,
        is_first_peer=True,
        cache_manager=cache,
    )


class TestPipelineIntegration:
    """End-to-end scheduler pipeline tests."""

    def test_full_request_lifecycle(self):
        """A request goes through enqueue -> admit -> form_batch."""
        cache = FakeCacheManager()
        sched = _make_scheduler(cache)
        req = _make_initial("req-1", prompt_len=5)
        sched.enque_request(req)

        # Admission happens inside form_batch via admit_requests
        sched.form_batch()

        # The prefill request was admitted and allocated KV residency
        assert cache.has_request("req-1")
        assert "req-1" in sched._running_requests

    def test_multiple_requests_batched(self):
        """Multiple requests are admitted together."""
        cache = FakeCacheManager()
        sched = _make_scheduler(cache)
        for i in range(4):
            sched.enque_request(_make_initial(f"r{i}", prompt_len=5))

        sched.form_batch()

        # All 4 should be admitted (within batch limit)
        for i in range(4):
            assert cache.has_request(f"r{i}")
            assert f"r{i}" in sched._running_requests

    def test_cache_backpressure_limits_admission(self):
        """When cache refuses allocation, requests stay in the wait queue."""
        cache = FakeCacheManager(max_reqs=2)
        sched = _make_scheduler(cache)
        for i in range(4):
            sched.enque_request(_make_initial(f"r{i}", prompt_len=5))

        sched.form_batch()

        # Only 2 should be admitted
        admitted = sum(1 for i in range(4) if cache.has_request(f"r{i}"))
        assert admitted == 2
        assert len(sched._running_requests) == 2

    def test_decode_requests_included_before_prefill(self):
        """Ready decode requests are admitted to the active batch before prefills."""
        cache = FakeCacheManager()
        sched = _make_scheduler(cache, max_batch_size=4)

        # A decode request already in the running set
        decode_req = Request(request_id="decode-1", status=RequestStatus.DECODING, prompt_len=3)
        decode_req.ready_for_next_step = True
        cache.allocate_request("decode-1", 3)
        sched._running_requests["decode-1"] = decode_req

        # New prefill arrives
        sched.enque_request(_make_initial("prefill-0", prompt_len=5))

        batch = sched.form_batch()

        batch_ids = {r.request_id for r in batch}
        assert "decode-1" in batch_ids
        assert "prefill-0" in batch_ids

    def test_request_status_transitions(self):
        """Verify request status is set correctly during pipeline stages."""
        req = _make_initial("status-test", prompt_len=3)
        assert req.request_id == "status-test"
        assert req.status == RequestStatus.PREFILLING
        assert req.is_prefill

        req.update_status(RequestStatus.DECODING)
        assert req.status == RequestStatus.DECODING
        assert req.is_decoding

    def test_empty_queue_returns_empty_batch(self):
        """Scheduler with no pending requests returns an empty batch."""
        cache = FakeCacheManager()
        sched = _make_scheduler(cache)
        batch = sched.form_batch()
        assert batch == []

    def test_large_prompt_respects_token_limit(self):
        """A prompt exceeding max tokens per batch is not placed into the batch."""
        cache = FakeCacheManager()
        sched = _make_scheduler(cache, max_num_tokens_per_batch=100)

        # Small prompt fits
        sched.enque_request(_make_initial("small", prompt_len=10))
        # Large prompt exceeds the token budget
        sched.enque_request(_make_initial("large", prompt_len=200))

        batch = sched.form_batch()

        # Small is admitted; large may be deferred
        assert cache.has_request("small")
        # The batch must respect the token budget
        assert sum(r.prompt_len if r.is_prefill else 1 for r in batch) <= 100
