"""Tests for RadixCache and TreeNode prefix caching."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# RadixCache depends on mlx
import importlib.util

mlx_spec = importlib.util.find_spec("mlx")
pytestmark = pytest.mark.skipif(mlx_spec is None, reason="mlx not installed")


if mlx_spec is not None:
    import mlx.core as mx
    from parallax.server.radix_cache import (
        RadixCache,
        TreeNode,
        _key_match_page_size1,
        _key_match_paged,
    )

    # ======================================================================
    # TreeNode tests
    # ======================================================================

    class TestTreeNode:
        def test_counter_increments(self):
            start = TreeNode.counter
            n1 = TreeNode()
            n2 = TreeNode()
            assert n2.node_id == start + 1

        def test_explicit_node_id(self):
            n = TreeNode(node_id=999)
            assert n.node_id == 999

        def test_evicted_when_value_is_none(self):
            n = TreeNode()
            n.value = None
            assert n.evicted is True

        def test_not_evicted_when_value_set(self):
            n = TreeNode()
            n.value = [1, 2, 3]
            assert n.evicted is False

        def test_lt_compares_access_time(self):
            n1 = TreeNode()
            n1.last_access_time = 1.0
            n2 = TreeNode()
            n2.last_access_time = 2.0
            assert n1 < n2
            assert not n2 < n1

    # ======================================================================
    # Key match helpers
    # ======================================================================

    class TestKeyMatch:
        def test_page_size1_full_match(self):
            assert _key_match_page_size1([1, 2, 3], [1, 2, 3]) == 3

        def test_page_size1_partial_match(self):
            assert _key_match_page_size1([1, 2, 3], [1, 2, 4]) == 2

        def test_page_size1_no_match(self):
            assert _key_match_page_size1([1, 2], [3, 4]) == 0

        def test_page_size1_empty(self):
            assert _key_match_page_size1([], [1, 2]) == 0

        def test_paged_full_match(self):
            assert _key_match_paged([1, 2, 3, 4], [1, 2, 3, 4], 2) == 4

        def test_paged_partial_match(self):
            assert _key_match_paged([1, 2, 3, 4], [1, 2, 5, 6], 2) == 2

        def test_paged_no_match(self):
            assert _key_match_paged([1, 2], [3, 4], 2) == 0

    # ======================================================================
    # RadixCache lifecycle tests
    # ======================================================================

    class TestRadixCache:
        @pytest.fixture
        def cache(self):
            return RadixCache(
                num_kv_heads=2,
                head_dim=4,
                num_layers=2,
                dtype=mx.float16,
                page_size=1,
                max_num_tokens=100,
            )

        def test_reset_clears_tree(self, cache):
            cache.req_to_token["r1"] = [1, 2, 3]
            cache.reset()
            assert len(cache.req_to_token) == 0
            assert cache.evictable_size_ == 0
            assert cache.protected_size_ == 0

        def test_total_size_empty(self, cache):
            assert cache.total_size() == 0

        def test_update_req_to_token_new(self, cache):
            cache.update_req_to_token("r1", [10, 20])
            assert cache.req_to_token["r1"] == [10, 20]

        def test_update_req_to_token_append(self, cache):
            cache.update_req_to_token("r1", [10, 20])
            cache.update_req_to_token("r1", [30])
            assert cache.req_to_token["r1"] == [10, 20, 30]

        def test_evict_request(self, cache):
            cache.req_to_token["r1"] = [1, 2]
            cache.evict_request("r1")
            assert "r1" not in cache.req_to_token

        def test_match_prefix_empty_key(self, cache):
            value, node = cache.match_prefix([])
            assert value == []
            assert node is cache.root_node

        def test_insert_and_total_size(self, cache):
            key = [1, 2, 3]
            # Create dummy k/v caches: shape (num_layers, num_kv_heads, seq_len, head_dim)
            k = mx.zeros((2, 2, 3, 4))
            v = mx.zeros((2, 2, 3, 4))
            cache.insert(key, None, k, v)
            assert cache.total_size() == 3

        def test_insert_overlapping_prefix(self, cache):
            k = mx.zeros((2, 2, 3, 4))
            v = mx.zeros((2, 2, 3, 4))
            cache.insert([1, 2, 3], None, k, v)

            k2 = mx.zeros((2, 2, 5, 4))
            v2 = mx.zeros((2, 2, 5, 4))
            cache.insert([1, 2, 3, 4, 5], None, k2, v2)
            # Should have 5 tokens total (3 from shared prefix + 2 new)
            assert cache.total_size() == 5

        def test_match_prefix_finds_existing(self, cache):
            k = mx.zeros((2, 2, 3, 4))
            v = mx.zeros((2, 2, 3, 4))
            cache.insert([1, 2, 3], None, k, v)
            value, node = cache.match_prefix([1, 2, 3, 4, 5])
            assert len(value) == 3

        def test_increase_decrease_lock_ref(self, cache):
            k = mx.zeros((2, 2, 3, 4))
            v = mx.zeros((2, 2, 3, 4))
            _, node = cache.insert([1, 2, 3], None, k, v)
            # Initially evictable
            initial_evictable = cache.evictable_size_
            cache.increase_lock_ref(node)
            assert cache.protected_size_ > 0
            assert cache.evictable_size_ < initial_evictable
            cache.decrease_lock_ref(node)
            assert cache.evictable_size_ == initial_evictable

        def test_evict_reduces_size(self, cache):
            k = mx.zeros((2, 2, 3, 4))
            v = mx.zeros((2, 2, 3, 4))
            cache.insert([1, 2, 3], None, k, v)
            cache.insert([4, 5, 6], None, k, v)
            initial = cache.total_size()
            cache.evict(3)
            assert cache.total_size() < initial
