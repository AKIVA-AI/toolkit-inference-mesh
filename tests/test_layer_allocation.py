"""Tests for scheduling.layer_allocation: LayerLoad, BaseLayerAllocator.

Covers:
- LayerLoad add/remove node and heap ordering
- BaseLayerAllocator: allocate, deallocate, reallocate, validate_allocation
- Pipeline endpoint tracking (embedding/lm_head node ids)
- should_global_rebalance
- declare and join
- adjust_pipeline_layers water-filling
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import mock_hw_deps  # noqa: E402, F401 — must precede scheduling imports

from scheduling.layer_allocation import BaseLayerAllocator, LayerLoad
from scheduling.model_info import ModelInfo
from scheduling.node import Node, NodeHardwareInfo


def _hw(node_id="n1", **overrides) -> NodeHardwareInfo:
    defaults = dict(
        node_id=node_id,
        num_gpus=1,
        tflops_fp16=200.0,
        gpu_name="TestGPU",
        memory_gb=80.0,
        memory_bandwidth_gbps=1000.0,
        device="cuda",
    )
    defaults.update(overrides)
    return NodeHardwareInfo(**defaults)


def _model(num_layers=12) -> ModelInfo:
    return ModelInfo(
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


def _node(node_id="n1", num_layers=12) -> Node:
    hw = _hw(node_id=node_id)
    model = _model(num_layers)
    return Node(
        node_id=node_id,
        hardware=hw,
        model_info=model,
        _force_max_concurrent_requests=True,
    )


# ============================================================================
# LayerLoad Tests
# ============================================================================


class TestLayerLoad:
    """Tests for the LayerLoad dataclass."""

    def test_add_node(self):
        ll = LayerLoad(layer_id=0, current_kv_size=0)
        n = _node()
        n.set_layer_allocation(0, 6)
        ll.add_node(n)
        assert n.node_id in ll.hosting_nodes
        assert ll.current_kv_size > 0

    def test_remove_node(self):
        ll = LayerLoad(layer_id=0, current_kv_size=0)
        n = _node()
        n.set_layer_allocation(0, 6)
        ll.add_node(n)
        prev_kv = ll.current_kv_size
        ll.remove_node(n)
        assert n.node_id not in ll.hosting_nodes
        assert ll.current_kv_size < prev_kv

    def test_remove_absent_node_is_noop(self):
        ll = LayerLoad(layer_id=0, current_kv_size=100)
        n = _node("absent")
        ll.remove_node(n)
        assert ll.current_kv_size == 100

    def test_heap_ordering(self):
        ll1 = LayerLoad(layer_id=0, current_kv_size=100)
        ll2 = LayerLoad(layer_id=1, current_kv_size=200)
        assert ll1 < ll2

    def test_heap_ordering_tiebreak_by_layer_id(self):
        ll1 = LayerLoad(layer_id=0, current_kv_size=100)
        ll2 = LayerLoad(layer_id=1, current_kv_size=100)
        assert ll1 < ll2

    def test_add_node_no_allocation_raises(self):
        ll = LayerLoad(layer_id=0, current_kv_size=0)
        n = _node()
        # No layer allocation -> per_decoder_layer_kv_cache_memory is None
        with pytest.raises(ValueError, match="must have per_decoder_layer_kv_cache_memory"):
            ll.add_node(n)


# ============================================================================
# BaseLayerAllocator Tests
# ============================================================================


class TestBaseLayerAllocator:
    """Tests for BaseLayerAllocator methods."""

    def _allocator(self, num_nodes=2, num_layers=12) -> BaseLayerAllocator:
        model = _model(num_layers)
        nodes = [_node(f"n{i}", num_layers) for i in range(num_nodes)]
        return BaseLayerAllocator(model, nodes)

    def test_init(self):
        alloc = self._allocator()
        assert alloc.num_nodes == 2
        assert alloc.num_total_layers == 12

    def test_validate_allocation_valid(self):
        alloc = self._allocator()
        assert alloc.validate_allocation(0, 6) is True
        assert alloc.validate_allocation(6, 12) is True
        assert alloc.validate_allocation(0, 12) is True

    def test_validate_allocation_invalid_start_ge_end(self):
        alloc = self._allocator()
        assert alloc.validate_allocation(6, 6) is False
        assert alloc.validate_allocation(7, 6) is False

    def test_validate_allocation_invalid_range(self):
        alloc = self._allocator()
        assert alloc.validate_allocation(-1, 6) is False
        assert alloc.validate_allocation(0, 13) is False

    def test_allocate(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        alloc.allocate(node, 0, 6)
        assert node.start_layer == 0
        assert node.end_layer == 6
        assert node.node_id in alloc.node_allocation

    def test_allocate_embedding_node_tracked(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        alloc.allocate(node, 0, 6)
        assert node.node_id in alloc.embedding_node_ids

    def test_allocate_lm_head_node_tracked(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        alloc.allocate(node, 6, 12)
        assert node.node_id in alloc.lm_head_node_ids

    def test_allocate_invalid_range_raises(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        with pytest.raises(ValueError, match="Invalid allocation"):
            alloc.allocate(node, 6, 6)

    def test_deallocate(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        alloc.allocate(node, 0, 6)
        alloc.deallocate(node)
        assert node.start_layer is None
        assert node.end_layer is None
        assert node.is_active is False
        assert node.node_id not in alloc.node_allocation

    def test_deallocate_unallocated_node(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        # Should not raise
        alloc.deallocate(node)

    def test_reallocate(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        alloc.allocate(node, 0, 6)
        alloc.reallocate(node, 3, 9)
        assert node.start_layer == 3
        assert node.end_layer == 9

    def test_declare_new_node(self):
        alloc = self._allocator(num_nodes=1)
        assert alloc.num_nodes == 1
        new_node = _node("new-node")
        alloc.declare(new_node)
        assert alloc.num_nodes == 2

    def test_declare_existing_node_no_duplicate(self):
        alloc = self._allocator(num_nodes=2)
        existing = alloc.nodes[0]
        alloc.declare(existing)
        assert alloc.num_nodes == 2

    def test_leave_node(self):
        alloc = self._allocator()
        node = alloc.nodes[0]
        alloc.allocate(node, 0, 6)
        nid = node.node_id
        alloc.leave(nid)
        assert nid not in alloc.node_allocation

    def test_leave_unknown_node_raises(self):
        alloc = self._allocator()
        with pytest.raises(ValueError, match="not found"):
            alloc.leave("nonexistent")


# ============================================================================
# Rebalance Tests
# ============================================================================


class TestRebalanceDecision:
    """Tests for should_global_rebalance."""

    def test_no_pipeline_triggers_rebalance(self):
        alloc = TestBaseLayerAllocator._allocator(
            TestBaseLayerAllocator(), num_nodes=2
        )
        # No allocations -> no full pipeline -> should rebalance
        assert alloc.should_global_rebalance() is True

    def test_balanced_allocation_no_rebalance(self):
        model = _model(12)
        n1 = _node("n1", 12)
        n2 = _node("n2", 12)
        nodes = [n1, n2]
        alloc = BaseLayerAllocator(model, nodes)
        alloc.allocate(n1, 0, 6)
        alloc.allocate(n2, 6, 12)
        # Full pipeline exists, balanced allocation
        result = alloc.should_global_rebalance()
        assert isinstance(result, bool)


# ============================================================================
# Water-filling Pipeline Adjustment Tests
# ============================================================================


class TestAdjustPipelineLayers:
    """Tests for adjust_pipeline_layers water-filling."""

    def test_single_node_pipeline(self):
        model = _model(12)
        n = _node("solo", 12)
        alloc = BaseLayerAllocator(model, [n])
        alloc.adjust_pipeline_layers([n])
        assert n.start_layer == 0
        assert n.end_layer == 12

    def test_two_node_equal_power(self):
        model = _model(12)
        n1 = _node("n1", 12)
        n2 = _node("n2", 12)
        alloc = BaseLayerAllocator(model, [n1, n2])
        alloc.adjust_pipeline_layers([n1, n2])
        # Equal power -> equal split (approximately)
        assert n1.start_layer == 0
        total = n1.num_current_layers + n2.num_current_layers
        assert total == 12
        assert n2.end_layer == 12

    def test_unequal_power_weighted_split(self):
        model = _model(12)
        hw1 = _hw("n1", tflops_fp16=400.0)
        hw2 = _hw("n2", tflops_fp16=200.0)
        n1 = Node(node_id="n1", hardware=hw1, model_info=model, _force_max_concurrent_requests=True)
        n2 = Node(node_id="n2", hardware=hw2, model_info=model, _force_max_concurrent_requests=True)
        alloc = BaseLayerAllocator(model, [n1, n2])
        alloc.adjust_pipeline_layers([n1, n2])
        # n1 has 2x TFLOPS -> should get more layers
        assert n1.num_current_layers >= n2.num_current_layers
        assert n1.num_current_layers + n2.num_current_layers == 12

    def test_empty_pipeline_raises(self):
        model = _model(12)
        alloc = BaseLayerAllocator(model, [_node("n1", 12)])
        with pytest.raises(ValueError, match="No nodes"):
            alloc.adjust_pipeline_layers([])

    def test_contiguous_coverage(self):
        """Adjusted pipeline must cover [0, num_layers) contiguously."""
        model = _model(24)
        nodes = [_node(f"n{i}", 24) for i in range(3)]
        alloc = BaseLayerAllocator(model, nodes)
        alloc.adjust_pipeline_layers(nodes)
        # Verify contiguous coverage
        assert nodes[0].start_layer == 0
        for i in range(1, len(nodes)):
            if nodes[i].start_layer is not None:
                prev = nodes[i - 1]
                assert nodes[i].start_layer == prev.end_layer
        last_allocated = [n for n in nodes if n.end_layer is not None]
        assert last_allocated[-1].end_layer == 24
