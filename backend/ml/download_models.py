#!/usr/bin/env python3
"""
Download ML Models
Pre-download models to cache directory to avoid slow first run.

Usage:
    python -m backend.ml.download_models
    python -m backend.ml.download_models --model ViT-L-14
"""

import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ml.config import get_ml_config, TORCH_AVAILABLE

if not TORCH_AVAILABLE:
    print("❌ PyTorch not installed. Please run:")
    print("   pip install -r requirements-ml.txt")
    sys.exit(1)

import open_clip


def download_clip_model(model_name: str = None, pretrained: str = None):
    """
    Download CLIP model to cache directory.

    Args:
        model_name: CLIP model name (e.g., 'ViT-B-32', 'ViT-L-14')
        pretrained: Pretrained source (e.g., 'openai', 'laion2b_s34b_b79k')
    """
    config = get_ml_config()

    # Use config defaults if not specified
    model_name = model_name or config.model.clip_model
    pretrained = pretrained or config.model.clip_pretrained

    print("=" * 60)
    print("  CLIP Model Download")
    print("=" * 60)
    print(f"Model: {model_name}")
    print(f"Pretrained: {pretrained}")
    print(f"Cache directory: {config.model.clip_cache_path}")
    print()

    # Check if model is already cached
    cache_path = config.model.clip_cache_path
    if cache_path.exists() and list(cache_path.glob("*")):
        print(f"ℹ  Cache directory already contains files")
        response = input("Download anyway? [y/N]: ")
        if response.lower() != "y":
            print("Skipping download")
            return

    print("Downloading model (this may take 2-5 minutes)...")
    print()

    try:
        # Download model
        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, cache_dir=str(cache_path)
        )

        print()
        print("✅ Model downloaded successfully!")
        print(f"   Cached at: {cache_path}")
        print()

        # Print model info
        param_count = sum(p.numel() for p in model.parameters())
        print("Model Information:")
        print(f"  - Parameters: {param_count:,}")
        print(f"  - Embedding dim: {model.visual.output_dim}")
        print(f"  - Device: {config.model.device}")
        print()

        # Verify model works
        print("Verifying model...")
        import torch
        from PIL import Image
        import requests
        from io import BytesIO

        # Test with a sample image
        try:
            url = "https://images.unsplash.com/photo-1434389677669-e08b4cac3105"
            response = requests.get(url, timeout=10)
            image = Image.open(BytesIO(response.content))

            model.eval()
            with torch.no_grad():
                image_tensor = preprocess(image).unsqueeze(0)
                embedding = model.encode_image(image_tensor)
                text_tokens = open_clip.tokenize(["a photo of a dress"])
                text_embedding = model.encode_text(text_tokens)

            print("✓ Image encoding works")
            print("✓ Text encoding works")
            print(f"✓ Embedding shape: {tuple(embedding.shape)}")

        except Exception as e:
            print(f"⚠  Verification warning: {e}")
            print("  (Model downloaded but verification failed)")

        print()
        print("=" * 60)
        print("Next steps:")
        print("1. Run: python -m backend.ml.test_setup")
        print("2. Proceed to Step 2: Product Embedding Generation")
        print("=" * 60)

    except Exception as e:
        print()
        print(f"❌ Download failed: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check internet connection")
        print("2. Verify model name and pretrained source")
        print("3. Try a different model:")
        print("   python -m backend.ml.download_models --model ViT-B-32 --pretrained openai")
        sys.exit(1)


def list_available_models():
    """List available CLIP models."""
    print("=" * 60)
    print("  Available CLIP Models")
    print("=" * 60)
    print()

    models = open_clip.list_pretrained()

    # Group by architecture
    architectures = {}
    for model_name, pretrained in models:
        if model_name not in architectures:
            architectures[model_name] = []
        architectures[model_name].append(pretrained)

    # Print recommended models
    print("Recommended for GreenThumb MVP:")
    print()
    recommended = [
        ("ViT-B-32", "openai", "Default, well-tested (512-dim, ~500MB)"),
        ("ViT-B-16-SigLIP", "webli", "Better for products (512-dim, ~700MB)"),
        ("ViT-L-14", "openai", "Higher quality (768-dim, ~900MB)"),
    ]

    for model, pretrained, description in recommended:
        if model in architectures:
            print(f"  • {model} ({pretrained})")
            print(f"    {description}")
            print()

    print()
    print("To download a specific model:")
    print("  python -m backend.ml.download_models --model ViT-B-32 --pretrained openai")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Download CLIP models for GreenThumb")
    parser.add_argument("--model", type=str, help="Model name (e.g., ViT-B-32, ViT-L-14)")
    parser.add_argument(
        "--pretrained", type=str, help="Pretrained source (e.g., openai, laion2b_s34b_b79k)"
    )
    parser.add_argument("--list", action="store_true", help="List available models")

    args = parser.parse_args()

    if args.list:
        list_available_models()
    else:
        download_clip_model(args.model, args.pretrained)


if __name__ == "__main__":
    main()
