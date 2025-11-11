"""
Similarity Search
k-NN vector similarity search using FAISS with result formatting.
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass, field

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from ..config import get_ml_config, MLConfig
from .index_manager import FAISSIndexManager, get_index_manager

logger = logging.getLogger(__name__)


class SimilaritySearchError(Exception):
    """Exception raised for similarity search errors."""

    pass


@dataclass
class SearchResult:
    """
    Single search result with product information and relevance score.
    """

    product_id: int
    distance: float  # L2 distance from FAISS
    similarity: float  # Converted to [0, 1] similarity score
    rank: int  # Position in results (0-indexed)

    # Optional metadata (populated later)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "product_id": self.product_id,
            "distance": float(self.distance),
            "similarity": float(self.similarity),
            "rank": self.rank,
            "metadata": self.metadata,
        }


@dataclass
class SearchResults:
    """
    Collection of search results with query metadata.
    """

    results: List[SearchResult]
    query_vector_shape: Tuple[int, ...]
    k: int  # Number of results requested
    total_found: int  # Actual number of results found
    search_time_ms: float  # Search latency

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "results": [r.to_dict() for r in self.results],
            "k": self.k,
            "total_found": self.total_found,
            "search_time_ms": float(self.search_time_ms),
        }

    def get_product_ids(self) -> List[int]:
        """Get list of product IDs from results."""
        return [r.product_id for r in self.results]


class SimilaritySearch:
    """
    Performs k-NN similarity search using FAISS.

    Supports:
    - Single vector search
    - Batch vector search
    - Distance-to-similarity conversion
    - Result formatting
    """

    def __init__(
        self, config: Optional[MLConfig] = None, index_manager: Optional[FAISSIndexManager] = None
    ):
        """
        Initialize similarity search.

        Args:
            config: ML configuration
            index_manager: FAISS index manager (uses global instance if not provided)
        """
        self.config = config or get_ml_config()
        self.index_manager = index_manager or get_index_manager()

        logger.info("Similarity search initialized")

    def search(
        self, query_vector: np.ndarray, k: int = 50, min_similarity: Optional[float] = None
    ) -> SearchResults:
        """
        Search for k nearest neighbors of query vector.

        Args:
            query_vector: Query embedding vector (1D array)
            k: Number of nearest neighbors to return
            min_similarity: Optional minimum similarity threshold (0-1)

        Returns:
            SearchResults object with results

        Raises:
            SimilaritySearchError: If search fails
        """
        import time

        start_time = time.time()

        # Validate input
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        elif query_vector.ndim != 2:
            raise SimilaritySearchError(
                f"Query vector must be 1D or 2D, got shape {query_vector.shape}"
            )

        if query_vector.shape[0] != 1:
            raise SimilaritySearchError("Use search_batch() for multiple query vectors")

        # Ensure vector is float32
        query_vector = query_vector.astype(np.float32)

        # Normalize if configured (important for cosine similarity via L2 distance)
        if self.config.embedding.normalize_embeddings:
            query_vector = self._normalize_vector(query_vector)

        # Get FAISS index
        index = self.index_manager.get_index()
        id_mapping = self.index_manager.get_id_mapping()

        # Limit k to available vectors
        max_k = index.ntotal
        if k > max_k:
            logger.warning(f"Requested k={k} but only {max_k} vectors available")
            k = max_k

        # Perform search
        distances, indices = index.search(query_vector, k)

        # Convert to SearchResults
        results = self._format_results(
            distances[0], indices[0], id_mapping, min_similarity=min_similarity
        )

        search_time_ms = (time.time() - start_time) * 1000

        return SearchResults(
            results=results,
            query_vector_shape=query_vector.shape,
            k=k,
            total_found=len(results),
            search_time_ms=search_time_ms,
        )

    def search_batch(
        self, query_vectors: np.ndarray, k: int = 50, min_similarity: Optional[float] = None
    ) -> List[SearchResults]:
        """
        Search for k nearest neighbors for multiple query vectors.

        Args:
            query_vectors: Query embedding vectors (2D array: batch_size x dimension)
            k: Number of nearest neighbors to return per query
            min_similarity: Optional minimum similarity threshold (0-1)

        Returns:
            List of SearchResults, one per query vector

        Raises:
            SimilaritySearchError: If search fails
        """
        import time

        start_time = time.time()

        # Validate input
        if query_vectors.ndim == 1:
            query_vectors = query_vectors.reshape(1, -1)
        elif query_vectors.ndim != 2:
            raise SimilaritySearchError(
                f"Query vectors must be 2D array, got shape {query_vectors.shape}"
            )

        # Ensure vectors are float32
        query_vectors = query_vectors.astype(np.float32)

        # Normalize if configured
        if self.config.embedding.normalize_embeddings:
            query_vectors = self._normalize_vectors(query_vectors)

        # Get FAISS index
        index = self.index_manager.get_index()
        id_mapping = self.index_manager.get_id_mapping()

        # Limit k to available vectors
        max_k = index.ntotal
        if k > max_k:
            logger.warning(f"Requested k={k} but only {max_k} vectors available")
            k = max_k

        # Perform batch search
        distances, indices = index.search(query_vectors, k)

        # Convert to list of SearchResults
        batch_results = []
        for i in range(len(query_vectors)):
            results = self._format_results(
                distances[i], indices[i], id_mapping, min_similarity=min_similarity
            )

            search_time_ms = (time.time() - start_time) * 1000 / len(query_vectors)

            batch_results.append(
                SearchResults(
                    results=results,
                    query_vector_shape=query_vectors[i : i + 1].shape,
                    k=k,
                    total_found=len(results),
                    search_time_ms=search_time_ms,
                )
            )

        return batch_results

    def search_by_product_id(
        self,
        product_id: int,
        k: int = 50,
        exclude_self: bool = True,
        min_similarity: Optional[float] = None,
    ) -> SearchResults:
        """
        Find similar products to a given product.

        Args:
            product_id: Product ID to find similar items for
            k: Number of similar products to return
            exclude_self: Whether to exclude the query product from results
            min_similarity: Optional minimum similarity threshold (0-1)

        Returns:
            SearchResults object

        Raises:
            SimilaritySearchError: If product not found in index
        """
        # Get FAISS position for this product
        faiss_idx = self.index_manager.get_faiss_position(product_id)

        if faiss_idx is None:
            raise SimilaritySearchError(f"Product ID {product_id} not found in FAISS index")

        # Get vector for this product from index
        index = self.index_manager.get_index()
        vector = index.reconstruct(faiss_idx).reshape(1, -1)

        # Search for similar vectors
        # Request k+1 if excluding self to ensure we get k results
        search_k = k + 1 if exclude_self else k
        results = self.search(vector, k=search_k, min_similarity=min_similarity)

        # Filter out self if needed
        if exclude_self:
            results.results = [r for r in results.results if r.product_id != product_id][:k]
            results.total_found = len(results.results)

            # Re-rank results
            for i, result in enumerate(results.results):
                result.rank = i

        return results

    def _format_results(
        self,
        distances: np.ndarray,
        indices: np.ndarray,
        id_mapping: Dict[int, int],
        min_similarity: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        Format raw FAISS results into SearchResult objects.

        Args:
            distances: Array of distances from FAISS
            indices: Array of indices from FAISS
            id_mapping: Mapping from FAISS index -> product_id
            min_similarity: Optional minimum similarity threshold

        Returns:
            List of SearchResult objects
        """
        results = []

        for rank, (distance, faiss_idx) in enumerate(zip(distances, indices)):
            # Skip invalid indices (FAISS returns -1 for missing results)
            if faiss_idx == -1:
                continue

            # Get product ID
            product_id = id_mapping.get(int(faiss_idx))
            if product_id is None:
                logger.warning(f"FAISS index {faiss_idx} not found in ID mapping")
                continue

            # Convert distance to similarity
            similarity = self._distance_to_similarity(float(distance))

            # Apply similarity threshold
            if min_similarity is not None and similarity < min_similarity:
                continue

            results.append(
                SearchResult(
                    product_id=product_id,
                    distance=float(distance),
                    similarity=similarity,
                    rank=rank,
                )
            )

        return results

    def _distance_to_similarity(self, distance: float) -> float:
        """
        Convert L2 distance to similarity score in [0, 1].

        For normalized vectors (L2 norm = 1):
        - L2 distance = sqrt(2 * (1 - cosine_similarity))
        - cosine_similarity = 1 - (distance^2 / 2)

        Args:
            distance: L2 distance from FAISS

        Returns:
            Similarity score in [0, 1] where 1 is most similar
        """
        if not self.config.embedding.normalize_embeddings:
            # If not normalized, use inverse distance
            # similarity = 1 / (1 + distance)
            return 1.0 / (1.0 + distance)

        # For normalized vectors, convert L2 to cosine similarity
        # Cosine similarity is in [-1, 1], we map it to [0, 1]
        cosine_sim = 1.0 - (distance**2 / 2.0)

        # Clamp to [-1, 1] to handle numerical errors
        cosine_sim = max(-1.0, min(1.0, cosine_sim))

        # Map [-1, 1] to [0, 1]
        similarity = (cosine_sim + 1.0) / 2.0

        return similarity

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """
        L2 normalize a single vector.

        Args:
            vector: Vector to normalize (1D or 2D with single row)

        Returns:
            Normalized vector
        """
        norm = np.linalg.norm(vector)
        if norm < 1e-8:
            logger.warning("Vector has near-zero norm, returning as-is")
            return vector
        return vector / norm

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """
        L2 normalize multiple vectors.

        Args:
            vectors: Vectors to normalize (2D array)

        Returns:
            Normalized vectors
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)

        # Handle zero norms
        norms = np.maximum(norms, 1e-8)

        return vectors / norms

    def get_product_vector(self, product_id: int) -> Optional[np.ndarray]:
        """
        Get embedding vector for a specific product.

        Args:
            product_id: Product ID

        Returns:
            Embedding vector or None if not found
        """
        faiss_idx = self.index_manager.get_faiss_position(product_id)

        if faiss_idx is None:
            return None

        index = self.index_manager.get_index()
        return index.reconstruct(faiss_idx)
