"""Tests for CacheManager — KV and Linear cache allocation."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# CacheManager depends on mlx, which may not be available.
# We conditionally skip if mlx is absent.
mlx_spec = None
try:
    import importlib.util
    mlx_spec = importlib.util.find_spec("mlx")
except Exception:
    pass

pytestmark = pytest.mark.skipif(mlx_spec is None, reason="mlx not installed")


@pytest.fixture
def mock_allocators():
    """Patch BlockAllocator and SlotAllocator."""
    with patch("parallax.server.cache_manager.BlockAllocator") as mock_ba, \
         patch("parallax.server.cache_manager.SlotAllocator") as mock_sa, \
         patch("parallax.server.cache_manager.KVCache") as mock_kv, \
         patch("parallax.server.cache_manager.DeepSeekSparseCache") as mock_dsa, \
         patch("parallax.server.cache_manager.LinearCache") as mock_lc:
        mock_ba_inst = MagicMock()
        mock_ba.return_value = mock_ba_inst
        mock_sa_inst = MagicMock()
        mock_sa.return_value = mock_sa_inst
        yield {
            "BlockAllocator": mock_ba,
            "SlotAllocator": mock_sa,
            "KVCache": mock_kv,
            "DeepSeekSparseCache": mock_dsa,
            "LinearCache": mock_lc,
            "ba_inst": mock_ba_inst,
            "sa_inst": mock_sa_inst,
        }


if mlx_spec is not None:
    import mlx.core as mx
    from parallax.server.cache_manager import CacheManager

    class TestCacheManagerInit:
        """Tests for CacheManager initialization."""

        def test_default_layer_types_all_attention(self, mock_allocators):
            cm = CacheManager(
                num_layers=4,
                num_kv_heads=8,
                head_dim=64,
                dtype=mx.float16,
                block_size=16,
                num_gpu_blocks=100,
            )
            assert cm.layer_types == ["attention"] * 4
            assert cm.needs_blocks is True
            assert cm.needs_slots is False

        def test_hybrid_layer_types(self, mock_allocators):
            cm = CacheManager(
                num_layers=4,
                num_kv_heads=8,
                head_dim=64,
                dtype=mx.float16,
                block_size=16,
                num_gpu_blocks=100,
                layer_types=["attention", "linear", "attention", "linear"],
                conv_dim=128,
                conv_kernel_size=4,
                linear_k_dim=64,
                linear_v_dim=64,
                linear_num_k_heads=8,
                linear_num_v_heads=8,
            )
            assert cm.needs_blocks is True
            assert cm.needs_slots is True
            assert len(cm.caches) == 4

        def test_layer_types_length_mismatch_raises(self, mock_allocators):
            with pytest.raises(AssertionError):
                CacheManager(
                    num_layers=4,
                    num_kv_heads=8,
                    head_dim=64,
                    dtype=mx.float16,
                    num_gpu_blocks=100,
                    layer_types=["attention", "attention"],  # wrong length
                )

        def test_unknown_layer_type_raises(self, mock_allocators):
            with pytest.raises(ValueError, match="Unknown layer type"):
                CacheManager(
                    num_layers=1,
                    num_kv_heads=8,
                    head_dim=64,
                    dtype=mx.float16,
                    num_gpu_blocks=100,
                    layer_types=["unknown"],
                )

    class TestCacheManagerAllocation:
        """Tests for request allocation and freeing."""

        @pytest.fixture
        def cm(self, mock_allocators):
            mocks = mock_allocators
            mocks["ba_inst"].get_num_free_blocks.return_value = 100
            mocks["ba_inst"].allocate.return_value = [0, 1, 2]
            mgr = CacheManager(
                num_layers=2,
                num_kv_heads=8,
                head_dim=64,
                dtype=mx.float16,
                block_size=16,
                num_gpu_blocks=100,
            )
            return mgr

        def test_can_allocate_returns_true(self, cm, mock_allocators):
            mock_allocators["ba_inst"].get_num_free_blocks.return_value = 10
            assert cm.can_allocate(16) is True

        def test_can_allocate_returns_false_insufficient_blocks(self, cm, mock_allocators):
            mock_allocators["ba_inst"].get_num_free_blocks.return_value = 0
            assert cm.can_allocate(16) is False

        def test_allocate_request_success(self, cm, mock_allocators):
            mock_allocators["ba_inst"].allocate.return_value = [0, 1]
            result = cm.allocate_request("req-1", 20)
            assert result is True
            assert "req-1" in cm.block_tables
            assert cm.context_lengths["req-1"] == 20

        def test_allocate_request_already_allocated(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [0]
            result = cm.allocate_request("req-1", 10)
            assert result is True  # returns True without re-allocating

        def test_allocate_request_fails_not_enough_blocks(self, cm, mock_allocators):
            mock_allocators["ba_inst"].allocate.return_value = [0]  # only 1 block but need 2
            result = cm.allocate_request("req-2", 20)
            assert result is False
            assert "req-2" not in cm.block_tables

        def test_free_request(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [0, 1]
            cm.context_lengths["req-1"] = 20
            cm.free_request("req-1")
            assert "req-1" not in cm.block_tables
            assert "req-1" not in cm.context_lengths
            mock_allocators["ba_inst"].free.assert_called_with([0, 1])

        def test_free_request_not_found(self, cm, mock_allocators):
            # Should not raise
            cm.free_request("nonexistent")

        def test_release_request_delegates_to_free(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [0]
            cm.context_lengths["req-1"] = 10
            cm.release_request("req-1")
            assert "req-1" not in cm.block_tables

        def test_has_request(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [0]
            assert cm.has_request("req-1") is True
            assert cm.has_request("req-2") is False

        def test_append_slot_within_block(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [0]
            cm.context_lengths["req-1"] = 5
            assert cm.append_slot("req-1") is True
            assert cm.context_lengths["req-1"] == 6

        def test_append_slot_needs_new_block(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [0]
            cm.context_lengths["req-1"] = 16  # exactly at block boundary
            mock_allocators["ba_inst"].allocate.return_value = [1]
            assert cm.append_slot("req-1") is True
            assert cm.context_lengths["req-1"] == 17
            assert 1 in cm.block_tables["req-1"]

        def test_append_slot_fails_no_blocks(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [0]
            cm.context_lengths["req-1"] = 16
            mock_allocators["ba_inst"].allocate.return_value = []
            assert cm.append_slot("req-1") is False

        def test_append_slot_unknown_request_raises(self, cm, mock_allocators):
            with pytest.raises(ValueError, match="not found"):
                cm.append_slot("nonexistent")

        def test_get_block_table(self, cm, mock_allocators):
            cm.block_tables["req-1"] = [5, 6]
            assert cm.get_block_table("req-1") == [5, 6]
            assert cm.get_block_table("missing") == []

        def test_get_context_length(self, cm, mock_allocators):
            cm.context_lengths["req-1"] = 42
            assert cm.get_context_length("req-1") == 42
            assert cm.get_context_length("missing") == 0

        def test_get_caches(self, cm, mock_allocators):
            assert len(cm.get_caches()) == 2
