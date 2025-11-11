#!/usr/bin/env python3
"""
Test ML Configuration
Run this to verify Step 1.2 is complete and config is valid.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ml.config import (
    get_ml_config,
    MLConfig,
    ModelType,
    PretrainedSource,
)


def test_config_loading():
    """Test that configuration loads without errors."""
    print("Testing configuration loading...")

    config = get_ml_config()
    assert config is not None, "Config should not be None"

    print("✓ Configuration loaded successfully")
    return config


def test_config_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")

    config = get_ml_config()

    # This should not raise any errors
    config.validate()

    print("✓ Configuration validation passed")


def test_dimension_consistency():
    """Test that all embedding dimensions are consistent."""
    print("\nTesting dimension consistency...")

    config = get_ml_config()

    assert (
        config.embedding.product_embedding_dim == config.user_modeling.user_embedding_dim
    ), "Product and user embedding dims must match"

    assert (
        config.embedding.image_embedding_dim == 512
    ), "Image embedding should be 512-dim for CLIP ViT-B/32"

    assert (
        config.embedding.text_embedding_dim == 512
    ), "Text embedding should be 512-dim for CLIP ViT-B/32"

    print("✓ All dimensions are consistent")


def test_fusion_weights():
    """Test fusion weight configuration."""
    print("\nTesting fusion weights...")

    config = get_ml_config()

    total = config.embedding.image_weight + config.embedding.text_weight
    assert abs(total - 1.0) < 1e-6, f"Fusion weights must sum to 1.0, got {total}"

    print(
        f"✓ Fusion weights valid: image={config.embedding.image_weight}, text={config.embedding.text_weight}"
    )


def test_user_blending_weights():
    """Test user embedding blending weights."""
    print("\nTesting user blending weights...")

    config = get_ml_config()

    total = config.user_modeling.long_term_alpha + config.user_modeling.session_alpha
    assert abs(total - 1.0) < 1e-6, f"User blending weights must sum to 1.0, got {total}"

    print(
        f"✓ User blending weights valid: long_term={config.user_modeling.long_term_alpha}, session={config.user_modeling.session_alpha}"
    )


def test_cache_directories():
    """Test that cache directories were created."""
    print("\nTesting cache directories...")

    config = get_ml_config()

    assert config.model.model_cache_dir.exists(), "Model cache directory should exist"
    assert config.model.clip_cache_path.exists(), "CLIP cache directory should exist"
    assert config.storage.faiss_index_path.exists(), "FAISS index directory should exist"

    print(f"✓ Cache directories exist:")
    print(f"  - Model cache: {config.model.model_cache_dir}")
    print(f"  - CLIP cache: {config.model.clip_cache_path}")
    print(f"  - FAISS index: {config.storage.faiss_index_path}")


def print_config_summary():
    """Print a summary of the current configuration."""
    print("\n" + "=" * 60)
    print("ML Configuration Summary")
    print("=" * 60)

    config = get_ml_config()

    print("\n[Model Configuration]")
    print(f"  CLIP Model: {config.model.clip_model}")
    print(f"  Pretrained: {config.model.clip_pretrained}")
    print(f"  Device: {config.model.device}")
    print(f"  FP16: {config.model.use_fp16}")
    print(f"  Model Version: {config.model_version}")

    print("\n[Embedding Configuration]")
    print(f"  Strategy: {config.embedding.fusion_strategy}")
    print(f"  Image weight: {config.embedding.image_weight}")
    print(f"  Text weight: {config.embedding.text_weight}")
    print(f"  Product dim: {config.embedding.product_embedding_dim}")
    print(f"  Batch size: {config.embedding.embedding_batch_size}")
    print(f"  Normalize: {config.embedding.normalize_embeddings}")

    print("\n[User Modeling Configuration]")
    print(f"  Long-term α: {config.user_modeling.long_term_alpha}")
    print(f"  Session α: {config.user_modeling.session_alpha}")
    print(f"  Session window: {config.user_modeling.session_window_size}")
    print(f"  EWMA α: {config.user_modeling.ewma_alpha}")
    print(f"  Exploration ε: {config.user_modeling.exploration_epsilon}")

    print("\n[Storage Configuration]")
    print(f"  Use pgvector: {config.storage.use_pgvector}")
    print(f"  pgvector index: {config.storage.pgvector_index_type}")
    print(f"  Use FAISS: {config.storage.use_faiss}")
    print(f"  FAISS index type: {config.storage.faiss_index_type}")
    print(f"  Redis: {config.storage.redis_host}:{config.storage.redis_port}")

    print("\n[Performance Configuration]")
    print(f"  Candidate K: {config.performance.candidate_retrieval_k}")
    print(f"  Final K: {config.performance.final_results_k}")
    print(f"  Hot user threshold: {config.performance.hot_user_threshold}")
    print(f"  Latency target: {config.performance.latency_target_ms}ms")

    print("\n" + "=" * 60)


def main():
    """Run all configuration tests."""
    print("=" * 60)
    print("  ML Configuration Test Suite")
    print("=" * 60)

    try:
        config = test_config_loading()
        test_config_validation()
        test_dimension_consistency()
        test_fusion_weights()
        test_user_blending_weights()
        test_cache_directories()

        print("\n" + "=" * 60)
        print("✅ All configuration tests passed!")
        print("=" * 60)

        print_config_summary()

        print("\n" + "=" * 60)
        print("Next Steps:")
        print("1. Proceed to Step 1.3: Model Loading Utilities")
        print("2. Or customize config in backend/ml/.env.ml")
        print("=" * 60)

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Configuration test failed: {e}")
        print("=" * 60)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
