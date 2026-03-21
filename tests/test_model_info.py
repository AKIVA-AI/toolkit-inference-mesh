"""Tests for scheduling.model_info.ModelInfo.

Covers:
- Property calculations (q_dim, v_dim, k_dim, embedding_io_bytes, etc.)
- FLOPs estimation for decoder layers and LM head
- IO bytes estimation (roofline vs parameter sizing)
- KV cache sizing
- MoE expert activation estimation
- Edge cases: tied embeddings, custom head dims, MoE configs
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scheduling.model_info import ModelInfo


def _base_model(**overrides) -> ModelInfo:
    """Build a baseline dense 12-layer model with sensible defaults."""
    defaults = dict(
        model_name="test-model",
        mlx_model_name="test-mlx",
        head_size=64,
        hidden_dim=2048,
        intermediate_dim=5504,
        num_attention_heads=32,
        num_kv_heads=8,
        vocab_size=32000,
        num_layers=12,
        ffn_num_projections=3,
        param_bytes_per_element=2,
        mlx_param_bytes_per_element=2,
        cache_bytes_per_element=2,
        embedding_bytes_per_element=2,
    )
    defaults.update(overrides)
    return ModelInfo(**defaults)


# ============================================================================
# Basic Property Tests
# ============================================================================


class TestModelInfoProperties:
    """Tests for derived properties of ModelInfo."""

    def test_q_dim(self):
        m = _base_model()
        assert m.q_dim == m.num_attention_heads * m.head_size
        assert m.q_dim == 32 * 64

    def test_v_dim(self):
        m = _base_model()
        assert m.v_dim == m.num_kv_heads * m.head_size_v
        assert m.v_dim == 8 * 64

    def test_k_dim_default(self):
        """Without qk_nope/qk_rope, k_dim equals num_kv_heads * head_size."""
        m = _base_model()
        assert m.k_dim == m.num_kv_heads * m.head_size_k
        assert m.head_size_k == m.head_size

    def test_k_dim_with_rope_and_nope(self):
        """With qk_nope_head_dim + qk_rope_head_dim, head_size_k is their sum."""
        m = _base_model(qk_nope_head_dim=48, qk_rope_head_dim=16)
        assert m.head_size_k == 48 + 16
        assert m.k_dim == m.num_kv_heads * 64

    def test_head_size_v_always_equals_head_size(self):
        m = _base_model()
        assert m.head_size_v == m.head_size

    def test_mlx_bit_factor(self):
        m = _base_model(mlx_param_bytes_per_element=4, param_bytes_per_element=2)
        assert m.mlx_bit_factor == 2.0

    def test_mlx_bit_factor_same(self):
        m = _base_model(mlx_param_bytes_per_element=2, param_bytes_per_element=2)
        assert m.mlx_bit_factor == 1.0

    def test_embedding_io_bytes(self):
        m = _base_model()
        expected = m.embedding_bytes_per_element * m.vocab_size * m.hidden_dim
        assert m.embedding_io_bytes == expected


# ============================================================================
# KV Cache Size Tests
# ============================================================================


class TestKVCacheSize:
    """Tests for KV cache sizing methods."""

    def test_per_token_per_layer_kv_size(self):
        m = _base_model()
        expected = m.cache_bytes_per_element * (m.k_dim + m.v_dim)
        assert m.per_token_per_layer_kv_size == expected

    def test_per_layer_kv_cache_size_defaults(self):
        m = _base_model()
        result = m.per_layer_kv_cache_size()
        expected = m.per_token_per_layer_kv_size * 1 * 256
        assert result == expected

    def test_per_layer_kv_cache_size_custom(self):
        m = _base_model()
        result = m.per_layer_kv_cache_size(batch_size=4, source_seq_len=1024)
        expected = m.per_token_per_layer_kv_size * 4 * 1024
        assert result == expected

    def test_per_layer_kv_cache_size_batch_1_seq_1(self):
        m = _base_model()
        result = m.per_layer_kv_cache_size(batch_size=1, source_seq_len=1)
        assert result == m.per_token_per_layer_kv_size


# ============================================================================
# MoE Expert Activation Tests
# ============================================================================


class TestMoEExperts:
    """Tests for expected_num_activated_experts."""

    def test_none_for_dense_model(self):
        m = _base_model()
        assert m.expected_num_activated_experts() is None

    def test_moe_single_token(self):
        m = _base_model(num_local_experts=8, num_experts_per_tok=2)
        result = m.expected_num_activated_experts(batch_size=1, target_seq_len=1)
        # formula: 8 * (1 - (1 - 2/8)^1) = 8 * (1 - 0.75) = 8 * 0.25 = 2
        assert result == 2

    def test_moe_multiple_tokens(self):
        m = _base_model(num_local_experts=8, num_experts_per_tok=2)
        result = m.expected_num_activated_experts(batch_size=2, target_seq_len=2)
        # num_tokens = 4, formula: 8 * (1 - (1 - 2/8)^4) = 8 * (1 - 0.75^4)
        expected = int(8 * (1 - (1 - 2 / 8) ** 4))
        assert result == expected

    def test_moe_large_batch_approaches_total(self):
        """With many tokens, nearly all experts should be activated."""
        m = _base_model(num_local_experts=16, num_experts_per_tok=2)
        result = m.expected_num_activated_experts(batch_size=100, target_seq_len=100)
        # With 10000 tokens, should be very close to 16
        assert result >= 15


# ============================================================================
# FLOPs Estimation Tests
# ============================================================================


class TestDecoderLayerFlops:
    """Tests for decoder_layer_flops."""

    def test_flops_positive(self):
        m = _base_model()
        flops = m.decoder_layer_flops()
        assert flops > 0

    def test_flops_scale_with_batch_size(self):
        m = _base_model()
        flops_1 = m.decoder_layer_flops(batch_size=1)
        flops_4 = m.decoder_layer_flops(batch_size=4)
        assert flops_4 == 4 * flops_1

    def test_flops_scale_with_target_seq_len(self):
        m = _base_model()
        flops_1 = m.decoder_layer_flops(target_seq_len=1)
        flops_2 = m.decoder_layer_flops(target_seq_len=2)
        # Should roughly double (attention flops dominate and scale with seq len)
        assert flops_2 > flops_1

    def test_flops_with_moe_higher_than_dense(self):
        m_dense = _base_model()
        m_moe = _base_model(num_local_experts=8, num_experts_per_tok=2)
        flops_dense = m_dense.decoder_layer_flops()
        flops_moe = m_moe.decoder_layer_flops()
        assert flops_moe > flops_dense

    def test_lm_head_flops(self):
        m = _base_model()
        flops = m.lm_head_flops(target_seq_len=1)
        expected = 2 * 1 * m.hidden_dim * m.vocab_size
        assert flops == expected

    def test_lm_head_flops_longer_seq(self):
        m = _base_model()
        flops_1 = m.lm_head_flops(target_seq_len=1)
        flops_10 = m.lm_head_flops(target_seq_len=10)
        assert flops_10 == 10 * flops_1


# ============================================================================
# IO Bytes Estimation Tests
# ============================================================================


class TestDecoderLayerIOBytes:
    """Tests for decoder_layer_io_bytes."""

    def test_io_bytes_positive(self):
        m = _base_model()
        io = m.decoder_layer_io_bytes(roofline=True)
        assert io > 0

    def test_io_bytes_param_size_mode(self):
        """When roofline=False, no KV cache size is included."""
        m = _base_model()
        io_param = m.decoder_layer_io_bytes(roofline=False)
        io_roofline = m.decoder_layer_io_bytes(roofline=True)
        # Roofline includes KV cache, so should be >= param-only
        assert io_roofline >= io_param

    def test_io_bytes_moe_roofline_uses_expected_experts(self):
        m = _base_model(num_local_experts=8, num_experts_per_tok=2)
        io = m.decoder_layer_io_bytes(roofline=True)
        assert io > 0

    def test_io_bytes_moe_param_uses_all_experts(self):
        m = _base_model(num_local_experts=8, num_experts_per_tok=2)
        io_param = m.decoder_layer_io_bytes(roofline=False)
        # param mode uses all local experts
        assert io_param > 0

    def test_io_bytes_moe_intermediate_dim_overrides(self):
        m1 = _base_model(
            num_local_experts=8, num_experts_per_tok=2, moe_intermediate_dim=1024
        )
        m2 = _base_model(
            num_local_experts=8, num_experts_per_tok=2, moe_intermediate_dim=4096
        )
        io1 = m1.decoder_layer_io_bytes(roofline=False)
        io2 = m2.decoder_layer_io_bytes(roofline=False)
        assert io2 > io1
