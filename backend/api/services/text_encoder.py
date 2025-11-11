"""
Text Encoder Service
Converts search query text to embeddings using CLIP text encoder.
"""

import logging
import numpy as np
from typing import Optional
import re

from ...ml.model_loader import model_registry
from ...ml.config import get_ml_config, MLConfig

logger = logging.getLogger(__name__)


class TextEncoderService:
    """
    Service for encoding text queries to embeddings.

    Uses CLIP text encoder to convert search queries into vector embeddings
    that can be used for similarity search.
    """

    def __init__(self, config: Optional[MLConfig] = None):
        """
        Initialize text encoder service.

        Args:
            config: ML configuration
        """
        self.config = config or get_ml_config()
        self.model_registry = model_registry

        logger.info("Text encoder service initialized")

    def encode_query(self, query: str) -> np.ndarray:
        """
        Encode search query text to embedding vector.

        Args:
            query: Search query text

        Returns:
            Embedding vector (normalized)

        Raises:
            ValueError: If query is empty or invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Clean and preprocess query
        cleaned_query = self._preprocess_query(query)

        # Encode with CLIP text encoder
        try:
            embedding = self.model_registry.encode_text(cleaned_query)

            logger.debug(
                f"Encoded query: '{cleaned_query[:50]}...' -> "
                f"embedding shape: {embedding.shape}"
            )

            return embedding

        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            raise ValueError(f"Failed to encode query: {e}")

    def encode_batch(self, queries: list[str]) -> np.ndarray:
        """
        Encode multiple queries in batch.

        Args:
            queries: List of search query strings

        Returns:
            Array of embeddings (shape: [num_queries, embedding_dim])
        """
        if not queries:
            raise ValueError("Queries list cannot be empty")

        # Clean queries
        cleaned_queries = [self._preprocess_query(q) for q in queries]

        # Batch encode
        try:
            embeddings = self.model_registry.encode_text_batch(cleaned_queries)

            logger.debug(f"Encoded {len(queries)} queries in batch")

            return embeddings

        except Exception as e:
            logger.error(f"Failed to encode queries batch: {e}")
            raise ValueError(f"Failed to encode queries: {e}")

    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess query text.

        Args:
            query: Raw query text

        Returns:
            Cleaned query text
        """
        # Remove extra whitespace
        query = " ".join(query.split())

        # Remove special characters (keep alphanumeric, spaces, and basic punctuation)
        query = re.sub(r"[^\w\s\-\']", " ", query)

        # Remove extra spaces again
        query = " ".join(query.split())

        # Lowercase for consistency
        query = query.lower()

        # Truncate if too long (CLIP has max token limit)
        max_length = 77  # CLIP's max token length
        words = query.split()
        if len(words) > max_length:
            query = " ".join(words[:max_length])
            logger.warning(f"Query truncated to {max_length} words")

        return query

    def get_embedding_dimension(self) -> int:
        """
        Get embedding vector dimension.

        Returns:
            Embedding dimension
        """
        return self.config.embedding.text_embedding_dim


# Singleton instance
_text_encoder_service: Optional[TextEncoderService] = None


def get_text_encoder_service() -> TextEncoderService:
    """Get global text encoder service instance."""
    global _text_encoder_service
    if _text_encoder_service is None:
        _text_encoder_service = TextEncoderService()
    return _text_encoder_service
