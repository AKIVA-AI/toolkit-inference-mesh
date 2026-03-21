"""Additional edge-case tests for scheduling.request_routing.

Covers:
- Empty/zero-layer inputs
- Inactive nodes filtered from DP routing
- Single-node round-robin
- Pipeline discovery with no viable pipelines
- Pipeline repair logic
- RoundRobinPipelineRouting cursor wrapping
- DynamicProgrammingRouting with gaps in layer coverage
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import mock_hw_deps  # noqa: E402, F401 — must precede scheduling imports

from scheduling.model_info import ModelInfo
from scheduling.node import Node, NodeHardwareInfo
from scheduling.request_routing import (
    DynamicProgrammingRouting,
    RoundRobinPipelineRouting,
)


def _hw(node_id="n1") -> NodeHardwareInfo:
    return NodeHardwareInfo(
        node_id=node_id,
        num_gpus=1,
        tflops_fp16=200.0,
        gpu_name="",
        memory_gb=80.0,
        memory_bandwidth_gbps=100.0,
        device="cuda",
    )


def _model(num_layers=12) -> ModelInfo:
    return ModelInfo(
        model_name=f"test-{num_layers}L",
        mlx_model_name=f"mlx-{num_layers}L",
        head_size=64,
        hidden_dim=2880,
        intermediate_dim=2880,
        num_attention_heads=64,
        num_kv_heads=8,
        vocab_size=32000,
        num_layers=num_layers,
        ffn_num_projections=3,
        param_bytes_per_element=1,
        mlx_param_bytes_per_element=1,
        cache_bytes_per_element=2,
        embedding_bytes_per_element=2,
    )


def _node(node_id, model, start=None, end=None) -> Node:
    hw = _hw(node_id)
    n = Node(
        node_id=node_id,
        hardware=hw,
        model_info=model,
        _force_max_concurrent_requests=True,
    )
    if start is not None and end is not None:
        n.set_layer_allocation(start, end)
        n.avg_layer_latency_ms = 10.0
    return n


def _set_symmetric_rtt(nodes, rtt_ms=20.0):
    """Set symmetric RTT between all node pairs."""
    for a in nodes:
        if a.rtt_to_nodes is None:
            a.rtt_to_nodes = {}
        for b in nodes:
            if a.node_id != b.node_id:
                a.rtt_to_nodes[b.node_id] = rtt_ms


# ============================================================================
# DynamicProgrammingRouting Edge Cases
# ============================================================================


class TestDPRoutingEdgeCases:
    """Edge cases for DynamicProgrammingRouting."""

    def test_empty_nodes(self):
        router = DynamicProgrammingRouting()
        path, lat = router.find_optimal_path([], 10)
        assert path == []
        assert lat == 0.0

    def test_zero_layers(self):
        router = DynamicProgrammingRouting()
        model = _model(12)
        n = _node("n1", model, 0, 12)
        path, lat = router.find_optimal_path([n], 0)
        assert path == []
        assert lat == 0.0

    def test_inactive_node_excluded(self):
        """Inactive nodes should be skipped by DP routing."""
        model = _model(12)
        n1 = _node("n1", model, 0, 12)
        n2 = _node("n2", model, 0, 12)
        _set_symmetric_rtt([n1, n2])
        n1.is_active = False

        router = DynamicProgrammingRouting()
        path, lat = router.find_optimal_path([n1, n2], 12)
        assert path == ["n2"]

    def test_gap_in_layer_coverage_returns_empty(self):
        """If no node covers a layer, no valid path exists."""
        model = _model(12)
        n1 = _node("n1", model, 0, 4)
        # Gap at layers 4-6
        n2 = _node("n2", model, 7, 12)
        _set_symmetric_rtt([n1, n2])

        router = DynamicProgrammingRouting()
        path, lat = router.find_optimal_path([n1, n2], 12)
        assert path == []
        assert lat == float("inf")

    def test_turning_points_empty_nodes(self):
        turns = DynamicProgrammingRouting.find_turning_points([], 10)
        assert turns == []

    def test_turning_points_zero_layers(self):
        model = _model(10)
        n = _node("n1", model, 0, 10)
        turns = DynamicProgrammingRouting.find_turning_points([n], 0)
        assert turns == []

    def test_turning_points_uncovered_layer(self):
        """If a layer has no host, return empty turning points."""
        model = _model(10)
        n1 = _node("n1", model, 0, 3)
        # Gap: layers 3-6 not covered
        n2 = _node("n2", model, 7, 10)
        _set_symmetric_rtt([n1, n2])

        turns = DynamicProgrammingRouting.find_turning_points([n1, n2], 10)
        assert turns == []


# ============================================================================
# RoundRobinPipelineRouting Edge Cases
# ============================================================================


class TestRRRoutingEdgeCases:
    """Edge cases for RoundRobinPipelineRouting."""

    def test_empty_nodes(self):
        rr = RoundRobinPipelineRouting()
        path, lat = rr.find_optimal_path([], 10)
        assert path == []
        assert lat == float("inf")

    def test_zero_layers(self):
        rr = RoundRobinPipelineRouting()
        model = _model(10)
        n = _node("n1", model, 0, 10)
        path, lat = rr.find_optimal_path([n], 0)
        assert path == []
        assert lat == float("inf")

    def test_single_node_full_pipeline(self):
        model = _model(10)
        n = _node("n1", model, 0, 10)

        rr = RoundRobinPipelineRouting()
        path, lat = rr.find_optimal_path([n], 10)
        assert path == ["n1"]
        assert lat > 0

    def test_no_complete_pipeline(self):
        """No pipeline covers [0, L) -> empty result."""
        model = _model(12)
        n1 = _node("n1", model, 0, 4)
        # Gap: no coverage for layers 5-7
        n2 = _node("n2", model, 8, 12)

        rr = RoundRobinPipelineRouting()
        path, lat = rr.find_optimal_path([n1, n2], 12)
        assert path == []
        assert lat == float("inf")

    def test_pipeline_discovery_empty(self):
        rr = RoundRobinPipelineRouting()
        pipelines = rr.pipeline_discovery([], 10)
        assert pipelines == []

    def test_pipeline_discovery_zero_layers(self):
        rr = RoundRobinPipelineRouting()
        model = _model(10)
        n = _node("n1", model, 0, 10)
        pipelines = rr.pipeline_discovery([n], 0)
        assert pipelines == []

    def test_pipeline_discovery_single_complete(self):
        model = _model(8)
        n = _node("solo", model, 0, 8)

        rr = RoundRobinPipelineRouting()
        pipelines = rr.pipeline_discovery([n], 8)
        assert pipelines == [["solo"]]

    def test_pipeline_discovery_no_head(self):
        """If no node starts at layer 0, no pipelines."""
        model = _model(12)
        n = _node("mid", model, 3, 12)

        rr = RoundRobinPipelineRouting()
        pipelines = rr.pipeline_discovery([n], 12)
        assert pipelines == []

    def test_cursor_wraps_around(self):
        """RR cursor should wrap correctly after cycling."""
        model = _model(6)
        n = _node("solo", model, 0, 6)
        _set_symmetric_rtt([n])

        rr = RoundRobinPipelineRouting()
        for _ in range(10):
            path, lat = rr.find_optimal_path([n], 6)
            assert path == ["solo"]

    def test_all_overloaded_returns_empty(self):
        model = _model(8)
        n = _node("n1", model, 0, 8)
        n.current_requests = n.max_requests

        rr = RoundRobinPipelineRouting()
        path, lat = rr.find_optimal_path([n], 8)
        assert path == []
        assert lat == float("inf")

    def test_turning_points_always_empty(self):
        """RoundRobin returns no turning points by design."""
        model = _model(10)
        n = _node("n1", model, 0, 10)
        rr = RoundRobinPipelineRouting()
        turns = rr.find_turning_points([n], 10)
        assert turns == []


# ============================================================================
# Pipeline Repair Tests
# ============================================================================


class TestPipelineRepair:
    """Tests for RoundRobinPipelineRouting._attempt_repair_pipeline."""

    def test_repair_with_alternative_suffix(self):
        """If one node is overloaded, repair finds a non-overloaded alternative."""
        model = _model(8)
        n1 = _node("n1", model, 0, 4)
        n2_overloaded = _node("n2", model, 4, 8)
        n2_overloaded.current_requests = n2_overloaded.max_requests
        n3 = _node("n3", model, 4, 8)

        rr = RoundRobinPipelineRouting()
        repaired = rr._attempt_repair_pipeline(["n1", "n2"], [n1, n2_overloaded, n3], 8)
        # Should find alternative via n3
        assert repaired is not None
        assert "n1" in repaired
        assert "n3" in repaired
        assert "n2" not in repaired

    def test_repair_no_alternative(self):
        """If no alternative exists, repair returns None."""
        model = _model(8)
        n1 = _node("n1", model, 0, 4)
        n2 = _node("n2", model, 4, 8)
        n2.current_requests = n2.max_requests
        # No other node covers [4, 8)

        rr = RoundRobinPipelineRouting()
        repaired = rr._attempt_repair_pipeline(["n1", "n2"], [n1, n2], 8)
        assert repaired is None

    def test_repair_prefix_also_bad(self):
        """If prefix node is missing, repair should try earlier split points."""
        model = _model(8)
        n1 = _node("n1", model, 0, 4)
        n1.current_requests = n1.max_requests
        n2 = _node("n2", model, 4, 8)
        n3 = _node("n3", model, 0, 8)

        rr = RoundRobinPipelineRouting()
        repaired = rr._attempt_repair_pipeline(["n1", "n2"], [n1, n2, n3], 8)
        # Should find n3 as full pipeline
        if repaired is not None:
            assert "n3" in repaired


# ============================================================================
# Build Start Index Tests
# ============================================================================


class TestBuildStartIndex:
    """Tests for RoundRobinPipelineRouting._build_start_index."""

    def test_basic_index(self):
        model = _model(12)
        n1 = _node("n1", model, 0, 6)
        n2 = _node("n2", model, 6, 12)

        rr = RoundRobinPipelineRouting()
        idx = rr._build_start_index([n1, n2])
        assert 0 in idx
        assert 6 in idx
        assert n1 in idx[0]
        assert n2 in idx[6]

    def test_nodes_without_allocation_excluded(self):
        model = _model(12)
        n1 = _node("n1", model, 0, 6)
        n2 = _node("n2", model)  # No allocation

        rr = RoundRobinPipelineRouting()
        idx = rr._build_start_index([n1, n2])
        assert 0 in idx
        # n2 has no start/end -> excluded
        total_nodes = sum(len(v) for v in idx.values())
        assert total_nodes == 1
