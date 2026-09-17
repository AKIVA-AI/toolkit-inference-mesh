"""
Tests for the radix tree.
"""

import mlx.core as mx
import pytest

from parallax.server.radix_cache import RadixCache

DATA_TYPE = mx.bfloat16


def _make_tree(max_num_tokens: int = 10000) -> RadixCache:
    return RadixCache(
        num_kv_heads=1,
        head_dim=4,
        num_layers=10,
        dtype=DATA_TYPE,
        page_size=1,
        max_num_tokens=max_num_tokens,
    )


@pytest.fixture
def tree() -> RadixCache:
    return _make_tree()


@pytest.fixture
def kv(tree) -> mx.array:
    return mx.zeros([tree.num_layers, tree.num_kv_heads, 1, tree.head_dim], dtype=DATA_TYPE)


def _total_size(tree: RadixCache) -> int:
    return tree._total_size_helper()


def test_insert_and_match_prefix(tree, kv):
    tree.insert("Hello", None, kv, kv)
    value, last_node = tree.match_prefix("Hello")
    # The full key should be matched
    assert len(value) == len("Hello")
    assert last_node is not tree.root_node


def test_match_prefix_returns_longest_match(tree, kv):
    tree.insert("Hello", None, kv, kv)
    tree.insert("Hello_L.A.!", None, kv, kv)
    # Query a key that extends beyond any inserted key: matches the longest prefix
    value, _ = tree.match_prefix("Hello_L.A.! extra tokens here")
    assert len(value) >= len("Hello_L.A.!")


def test_shared_prefix_does_not_double_count(tree, kv):
    tree.insert("Hello", None, kv, kv)
    tree.insert("Hello", None, kv, kv)
    # Inserting the same key twice should not duplicate stored tokens
    tree2 = _make_tree()
    tree2.insert("Hello", None, kv, kv)
    assert _total_size(tree) == _total_size(tree2)


def test_no_match_returns_empty(tree, kv):
    tree.insert("Hello", None, kv, kv)
    value, last_node = tree.match_prefix("completely different")
    assert len(value) == 0
    assert last_node is tree.root_node


def test_evict_reduces_size(tree, kv):
    tree.insert("Hello", None, kv, kv)
    tree.insert("Hello_L.A.!", None, kv, kv)
    tree.insert("Hello_world! Happy", None, kv, kv)
    tree.insert("I love you!", None, kv, kv)
    size_before = _total_size(tree)
    tree.evict(5)
    size_after = _total_size(tree)
    assert size_after < size_before


def test_match_prefix_after_insert_is_consistent(tree, kv):
    tree.insert("I love you!", None, kv, kv)
    value, last_node = tree.match_prefix("I love you! aha")
    # Should match the full inserted prefix "I love you!"
    assert len(value) == len("I love you!")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

