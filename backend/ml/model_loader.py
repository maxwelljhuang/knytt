"""
Model Loader
Singleton registry for loading and caching ML models (CLIP/SigLIP).
Handles lazy loading, device management, and provides encoding APIs.
"""

import logging
import time
from typing import Optional, List, Union, Tuple
from pathlib import Path
import numpy as np
from PIL import Image

from .config import get_ml_config, TORCH_AVAILABLE

# Only import ML libraries if available
if TORCH_AVAILABLE:
    import torch
    import open_clip
    from open_clip import tokenize
else:
    torch = None
    open_clip = None
    tokenize = None

logger = logging.getLogger(__name__)


class ModelNotAvailableError(Exception):
    """Raised when trying to use models without ML dependencies installed."""

    pass


class ModelRegistry:
    """
    Singleton registry for ML models.

    Provides:
    - Lazy loading of CLIP/SigLIP models
    - In-memory caching (models loaded once per process)
    - Device management (CPU/GPU/MPS)
    - Encoding APIs for images and text

    Usage:
        registry = ModelRegistry()
        image_emb = registry.encode_image(image)
        text_emb = registry.encode_text("vintage dress")
    """

    _instance: Optional["ModelRegistry"] = None
    _models: dict = {}
    _config = None

    def __new__(cls):
        """Singleton pattern - only one instance per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize registry (only runs once due to singleton)."""
        if self._initialized:
            return

        if not TORCH_AVAILABLE:
            logger.warning(
                "PyTorch not available. Install ML dependencies with: "
                "pip install -r requirements-ml.txt"
            )

        self._config = get_ml_config()
        self._device = self._config.model.device
        self._initialized = True

        logger.info(f"ModelRegistry initialized (device: {self._device})")

    def _check_ml_available(self):
        """Raise error if ML libraries not installed."""
        if not TORCH_AVAILABLE:
            raise ModelNotAvailableError(
                "ML dependencies not installed. Run: pip install -r requirements-ml.txt"
            )

    def get_clip_model(self) -> Tuple:
        """
        Load CLIP/SigLIP model (cached).

        Returns:
            Tuple of (model, preprocess_fn)

        Raises:
            ModelNotAvailableError: If ML dependencies not installed
        """
        self._check_ml_available()

        if "clip" not in self._models:
            logger.info(
                f"Loading CLIP model: {self._config.model.clip_model} "
                f"({self._config.model.clip_pretrained})"
            )
            start_time = time.time()

            # Load model
            model, _, preprocess = open_clip.create_model_and_transforms(
                self._config.model.clip_model,
                pretrained=self._config.model.clip_pretrained,
                cache_dir=str(self._config.model.clip_cache_path),
            )

            # Move to device
            model = model.to(self._device)
            model.eval()  # Set to inference mode

            # Enable mixed precision if configured (GPU only)
            if self._config.model.use_fp16 and self._device != "cpu":
                model = model.half()
                logger.info("Enabled FP16 mixed precision")

            # Cache the model
            self._models["clip"] = model
            self._models["clip_preprocess"] = preprocess

            load_time = time.time() - start_time
            logger.info(f"CLIP model loaded successfully in {load_time:.2f}s")

        return self._models["clip"], self._models["clip_preprocess"]

    def encode_image(self, image: Image.Image) -> np.ndarray:
        """
        Encode a single image to embedding vector.

        Args:
            image: PIL Image object

        Returns:
            Normalized embedding vector (shape: [embedding_dim])

        Example:
            >>> from PIL import Image
            >>> image = Image.open("product.jpg")
            >>> embedding = registry.encode_image(image)
            >>> embedding.shape
            (512,)
        """
        self._check_ml_available()

        model, preprocess = self.get_clip_model()

        # Preprocess image
        image_tensor = preprocess(image).unsqueeze(0).to(self._device)

        # Handle FP16
        if self._config.model.use_fp16 and self._device != "cpu":
            image_tensor = image_tensor.half()

        # Encode
        with torch.no_grad():
            embedding = model.encode_image(image_tensor)

            # Normalize if configured
            if self._config.embedding.normalize_embeddings:
                embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        # Convert to numpy
        return embedding.cpu().float().numpy()[0]

    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text using CLIP text encoder.

        Args:
            text: Text string to encode

        Returns:
            Normalized embedding vector (shape: [embedding_dim])

        Example:
            >>> embedding = registry.encode_text("vintage floral dress")
            >>> embedding.shape
            (512,)
        """
        self._check_ml_available()

        model, _ = self.get_clip_model()

        # Tokenize text
        text_tokens = tokenize([text]).to(self._device)

        # Encode
        with torch.no_grad():
            embedding = model.encode_text(text_tokens)

            # Normalize if configured
            if self._config.embedding.normalize_embeddings:
                embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        # Convert to numpy
        return embedding.cpu().float().numpy()[0]

    def encode_image_batch(self, images: List[Image.Image]) -> np.ndarray:
        """
        Batch encode multiple images for efficiency.

        Args:
            images: List of PIL Image objects

        Returns:
            Batch of normalized embeddings (shape: [batch_size, embedding_dim])

        Example:
            >>> images = [Image.open(f"product_{i}.jpg") for i in range(10)]
            >>> embeddings = registry.encode_image_batch(images)
            >>> embeddings.shape
            (10, 512)
        """
        self._check_ml_available()

        if not images:
            return np.array([])

        model, preprocess = self.get_clip_model()

        # Preprocess all images
        image_tensors = torch.stack([preprocess(img) for img in images]).to(self._device)

        # Handle FP16
        if self._config.model.use_fp16 and self._device != "cpu":
            image_tensors = image_tensors.half()

        # Encode in batch
        with torch.no_grad():
            embeddings = model.encode_image(image_tensors)

            # Normalize if configured
            if self._config.embedding.normalize_embeddings:
                embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

        # Convert to numpy
        return embeddings.cpu().float().numpy()

    def encode_text_batch(self, texts: List[str]) -> np.ndarray:
        """
        Batch encode multiple text strings.

        Args:
            texts: List of text strings

        Returns:
            Batch of normalized embeddings (shape: [batch_size, embedding_dim])

        Example:
            >>> texts = ["dress", "shirt", "pants"]
            >>> embeddings = registry.encode_text_batch(texts)
            >>> embeddings.shape
            (3, 512)
        """
        self._check_ml_available()

        if not texts:
            return np.array([])

        model, _ = self.get_clip_model()

        # Tokenize all texts
        text_tokens = tokenize(texts).to(self._device)

        # Encode in batch
        with torch.no_grad():
            embeddings = model.encode_text(text_tokens)

            # Normalize if configured
            if self._config.embedding.normalize_embeddings:
                embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

        # Convert to numpy
        return embeddings.cpu().float().numpy()

    def get_embedding_dim(self) -> int:
        """Get the embedding dimension of the loaded model."""
        return self._config.embedding.image_embedding_dim

    def get_device(self) -> str:
        """Get the current device (cpu/cuda/mps)."""
        return self._device

    def is_loaded(self) -> bool:
        """Check if CLIP model is currently loaded in memory."""
        return "clip" in self._models

    def unload_models(self):
        """
        Unload models from memory (useful for freeing GPU memory).
        Models will be reloaded on next use.
        """
        if self._models:
            logger.info("Unloading models from memory")
            self._models.clear()

            # Clear CUDA cache if using GPU
            if TORCH_AVAILABLE and self._device != "cpu":
                torch.cuda.empty_cache()

    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.

        Returns:
            Dict with model configuration and status
        """
        return {
            "model_name": self._config.model.clip_model,
            "pretrained": self._config.model.clip_pretrained,
            "device": self._device,
            "fp16": self._config.model.use_fp16,
            "embedding_dim": self.get_embedding_dim(),
            "is_loaded": self.is_loaded(),
            "torch_available": TORCH_AVAILABLE,
        }


# Global singleton instance
model_registry = ModelRegistry()


# Convenience functions for direct access
def encode_image(image: Image.Image) -> np.ndarray:
    """Encode image using global model registry."""
    return model_registry.encode_image(image)


def encode_text(text: str) -> np.ndarray:
    """Encode text using global model registry."""
    return model_registry.encode_text(text)


def encode_image_batch(images: List[Image.Image]) -> np.ndarray:
    """Batch encode images using global model registry."""
    return model_registry.encode_image_batch(images)


def encode_text_batch(texts: List[str]) -> np.ndarray:
    """Batch encode texts using global model registry."""
    return model_registry.encode_text_batch(texts)
