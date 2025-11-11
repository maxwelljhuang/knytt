"""
Advanced Deduplication Service
Uses HDBSCAN clustering and fuzzy matching to identify duplicate products.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Set, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from collections import defaultdict
import hashlib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Initialize logger first
logger = logging.getLogger(__name__)

try:
    import hdbscan

    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    hdbscan = None
    logger.warning("hdbscan not available - clustering-based deduplication disabled")

from rapidfuzz import fuzz, process
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.product import ProductIngestion, ProductCanonical


@dataclass
class DuplicateCluster:
    """Represents a cluster of duplicate products."""

    cluster_id: str
    products: List[Dict]
    canonical_product: Dict
    confidence: float
    method: str  # 'exact_hash', 'fuzzy_match', 'hdbscan_cluster'


class AdvancedDeduplicator:
    """
    Advanced deduplication using multiple strategies:
    1. Exact hash matching
    2. Fuzzy string matching
    3. HDBSCAN clustering on text embeddings
    """

    def __init__(
        self,
        exact_threshold: float = 1.0,
        fuzzy_threshold: float = 0.85,
        cluster_min_similarity: float = 0.70,
    ):
        """
        Initialize the deduplicator.

        Args:
            exact_threshold: Threshold for exact matching (always 1.0)
            fuzzy_threshold: Threshold for fuzzy string matching (0.85-0.95)
            cluster_min_similarity: Minimum similarity for HDBSCAN clusters (0.65-0.75)
        """
        self.exact_threshold = exact_threshold
        self.fuzzy_threshold = fuzzy_threshold
        self.cluster_min_similarity = cluster_min_similarity

        # TF-IDF vectorizer for text embedding
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            strip_accents="unicode",
            analyzer="word",
            token_pattern=r"\b[a-zA-Z0-9]+\b",
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_df=0.9,
            min_df=2,
            sublinear_tf=True,
        )

        # HDBSCAN clusterer (optional - only if hdbscan is available)
        if HDBSCAN_AVAILABLE:
            self.clusterer = hdbscan.HDBSCAN(
                min_cluster_size=2,
                min_samples=1,
                metric="euclidean",
                cluster_selection_method="eom",  # Excess of Mass
                prediction_data=True,
            )
        else:
            self.clusterer = None
            logger.info("HDBSCAN clustering disabled - hdbscan package not installed")

        # Statistics
        self.stats = {
            "total_products": 0,
            "unique_products": 0,
            "exact_duplicates": 0,
            "fuzzy_duplicates": 0,
            "cluster_duplicates": 0,
            "clusters_found": 0,
        }

    def deduplicate_batch(
        self,
        products: List[ProductIngestion],
        check_database: bool = True,
        session: Optional[Session] = None,
    ) -> Tuple[List[ProductIngestion], List[DuplicateCluster]]:
        """
        Deduplicate a batch of products using all strategies.

        Args:
            products: List of products to deduplicate
            check_database: Whether to check against existing database
            session: Database session for checking existing products

        Returns:
            Tuple of (unique_products, duplicate_clusters)
        """
        if not products:
            return [], []

        self.stats["total_products"] = len(products)
        logger.info(f"Starting deduplication for {len(products)} products")

        # Convert to DataFrame for easier processing
        df = self._products_to_dataframe(products)

        # Step 1: Check against database FIRST (before any clustering)
        # This prevents canonicals from being removed after clusters are formed
        db_duplicates = []
        if check_database and session:
            df, db_duplicates = self._check_database_duplicates(df, session)
            logger.info(f"Found {len(df[df['is_duplicate']].index)} products already in database")

        # Step 2: Exact hash matching on remaining products
        df, exact_clusters = self._exact_deduplication(df)
        logger.info(f"Found {len(exact_clusters)} exact duplicate clusters")

        # Step 3: Fuzzy string matching on remaining products
        df, fuzzy_clusters = self._fuzzy_deduplication(df)
        logger.info(f"Found {len(fuzzy_clusters)} fuzzy duplicate clusters")

        # Step 4: HDBSCAN clustering on remaining products (if available)
        if len(df) > 10 and HDBSCAN_AVAILABLE and self.clusterer is not None:
            df, cluster_duplicates = self._hdbscan_deduplication(df)
            logger.info(f"Found {len(cluster_duplicates)} clusters via HDBSCAN")
        else:
            if len(df) > 10 and not HDBSCAN_AVAILABLE:
                logger.info("Skipping HDBSCAN clustering (hdbscan not available)")
            cluster_duplicates = []

        # Combine all duplicate clusters
        all_clusters = exact_clusters + fuzzy_clusters + cluster_duplicates + db_duplicates

        # Convert remaining unique products back
        unique_products = self._dataframe_to_products(df, products)

        self.stats["unique_products"] = len(unique_products)
        self._log_statistics()

        return unique_products, all_clusters

    def _products_to_dataframe(self, products: List[ProductIngestion]) -> pd.DataFrame:
        """Convert products to DataFrame for processing."""
        data = []
        for idx, product in enumerate(products):
            data.append(
                {
                    "idx": idx,
                    "product_id": product.merchant_product_id,
                    "merchant_id": product.merchant_id,
                    "name": product.product_name,
                    "brand": product.brand_name or "",
                    "description": product.description or "",
                    "category": product.category_name or "",
                    "price": float(product.search_price) if product.search_price else 0,
                    "colour": product.colour or "",
                    "size": product.fashion_size or "",
                    "model": product.model_number or "",
                    "quality_score": product.quality_score,
                    "hash": product.dedup_hash,
                    # Combined text for embedding
                    "text": self._create_text_representation(product),
                    "is_duplicate": False,
                    "cluster_id": None,
                    "original_product": product,
                }
            )

        return pd.DataFrame(data)

    def _create_text_representation(self, product: ProductIngestion) -> str:
        """Create text representation for similarity comparison."""
        parts = []

        # Add important fields
        if product.brand_name:
            parts.append(product.brand_name.lower())

        if product.product_name:
            # Clean product name
            name = product.product_name.lower()
            # Remove common words
            for word in ["the", "and", "or", "with", "for"]:
                name = name.replace(f" {word} ", " ")
            parts.append(name)

        if product.category_name:
            parts.append(product.category_name.lower())

        if product.colour:
            parts.append(product.colour.lower())

        if product.fashion_size:
            parts.append(f"size_{product.fashion_size.lower()}")

        if product.model_number:
            parts.append(f"model_{product.model_number.lower()}")

        return " ".join(parts)

    def _exact_deduplication(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[DuplicateCluster]]:
        """Find exact duplicates using hash."""
        clusters = []

        # Only consider products not already marked as duplicates
        df_to_check = df[~df["is_duplicate"]].copy() if "is_duplicate" in df.columns else df.copy()

        # Group by hash
        hash_groups = df_to_check.groupby("hash").filter(lambda x: len(x) > 1)

        if not hash_groups.empty:
            for hash_val, group in hash_groups.groupby("hash"):
                # Keep the one with highest quality score
                best_idx = group["quality_score"].idxmax()

                cluster = DuplicateCluster(
                    cluster_id=f"exact_{hash_val[:8]}",
                    products=group.to_dict("records"),
                    canonical_product=group.loc[best_idx].to_dict(),
                    confidence=1.0,
                    method="exact_hash",
                )
                clusters.append(cluster)

                # Mark duplicates
                duplicate_indices = group.index[group.index != best_idx]
                df.loc[duplicate_indices, "is_duplicate"] = True
                df.loc[duplicate_indices, "cluster_id"] = cluster.cluster_id

                self.stats["exact_duplicates"] += len(duplicate_indices)

        # Remove duplicates from DataFrame
        df_unique = df[~df["is_duplicate"]].copy()

        return df_unique, clusters

    def _fuzzy_deduplication(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[DuplicateCluster]]:
        """Find near-duplicates using fuzzy string matching."""
        clusters = []

        # Only work with products not already marked as duplicates
        if "is_duplicate" not in df.columns:
            df["is_duplicate"] = False

        df_to_check = df[~df["is_duplicate"]].copy()

        # Group by brand for efficiency
        brand_groups = df_to_check.groupby("brand")

        for brand, group in brand_groups:
            if len(group) < 2:
                continue

            # Get product names
            names = group["name"].tolist()
            indices = group.index.tolist()

            # Find fuzzy matches
            processed_indices = set()

            for i, (idx, name) in enumerate(zip(indices, names)):
                if idx in processed_indices:
                    continue

                # Find similar products
                matches = process.extract(
                    name,
                    names[i + 1 :],  # Only check subsequent products
                    scorer=fuzz.token_sort_ratio,
                    limit=10,
                )

                # Collect high-similarity matches
                similar_indices = []
                for match_name, score, match_idx in matches:
                    if score >= self.fuzzy_threshold * 100:  # Convert to percentage
                        actual_idx = indices[i + 1 + match_idx]
                        similar_indices.append(actual_idx)
                        processed_indices.add(actual_idx)

                if similar_indices:
                    # Create cluster
                    cluster_indices = [idx] + similar_indices
                    cluster_data = df.loc[cluster_indices]

                    # Choose canonical (highest quality)
                    best_idx = cluster_data["quality_score"].idxmax()

                    cluster = DuplicateCluster(
                        cluster_id=f"fuzzy_{brand[:4]}_{len(clusters)}",
                        products=cluster_data.to_dict("records"),
                        canonical_product=cluster_data.loc[best_idx].to_dict(),
                        confidence=max(m[1] for m in matches) / 100,
                        method="fuzzy_match",
                    )
                    clusters.append(cluster)

                    # Mark non-canonical as duplicates
                    duplicate_indices = [i for i in cluster_indices if i != best_idx]
                    df.loc[duplicate_indices, "is_duplicate"] = True
                    df.loc[duplicate_indices, "cluster_id"] = cluster.cluster_id

                    self.stats["fuzzy_duplicates"] += len(duplicate_indices)
                    processed_indices.add(idx)

        # Remove duplicates
        df_unique = df[~df["is_duplicate"]].copy()

        return df_unique, clusters

    def _hdbscan_deduplication(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[DuplicateCluster]]:
        """Find duplicates using HDBSCAN clustering on text embeddings."""
        clusters = []

        # Check if HDBSCAN is available
        if not HDBSCAN_AVAILABLE or self.clusterer is None:
            logger.info("HDBSCAN clustering skipped (not available)")
            return df, []

        # Reset duplicate flags
        df["is_duplicate"] = False

        # Create TF-IDF embeddings
        try:
            embeddings = self.vectorizer.fit_transform(df["text"].tolist())
        except Exception as e:
            logger.warning(f"Failed to create embeddings: {e}")
            return df, []

        # Run HDBSCAN clustering
        cluster_labels = self.clusterer.fit_predict(embeddings.toarray())

        # Add cluster labels to DataFrame
        df["hdbscan_cluster"] = cluster_labels

        # Process each cluster (excluding noise points with label -1)
        unique_clusters = set(cluster_labels)
        unique_clusters.discard(-1)  # Remove noise label

        for cluster_label in unique_clusters:
            cluster_mask = df["hdbscan_cluster"] == cluster_label
            cluster_data = df[cluster_mask]

            if len(cluster_data) < 2:
                continue

            # Calculate intra-cluster similarity
            cluster_indices = cluster_data.index.tolist()
            cluster_embeddings = embeddings[cluster_indices]

            # Compute pairwise similarity
            similarity_matrix = cosine_similarity(cluster_embeddings)
            avg_similarity = (similarity_matrix.sum() - len(cluster_data)) / (
                len(cluster_data) * (len(cluster_data) - 1)
            )

            # Only consider as duplicates if similarity is high enough
            if avg_similarity >= self.cluster_min_similarity:
                # Choose canonical (highest quality)
                best_idx = cluster_data["quality_score"].idxmax()

                cluster = DuplicateCluster(
                    cluster_id=f"cluster_{cluster_label}",
                    products=cluster_data.to_dict("records"),
                    canonical_product=cluster_data.loc[best_idx].to_dict(),
                    confidence=float(avg_similarity),
                    method="hdbscan_cluster",
                )
                clusters.append(cluster)

                # Mark non-canonical as duplicates
                duplicate_indices = [i for i in cluster_indices if i != best_idx]
                df.loc[duplicate_indices, "is_duplicate"] = True
                df.loc[duplicate_indices, "cluster_id"] = cluster.cluster_id

                self.stats["cluster_duplicates"] += len(duplicate_indices)

        self.stats["clusters_found"] = len(clusters)

        # Remove duplicates
        df_unique = df[~df["is_duplicate"]].copy()

        return df_unique, clusters

    def _check_database_duplicates(
        self, df: pd.DataFrame, session: Session
    ) -> Tuple[pd.DataFrame, List[DuplicateCluster]]:
        """Check for duplicates against existing database products."""
        clusters = []

        # Get all hashes from the batch
        batch_hashes = df["hash"].unique().tolist()

        # Query existing products with same hashes
        result = session.execute(
            text(
                """
                SELECT product_hash, id, product_name, quality_score
                FROM products
                WHERE product_hash = ANY(:hashes)
                AND is_active = true
            """
            ),
            {"hashes": batch_hashes},
        )

        existing_products = {
            row[0]: {"id": row[1], "name": row[2], "quality_score": row[3]} for row in result
        }

        # Find duplicates
        for idx, row in df.iterrows():
            if row["hash"] in existing_products:
                existing = existing_products[row["hash"]]

                # Compare quality scores
                if row["quality_score"] > existing["quality_score"]:
                    # New product is better, mark for update
                    logger.info(f"Found better version of product {existing['id']}")
                else:
                    # Existing is better, mark new as duplicate
                    df.loc[idx, "is_duplicate"] = True
                    df.loc[idx, "cluster_id"] = f"db_{str(existing['id'])[:8]}"

        # Remove duplicates
        df_unique = df[~df["is_duplicate"]].copy()

        return df_unique, clusters

    def _dataframe_to_products(
        self, df: pd.DataFrame, original_products: List[ProductIngestion]
    ) -> List[ProductIngestion]:
        """Convert DataFrame back to products."""
        unique_indices = df["idx"].tolist()
        return [original_products[i] for i in unique_indices]

    def _log_statistics(self):
        """Log deduplication statistics."""
        logger.info("=== Deduplication Statistics ===")
        logger.info(f"Total Products: {self.stats['total_products']}")
        logger.info(f"Unique Products: {self.stats['unique_products']}")
        logger.info(f"Exact Duplicates: {self.stats['exact_duplicates']}")
        logger.info(f"Fuzzy Duplicates: {self.stats['fuzzy_duplicates']}")
        logger.info(f"Cluster Duplicates: {self.stats['cluster_duplicates']}")
        logger.info(f"HDBSCAN Clusters Found: {self.stats['clusters_found']}")

        dedup_rate = (
            (self.stats["total_products"] - self.stats["unique_products"])
            / self.stats["total_products"]
            * 100
            if self.stats["total_products"] > 0
            else 0
        )
        logger.info(f"Deduplication Rate: {dedup_rate:.1f}%")

    def merge_duplicate_clusters(self, session: Session, clusters: List[DuplicateCluster]):
        """
        Merge duplicate products in the database.
        Keep the canonical product and update references.
        """
        for cluster in clusters:
            canonical = cluster.canonical_product

            # Update all duplicates to point to canonical
            duplicate_ids = [
                p["product_id"]
                for p in cluster.products
                if p["product_id"] != canonical["product_id"]
            ]

            if duplicate_ids:
                # Mark duplicates
                session.execute(
                    text(
                        """
                        UPDATE products
                        SET is_duplicate = true,
                            canonical_product_id = :canonical_id,
                            is_active = false
                        WHERE merchant_product_id = ANY(:duplicate_ids)
                        AND merchant_id = :merchant_id
                    """
                    ),
                    {
                        "canonical_id": canonical["product_id"],
                        "duplicate_ids": duplicate_ids,
                        "merchant_id": canonical["merchant_id"],
                    },
                )

                # Log deduplication
                for dup_id in duplicate_ids:
                    session.execute(
                        text(
                            """
                            INSERT INTO deduplication_log (
                                original_product_id,
                                duplicate_product_id,
                                similarity_score,
                                dedup_method
                            ) VALUES (
                                :original_id,
                                :duplicate_id,
                                :similarity,
                                :method
                            )
                        """
                        ),
                        {
                            "original_id": canonical["product_id"],
                            "duplicate_id": dup_id,
                            "similarity": cluster.confidence,
                            "method": cluster.method,
                        },
                    )


class CrossMerchantDeduplicator:
    """
    Deduplicate products across different merchants.
    Identifies the same product sold by multiple merchants.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            strip_accents="unicode",
            analyzer="word",
            ngram_range=(1, 3),  # Include trigrams for better matching
            max_df=0.8,
            min_df=1,
        )

    def find_cross_merchant_duplicates(
        self,
        session: Session,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        batch_size: int = 1000,
    ) -> List[DuplicateCluster]:
        """
        Find products that are the same across different merchants.

        Args:
            session: Database session
            category_id: Optional category filter
            brand_id: Optional brand filter
            batch_size: Number of products to process at once
        """
        clusters = []

        # Build query
        query = """
            SELECT id, merchant_id, merchant_product_id, product_name, 
                   brand_name, description, model_number, quality_score
            FROM products
            WHERE is_active = true AND is_duplicate = false
        """

        params = {}
        if category_id:
            query += " AND category_id = :category_id"
            params["category_id"] = category_id

        if brand_id:
            query += " AND brand_id = :brand_id"
            params["brand_id"] = brand_id

        query += " ORDER BY brand_name, product_name"

        result = session.execute(text(query), params)
        products = result.fetchall()

        logger.info(f"Checking {len(products)} products for cross-merchant duplicates")

        # Group by brand for efficiency
        brand_groups = defaultdict(list)
        for product in products:
            brand = product[4] or "unknown"
            brand_groups[brand].append(product)

        # Process each brand group
        for brand, brand_products in brand_groups.items():
            if len(brand_products) < 2:
                continue

            # Create text representations
            texts = []
            for p in brand_products:
                text = f"{p[3]} {p[5] or ''} {p[6] or ''}"  # name + description + model
                texts.append(text)

            # Create embeddings
            try:
                embeddings = self.vectorizer.fit_transform(texts)
                similarity_matrix = cosine_similarity(embeddings)

                # Find similar products
                processed = set()
                for i in range(len(brand_products)):
                    if i in processed:
                        continue

                    similar_indices = []
                    for j in range(i + 1, len(brand_products)):
                        if similarity_matrix[i][j] >= 0.85:  # High similarity threshold
                            # Check if different merchants
                            if brand_products[i][1] != brand_products[j][1]:
                                similar_indices.append(j)
                                processed.add(j)

                    if similar_indices:
                        # Create cross-merchant cluster
                        cluster_products = [brand_products[i]]
                        cluster_products.extend([brand_products[j] for j in similar_indices])

                        # Choose canonical (highest quality)
                        best_product = max(cluster_products, key=lambda x: x[7])  # quality_score

                        cluster = DuplicateCluster(
                            cluster_id=f"xmerchant_{brand[:4]}_{len(clusters)}",
                            products=[
                                {
                                    "id": p[0],
                                    "merchant_id": p[1],
                                    "product_id": p[2],
                                    "name": p[3],
                                    "quality_score": p[7],
                                }
                                for p in cluster_products
                            ],
                            canonical_product={
                                "id": best_product[0],
                                "merchant_id": best_product[1],
                                "product_id": best_product[2],
                                "name": best_product[3],
                            },
                            confidence=max(similarity_matrix[i][j] for j in similar_indices),
                            method="cross_merchant",
                        )
                        clusters.append(cluster)
                        processed.add(i)

            except Exception as e:
                logger.warning(f"Failed to process brand {brand}: {e}")
                continue

        logger.info(f"Found {len(clusters)} cross-merchant duplicate clusters")
        return clusters
