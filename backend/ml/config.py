"""
ML Configuration
Centralized configuration for embedding generation, model loading, and user modeling.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal, Optional
from enum import Enum

# Optional torch import (only needed when actually using models)
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

    # Create a mock torch module for configuration
    class _MockTorch:
        class cuda:
            @staticmethod
            def is_available():
                return False

    torch = _MockTorch()


class ModelType(Enum):
    """Supported embedding model types."""

    CLIP_VIT_B32 = "ViT-B-32"
    CLIP_VIT_L14 = "ViT-L-14"
    SIGLIP_BASE = "ViT-B-16-SigLIP"
    SIGLIP_LARGE = "ViT-L-16-SigLIP"


class PretrainedSource(Enum):
    """Pretrained model sources."""

    OPENAI = "openai"
    LAION400M = "laion400m_e32"
    LAION2B = "laion2b_s34b_b79k"
    WEBLI = "webli"  # SigLIP


@dataclass
class ModelConfig:
    """Model selection and loading configuration."""

    # CLIP/SigLIP model selection
    clip_model: str = ModelType.CLIP_VIT_B32.value
    clip_pretrained: str = PretrainedSource.OPENAI.value

    # For SigLIP, use:
    # clip_model = ModelType.SIGLIP_BASE.value
    # clip_pretrained = PretrainedSource.WEBLI.value

    # Model cache directory
    model_cache_dir: Path = field(default_factory=lambda: Path("models/cache"))
    clip_cache_path: Path = field(default_factory=lambda: Path("models/cache/clip"))

    # Device configuration
    device: str = field(default_factory=lambda: "cuda" if torch.cuda.is_available() else "cpu")

    # Use mixed precision for faster inference (GPU only)
    use_fp16: bool = field(default_factory=lambda: torch.cuda.is_available())

    def __post_init__(self):
        """Ensure cache directories exist."""
        self.model_cache_dir = Path(self.model_cache_dir)
        self.clip_cache_path = Path(self.clip_cache_path)
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)
        self.clip_cache_path.mkdir(parents=True, exist_ok=True)


@dataclass
class EmbeddingConfig:
    """Embedding generation and fusion configuration."""

    # Embedding dimensions
    image_embedding_dim: int = 512
    text_embedding_dim: int = 512
    product_embedding_dim: int = 512  # Fused embedding dimension

    # Fusion strategy: 'weighted_average' | 'concatenate' | 'late_fusion'
    fusion_strategy: Literal["weighted_average", "concatenate", "late_fusion"] = "weighted_average"

    # Fusion weights (for weighted_average strategy)
    image_weight: float = 0.7  # Fashion is visual-first
    text_weight: float = 0.3

    # Ensure weights sum to 1.0
    def __post_init__(self):
        if self.fusion_strategy == "weighted_average":
            total = self.image_weight + self.text_weight
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"Fusion weights must sum to 1.0, got {total}")

    # Normalization
    normalize_embeddings: bool = True  # L2 normalization (required for cosine similarity)

    # Batch processing
    embedding_batch_size: int = 32
    max_workers: int = 4  # Parallel image downloads
    image_download_timeout: int = 10  # seconds

    # Image preprocessing
    max_image_size: int = 512  # Resize large images to save memory
    image_formats: list = field(default_factory=lambda: ["jpg", "jpeg", "png", "webp", "heic"])


@dataclass
class UserModelingConfig:
    """User embedding and personalization configuration."""

    # User embedding dimensions (must match product embeddings)
    user_embedding_dim: int = 512

    # Long-term vs session blending
    long_term_alpha: float = 0.7  # Weight for long-term taste profile
    session_alpha: float = 0.3  # Weight for current session intent

    def __post_init__(self):
        total = self.long_term_alpha + self.session_alpha
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"User blending weights must sum to 1.0, got {total}")

    # Session configuration
    session_window_size: int = 10  # Last N interactions for session embedding
    session_timeout_minutes: int = 30  # Clear session after inactivity

    # EWMA (Exponentially Weighted Moving Average) for long-term updates
    ewma_alpha: float = 0.95  # Higher = slower drift, emphasizes history

    # Cold-start configuration
    min_quiz_selections: int = 3  # Minimum moodboard selections for onboarding
    max_quiz_selections: int = 5  # Maximum selections

    # Exploration vs exploitation
    exploration_epsilon: float = 0.1  # 10% random exploration in recommendations
    diversity_weight: float = 0.15  # Weight for diversity in ranking


@dataclass
class StorageConfig:
    """Vector storage and indexing configuration."""

    # Primary storage (Postgres with pgvector)
    use_pgvector: bool = True
    pgvector_index_type: Literal["ivfflat", "hnsw"] = "ivfflat"
    ivfflat_lists: int = 100  # Number of lists for IVFFlat index

    # FAISS configuration
    use_faiss: bool = True
    faiss_index_type: Literal["Flat", "IVF", "HNSW"] = "Flat"  # Start simple for MVP
    faiss_index_path: Path = field(default_factory=lambda: Path("models/cache/faiss_index"))

    # FAISS build configuration
    faiss_nprobe: int = 10  # Number of clusters to visit during search (IVF only)
    faiss_ef_search: int = 64  # Search depth for HNSW

    # Rebuild schedule
    rebuild_index_interval_hours: int = 6  # Rebuild FAISS index every 6 hours

    # Redis configuration for user embeddings
    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "redis"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    redis_db: int = 1  # Separate DB for embeddings
    redis_ttl_hours: int = 24  # Cache user embeddings for 24 hours

    def __post_init__(self):
        """Ensure FAISS index directory exists."""
        self.faiss_index_path = Path(self.faiss_index_path)
        self.faiss_index_path.mkdir(parents=True, exist_ok=True)


@dataclass
class PerformanceConfig:
    """Performance and optimization settings."""

    # Batch sizes for different operations
    embedding_generation_batch_size: int = 32
    search_batch_size: int = 100

    # Retrieval configuration
    candidate_retrieval_k: int = 500  # Initial candidates from FAISS
    final_results_k: int = 50  # Final results after filtering/ranking

    # Caching
    cache_hot_embeddings: bool = True
    hot_user_threshold: int = 10000  # Cache top 10k active users in Redis

    # Model optimization
    use_torch_compile: bool = False  # PyTorch 2.0+ compilation (experimental)
    use_onnx: bool = False  # Export to ONNX for faster inference (post-MVP)

    # Monitoring
    log_embedding_time: bool = True
    latency_target_ms: int = 300  # Target p95 latency for /recommend and /search


@dataclass
class MLConfig:
    """Top-level ML configuration combining all sub-configs."""

    model: ModelConfig = field(default_factory=ModelConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    user_modeling: UserModelingConfig = field(default_factory=UserModelingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    # Model versioning (for tracking embedding re-generation)
    model_version: str = "v1.0-clip-vit-b32"

    @classmethod
    def from_env(cls) -> "MLConfig":
        """Load configuration from environment variables."""
        config = cls()

        # Override with environment variables if present
        if clip_model := os.getenv("CLIP_MODEL"):
            config.model.clip_model = clip_model

        if clip_pretrained := os.getenv("CLIP_PRETRAINED"):
            config.model.clip_pretrained = clip_pretrained

        if device := os.getenv("ML_DEVICE"):
            config.model.device = device

        if batch_size := os.getenv("EMBEDDING_BATCH_SIZE"):
            config.embedding.embedding_batch_size = int(batch_size)

        return config

    def validate(self) -> None:
        """Validate configuration consistency."""
        # Ensure dimensions match
        assert (
            self.embedding.product_embedding_dim == self.user_modeling.user_embedding_dim
        ), "Product and user embedding dimensions must match"

        # Ensure fusion weights are valid
        if self.embedding.fusion_strategy == "weighted_average":
            assert 0 <= self.embedding.image_weight <= 1, "Image weight must be in [0, 1]"
            assert 0 <= self.embedding.text_weight <= 1, "Text weight must be in [0, 1]"

        # Ensure retrieval k values make sense
        assert (
            self.performance.candidate_retrieval_k >= self.performance.final_results_k
        ), "Candidate K must be >= final K"


# Global configuration instance
_global_config: Optional[MLConfig] = None


def get_ml_config() -> MLConfig:
    """Get global ML configuration (singleton pattern)."""
    global _global_config
    if _global_config is None:
        _global_config = MLConfig.from_env()
        _global_config.validate()
    return _global_config


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _global_config
    _global_config = None


# Convenience exports for quick access
ml_config = get_ml_config()
