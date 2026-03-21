"""Tests for scheduling.node: Node, NodeHardwareInfo, RequestSignal, RooflinePerformanceModel.

Covers:
- Node layer allocation, capacity, and property helpers
- RequestSignal defaults
- RooflinePerformanceModel compute and IO latency
- RTT cache and network-aware routing hooks
- Edge cases: overloaded nodes, missing layers, zero-layer allocations
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import mock_hw_deps  # noqa: E402, F401 — must precede scheduling imports

from scheduling.model_info import ModelInfo
from scheduling.node import Node, NodeHardwareInfo, RequestSignal, RooflinePerformanceModel


def _hw(**overrides) -> NodeHardwareInfo:
    defaults = dict(
        node_id="test-hw",
        num_gpus=1,
        tflops_fp16=200.0,
        gpu_name="TestGPU",
        memory_gb=80.0,
        memory_bandwidth_gbps=1000.0,
        device="cuda",
    )
    defaults.update(overrides)
    return NodeHardwareInfo(**defaults)


def _model(num_layers=12, **overrides) -> ModelInfo:
    defaults = dict(
        model_name="test-model",
        mlx_model_name="test-mlx",
        head_size=64,
        hidden_dim=2048,
        intermediate_dim=5504,
        num_attention_heads=32,
        num_kv_heads=8,
        vocab_size=32000,
        num_layers=num_layers,
        ffn_num_projections=3,
        param_bytes_per_element=1,
        mlx_param_bytes_per_element=1,
        cache_bytes_per_element=2,
        embedding_bytes_per_element=2,
    )
    defaults.update(overrides)
    return ModelInfo(**defaults)


def _node(node_id="n1", num_layers=12, **overrides) -> Node:
    hw = _hw(node_id=node_id)
    model = _model(num_layers)
    defaults = dict(
        node_id=node_id,
        hardware=hw,
        model_info=model,
        _force_max_concurrent_requests=True,
    )
    defaults.update(overrides)
    return Node(**defaults)


# ============================================================================
# RequestSignal Tests
# ============================================================================


class TestRequestSignal:
    """Tests for the RequestSignal dataclass."""

    def test_defaults(self):
        before = time.time()
        sig = RequestSignal(request_id="req-1")
        after = time.time()
        assert sig.request_id == "req-1"
        assert before <= sig.received_ts <= after
        assert sig.routing_table is None

    def test_custom_routing_table(self):
        sig = RequestSignal(request_id="req-2", routing_table=["a", "b"])
        assert sig.routing_table == ["a", "b"]

    def test_empty_routing_table_means_all_full(self):
        sig = RequestSignal(request_id="req-3", routing_table=[])
        assert sig.routing_table == []


# ============================================================================
# NodeHardwareInfo Tests
# ============================================================================


class TestNodeHardwareInfo:
    """Tests for NodeHardwareInfo dataclass."""

    def test_fields(self):
        hw = _hw(node_id="gpu-01", num_gpus=4, memory_gb=320.0)
        assert hw.node_id == "gpu-01"
        assert hw.num_gpus == 4
        assert hw.memory_gb == 320.0
        assert hw.device == "cuda"


# ============================================================================
# Node Allocation Tests
# ============================================================================


class TestNodeLayerAllocation:
    """Tests for Node layer allocation and related properties."""

    def test_initial_state_no_layers(self):
        n = _node()
        assert n.start_layer is None
        assert n.end_layer is None
        assert n.num_current_layers == 0

    def test_set_layer_allocation(self):
        n = _node()
        n.set_layer_allocation(2, 8)
        assert n.start_layer == 2
        assert n.end_layer == 8
        assert n.num_current_layers == 6

    def test_clear_layer_allocation(self):
        n = _node()
        n.set_layer_allocation(0, 12)
        n.clear_layer_allocation()
        assert n.start_layer is None
        assert n.end_layer is None
        assert n.num_current_layers == 0

    def test_has_embedding_true(self):
        n = _node()
        n.set_layer_allocation(0, 6)
        assert n.has_embedding is True

    def test_has_embedding_false(self):
        n = _node()
        n.set_layer_allocation(3, 9)
        assert n.has_embedding is False

    def test_has_embedding_no_allocation(self):
        n = _node()
        assert n.has_embedding is False

    def test_has_lm_head_true(self):
        n = _node(num_layers=12)
        n.set_layer_allocation(6, 12)
        assert n.has_lm_head is True

    def test_has_lm_head_false(self):
        n = _node(num_layers=12)
        n.set_layer_allocation(0, 6)
        assert n.has_lm_head is False

    def test_has_lm_head_no_allocation(self):
        n = _node()
        assert n.has_lm_head is False

    def test_hosts_layer_in_range(self):
        n = _node()
        n.set_layer_allocation(3, 7)
        assert n.hosts_layer(3) is True
        assert n.hosts_layer(6) is True
        assert n.hosts_layer(7) is False  # half-open interval
        assert n.hosts_layer(2) is False

    def test_hosts_layer_no_allocation(self):
        n = _node()
        assert n.hosts_layer(0) is False


# ============================================================================
# Node Request Load Tests
# ============================================================================


class TestNodeRequestLoad:
    """Tests for request counting and overload detection."""

    def test_add_request(self):
        n = _node()
        n.add_request()
        assert n.current_requests == 1

    def test_remove_request(self):
        n = _node()
        n.current_requests = 5
        n.remove_request()
        assert n.current_requests == 4

    def test_is_overloaded_at_capacity(self):
        n = _node()
        n.current_requests = n.max_requests
        assert n.is_overloaded is True

    def test_is_overloaded_below_capacity(self):
        n = _node()
        n.current_requests = 0
        assert n.is_overloaded is False

    def test_max_requests_forced(self):
        n = _node(max_concurrent_requests=32, _force_max_concurrent_requests=True)
        assert n.max_requests == 32


# ============================================================================
# Node RTT Tests
# ============================================================================


class TestNodeRTT:
    """Tests for RTT caching and retrieval."""

    def test_update_rtt(self):
        n = _node()
        n.update_rtt("n2", 15.5)
        assert n.rtt_to_nodes["n2"] == 15.5

    def test_get_rtt_to_self(self):
        n = _node()
        assert n.get_rtt_to(n) == 0.0

    def test_get_rtt_to_known_node(self):
        n1 = _node("n1")
        n2 = _node("n2")
        n1.update_rtt("n2", 25.0)
        assert n1.get_rtt_to(n2) == 25.0

    def test_get_rtt_to_unknown_node_returns_inf(self):
        n1 = _node("n1")
        n2 = _node("n2")
        assert n1.get_rtt_to(n2) == float("inf")

    def test_get_rtt_with_none_rtt_dict(self):
        n1 = _node("n1")
        n2 = _node("n2")
        n1.rtt_to_nodes = None
        assert n1.get_rtt_to(n2) == float("inf")


# ============================================================================
# Node Latency Tests
# ============================================================================


class TestNodeLatency:
    """Tests for layer latency computation."""

    def test_layer_latency_with_avg_set(self):
        n = _node()
        n.set_layer_allocation(0, 6)
        n.set_layer_latency_ms(10.0)
        n.current_requests = 2
        # latency = avg + load_compensator * (requests/max_requests)
        expected = 10.0 + n.load_compensator * (1.0 * 2 / n.max_requests)
        assert n.layer_latency_ms == pytest.approx(expected)

    def test_layer_latency_overloaded_returns_inf(self):
        n = _node()
        n.set_layer_allocation(0, 6)
        n.current_requests = n.max_requests
        assert n.layer_latency_ms == float("inf")

    def test_roofline_layer_latency_positive(self):
        n = _node()
        n.set_layer_allocation(0, 6)
        latency = n.roofline_layer_latency_ms()
        assert latency > 0

    def test_layer_latency_falls_back_to_roofline(self):
        n = _node()
        n.set_layer_allocation(0, 6)
        assert n.avg_layer_latency_ms is None
        # Should use roofline
        latency = n.layer_latency_ms
        assert latency > 0
        assert latency == pytest.approx(n.roofline_layer_latency_ms())


# ============================================================================
# Node Capacity Tests
# ============================================================================


class TestNodeCapacity:
    """Tests for decoder layer capacity and KV cache memory."""

    def test_get_decoder_layer_capacity_positive(self):
        n = _node()
        cap = n.get_decoder_layer_capacity()
        assert cap > 0

    def test_capacity_with_embedding_smaller(self):
        n = _node()
        cap_plain = n.get_decoder_layer_capacity()
        cap_embed = n.get_decoder_layer_capacity(include_input_embed=True)
        assert cap_embed <= cap_plain

    def test_capacity_with_lm_head_smaller(self):
        n = _node()
        cap_plain = n.get_decoder_layer_capacity()
        cap_head = n.get_decoder_layer_capacity(include_lm_head=True)
        assert cap_head <= cap_plain

    def test_per_decoder_layer_kv_cache_memory_no_layers(self):
        n = _node()
        assert n.per_decoder_layer_kv_cache_memory is None

    def test_per_decoder_layer_kv_cache_memory_with_layers(self):
        n = _node()
        n.set_layer_allocation(0, 6)
        mem = n.per_decoder_layer_kv_cache_memory
        assert mem is not None
        assert mem > 0

    def test_capacity_mlx_device(self):
        """MLX device should apply mlx_bit_factor to capacity calculation."""
        hw = _hw(device="mlx")
        model = _model()
        n = Node(
            node_id="mlx-node",
            hardware=hw,
            model_info=model,
            _force_max_concurrent_requests=True,
        )
        cap_mlx = n.get_decoder_layer_capacity()
        assert cap_mlx > 0


# ============================================================================
# RooflinePerformanceModel Tests
# ============================================================================


class TestRooflinePerformanceModel:
    """Tests for the RooflinePerformanceModel class."""

    def _make_model(self, **kwargs) -> RooflinePerformanceModel:
        hw = _hw()
        mi = _model()
        return RooflinePerformanceModel(hw, mi, **kwargs)

    def test_compute_roofline_latency_positive(self):
        rpm = self._make_model()
        lat = rpm.get_compute_roofline_latency_ms(1_000_000)
        assert lat > 0

    def test_io_roofline_latency_positive(self):
        rpm = self._make_model()
        lat = rpm.get_io_roofline_latency_ms(1_000_000)
        assert lat > 0

    def test_set_sequence_shape(self):
        rpm = self._make_model()
        rpm.set_sequence_shape(batch_size=8, target_seq_len=64, source_seq_len=512)
        assert rpm.batch_size == 8
        assert rpm.target_seq_len == 64
        assert rpm.source_seq_len == 512

    def test_set_sequence_shape_partial(self):
        rpm = self._make_model(batch_size=2)
        rpm.set_sequence_shape(batch_size=4)
        assert rpm.batch_size == 4
        # Others unchanged
        assert rpm.target_seq_len == 1
        assert rpm.source_seq_len == 256

    def test_roofline_layer_latency_ms_positive(self):
        rpm = self._make_model()
        lat = rpm.roofline_layer_latency_ms(num_current_layers=4)
        assert lat > 0

    def test_roofline_layer_latency_with_embed_and_head(self):
        rpm = self._make_model()
        lat_plain = rpm.roofline_layer_latency_ms(num_current_layers=4)
        lat_with = rpm.roofline_layer_latency_ms(
            include_input_embed=True, include_lm_head=True, num_current_layers=4
        )
        # Including embed/head should add overhead
        assert lat_with >= lat_plain

    def test_quantization_speedup_effect(self):
        rpm_fast = self._make_model(quantization_speedup=2.0)
        rpm_slow = self._make_model(quantization_speedup=0.5)
        lat_fast = rpm_fast.get_compute_roofline_latency_ms(1_000_000)
        lat_slow = rpm_slow.get_compute_roofline_latency_ms(1_000_000)
        assert lat_fast < lat_slow
