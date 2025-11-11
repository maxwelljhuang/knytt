#!/usr/bin/env python3
"""
Test ML Setup - Step 1.3
Verifies that model loading utilities work correctly.

Usage:
    python -m backend.ml.test_setup

Note: Requires ML dependencies installed (pip install -r requirements-ml.txt)
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ml.config import get_ml_config, TORCH_AVAILABLE
from backend.ml.model_loader import (
    model_registry,
    ModelNotAvailableError,
)

# Only import if available
if TORCH_AVAILABLE:
    from PIL import Image
    import requests
    from io import BytesIO
    import numpy as np


def check_dependencies():
    """Check if ML dependencies are installed."""
    print("Checking ML dependencies...")

    if not TORCH_AVAILABLE:
        print("❌ ML dependencies not installed")
        print()
        print("Please install with:")
        print("  pip install -r requirements-ml.txt")
        print()
        print("For installation help, see: ML_SETUP.md")
        return False

    # Check individual imports
    try:
        import torch

        print(f"✓ PyTorch {torch.__version__}")

        import open_clip

        print(f"✓ OpenCLIP installed")

        import PIL

        print(f"✓ Pillow {PIL.__version__}")

        import numpy

        print(f"✓ NumPy {numpy.__version__}")

        # Check device
        cuda_available = torch.cuda.is_available()
        mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()

        if cuda_available:
            print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
        elif mps_available:
            print(f"✓ MPS (Apple Silicon) available")
        else:
            print(f"ℹ Using CPU (no GPU acceleration)")

        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_model_registry_init():
    """Test that model registry initializes correctly."""
    print("\nTesting model registry initialization...")

    try:
        # Get registry info without loading models
        info = model_registry.get_model_info()

        print(f"✓ Registry initialized")
        print(f"  - Device: {info['device']}")
        print(f"  - Model: {info['model_name']}")
        print(f"  - Pretrained: {info['pretrained']}")
        print(f"  - Embedding dim: {info['embedding_dim']}")
        print(f"  - Is loaded: {info['is_loaded']}")

        return True
    except Exception as e:
        print(f"❌ Registry init failed: {e}")
        return False


def test_model_loading():
    """Test CLIP model loading."""
    print("\nTesting CLIP model loading...")
    print("(This will download ~500MB on first run, please wait...)")

    try:
        start_time = time.time()

        model, preprocess = model_registry.get_clip_model()

        load_time = time.time() - start_time

        print(f"✓ Model loaded in {load_time:.2f}s")
        print(f"  - Model is now cached in memory")

        # Check if loaded
        assert model_registry.is_loaded(), "Model should be loaded"
        print(f"✓ Model is loaded: {model_registry.is_loaded()}")

        return True
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_image_encoding():
    """Test image encoding."""
    print("\nTesting image encoding...")
    print("(Downloading sample image...)")

    try:
        # Download a sample image
        url = "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=400"
        response = requests.get(url, timeout=10)
        image = Image.open(BytesIO(response.content))

        print(f"✓ Sample image loaded: {image.size}")

        # Encode image
        start_time = time.time()
        embedding = model_registry.encode_image(image)
        encode_time = (time.time() - start_time) * 1000  # Convert to ms

        print(f"✓ Image encoded in {encode_time:.1f}ms")
        print(f"  - Embedding shape: {embedding.shape}")
        print(f"  - Embedding dtype: {embedding.dtype}")
        print(f"  - Embedding norm: {np.linalg.norm(embedding):.4f}")

        # Check shape
        config = get_ml_config()
        expected_dim = config.embedding.image_embedding_dim
        assert embedding.shape == (
            expected_dim,
        ), f"Expected shape ({expected_dim},), got {embedding.shape}"

        # Check normalization
        if config.embedding.normalize_embeddings:
            norm = np.linalg.norm(embedding)
            assert (
                abs(norm - 1.0) < 0.01
            ), f"Expected normalized embedding (norm=1.0), got {norm:.4f}"
            print(f"✓ Embedding is normalized (norm ≈ 1.0)")

        return True
    except Exception as e:
        print(f"❌ Image encoding failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_text_encoding():
    """Test text encoding."""
    print("\nTesting text encoding...")

    try:
        # Test queries
        queries = ["vintage floral dress", "minimalist black shoes", "bohemian style jacket"]

        print(f"Testing {len(queries)} text queries...")

        for query in queries:
            start_time = time.time()
            embedding = model_registry.encode_text(query)
            encode_time = (time.time() - start_time) * 1000

            print(f"  • '{query}': {encode_time:.1f}ms")

        # Check last embedding
        config = get_ml_config()
        expected_dim = config.embedding.text_embedding_dim
        assert embedding.shape == (
            expected_dim,
        ), f"Expected shape ({expected_dim},), got {embedding.shape}"

        print(f"✓ All text queries encoded successfully")
        print(f"  - Embedding shape: {embedding.shape}")
        print(f"  - Embedding norm: {np.linalg.norm(embedding):.4f}")

        return True
    except Exception as e:
        print(f"❌ Text encoding failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_batch_encoding():
    """Test batch encoding for efficiency."""
    print("\nTesting batch encoding...")

    try:
        # Test batch text encoding
        texts = ["red dress", "blue shirt", "green pants", "yellow jacket", "purple shoes"]

        start_time = time.time()
        embeddings = model_registry.encode_text_batch(texts)
        batch_time = (time.time() - start_time) * 1000

        print(f"✓ Batch encoded {len(texts)} texts in {batch_time:.1f}ms")
        print(f"  - Per item: {batch_time/len(texts):.1f}ms")
        print(f"  - Batch shape: {embeddings.shape}")

        # Test that batch is faster than sequential
        start_time = time.time()
        for text in texts:
            _ = model_registry.encode_text(text)
        sequential_time = (time.time() - start_time) * 1000

        speedup = sequential_time / batch_time
        print(f"  - Speedup vs sequential: {speedup:.2f}x")

        return True
    except Exception as e:
        print(f"❌ Batch encoding failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_similarity():
    """Test that similar items have high cosine similarity."""
    print("\nTesting semantic similarity...")

    try:
        # Encode related texts
        dress_1 = model_registry.encode_text("vintage floral dress")
        dress_2 = model_registry.encode_text("retro flower pattern dress")
        shirt = model_registry.encode_text("casual t-shirt")

        # Compute cosine similarity
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_dress = cosine_sim(dress_1, dress_2)
        sim_different = cosine_sim(dress_1, shirt)

        print(f"✓ Similarity computed:")
        print(f"  - 'vintage floral dress' vs 'retro flower dress': {sim_dress:.4f}")
        print(f"  - 'vintage floral dress' vs 'casual t-shirt': {sim_different:.4f}")

        # Similar items should have higher similarity
        assert sim_dress > sim_different, "Similar items should have higher similarity"
        print(f"✓ Semantic similarity works correctly")

        return True
    except Exception as e:
        print(f"❌ Similarity test failed: {e}")
        return False


def main():
    """Run all setup tests."""
    print("=" * 60)
    print("  ML Setup Test Suite - Step 1.3")
    print("=" * 60)

    # Check dependencies first
    if not check_dependencies():
        print("\n" + "=" * 60)
        print("Please install ML dependencies and try again.")
        print("=" * 60)
        return 1

    tests = [
        ("Registry Initialization", test_model_registry_init),
        ("Model Loading", test_model_loading),
        ("Image Encoding", test_image_encoding),
        ("Text Encoding", test_text_encoding),
        ("Batch Encoding", test_batch_encoding),
        ("Semantic Similarity", test_similarity),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n⚠  {test_name} had issues")
        except ModelNotAvailableError:
            print(f"\n⚠  {test_name} skipped (ML dependencies not installed)")
            failed += 1
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    if failed == 0:
        print("✅ All tests passed!")
        print("=" * 60)
        print(f"Tests passed: {passed}/{len(tests)}")
        print()
        print("Next steps:")
        print("1. Proceed to Step 1.4: Add Database Columns")
        print("2. Or continue to Step 2: Product Embedding Generation")
        print("=" * 60)
        return 0
    else:
        print(f"❌ Some tests failed")
        print("=" * 60)
        print(f"Tests passed: {passed}/{len(tests)}")
        print(f"Tests failed: {failed}/{len(tests)}")
        print()
        print("Check the errors above and:")
        print("1. Verify ML dependencies are installed")
        print("2. Check internet connection (for model download)")
        print("3. See ML_SETUP.md for troubleshooting")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
