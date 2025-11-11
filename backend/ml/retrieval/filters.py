"""
Product Filtering
Build SQL queries and filter product embeddings based on business logic.
"""

import logging
from typing import List, Optional, Dict, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class FilterOperator(Enum):
    """Comparison operators for filters."""

    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    IN = "IN"
    NOT_IN = "NOT IN"
    LIKE = "LIKE"
    ILIKE = "ILIKE"  # Case-insensitive LIKE


@dataclass
class ProductFilter:
    """
    Single filter condition for products.

    Example:
        ProductFilter("price", FilterOperator.LTE, 100.0)  # price <= 100
        ProductFilter("merchant_id", FilterOperator.IN, [1, 2, 3])
    """

    field: str
    operator: FilterOperator
    value: Any

    def to_sql(self) -> Tuple[str, Any]:
        """
        Convert filter to SQL WHERE clause.

        Returns:
            Tuple of (sql_fragment, parameter_value)
        """
        if self.operator in [FilterOperator.IN, FilterOperator.NOT_IN]:
            # Handle IN/NOT IN with list values
            placeholders = ",".join(["%s"] * len(self.value))
            sql = f"{self.field} {self.operator.value} ({placeholders})"
            return sql, self.value
        elif self.operator in [FilterOperator.LIKE, FilterOperator.ILIKE]:
            # Handle LIKE with pattern
            sql = f"{self.field} {self.operator.value} %s"
            return sql, self.value
        else:
            # Handle simple comparisons
            sql = f"{self.field} {self.operator.value} %s"
            return sql, self.value


@dataclass
class ProductFilters:
    """
    Collection of filters for product search.

    Common filters:
    - Price range
    - Stock availability
    - Merchant/seller
    - Category
    - Brand
    - Gender/size (for fashion)
    """

    # Price filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    # Availability
    in_stock_only: bool = True
    min_stock_quantity: int = 0

    # Merchant/Seller
    merchant_ids: Optional[List[int]] = None
    exclude_merchant_ids: Optional[List[int]] = None

    # Category/Classification
    category_ids: Optional[List[int]] = None
    exclude_category_ids: Optional[List[int]] = None

    # Brand
    brand_ids: Optional[List[int]] = None
    exclude_brand_ids: Optional[List[int]] = None

    # Gender (for fashion)
    gender: Optional[str] = None  # 'M', 'F', 'U' (unisex)

    # Custom filters
    custom_filters: List[ProductFilter] = field(default_factory=list)

    # Embedding requirement
    require_embedding: bool = True  # Only return products with embeddings

    def build_filters(self) -> List[ProductFilter]:
        """
        Build list of ProductFilter objects from this config.

        Returns:
            List of ProductFilter objects
        """
        filters = []

        # Price filters
        if self.min_price is not None:
            filters.append(ProductFilter("price", FilterOperator.GTE, self.min_price))
        if self.max_price is not None:
            filters.append(ProductFilter("price", FilterOperator.LTE, self.max_price))

        # Stock filters
        if self.in_stock_only:
            filters.append(ProductFilter("in_stock", FilterOperator.EQ, True))
        if self.min_stock_quantity > 0:
            filters.append(
                ProductFilter("stock_quantity", FilterOperator.GTE, self.min_stock_quantity)
            )

        # Merchant filters
        if self.merchant_ids:
            filters.append(ProductFilter("merchant_id", FilterOperator.IN, self.merchant_ids))
        if self.exclude_merchant_ids:
            filters.append(
                ProductFilter("merchant_id", FilterOperator.NOT_IN, self.exclude_merchant_ids)
            )

        # Category filters
        if self.category_ids:
            filters.append(ProductFilter("category_id", FilterOperator.IN, self.category_ids))
        if self.exclude_category_ids:
            filters.append(
                ProductFilter("category_id", FilterOperator.NOT_IN, self.exclude_category_ids)
            )

        # Brand filters
        if self.brand_ids:
            filters.append(ProductFilter("brand_id", FilterOperator.IN, self.brand_ids))
        if self.exclude_brand_ids:
            filters.append(ProductFilter("brand_id", FilterOperator.NOT_IN, self.exclude_brand_ids))

        # Gender filter
        if self.gender:
            filters.append(ProductFilter("gender", FilterOperator.EQ, self.gender))

        # Embedding requirement
        if self.require_embedding:
            filters.append(ProductFilter("embedding", FilterOperator.NE, None))

        # Add custom filters
        filters.extend(self.custom_filters)

        return filters

    def to_sql_where_clause(self) -> Tuple[str, List[Any]]:
        """
        Build SQL WHERE clause from filters.

        Returns:
            Tuple of (where_clause, parameters)
            Example: ("price >= %s AND price <= %s AND in_stock = %s", [10.0, 100.0, True])
        """
        filters = self.build_filters()

        if not filters:
            return "", []

        conditions = []
        parameters = []

        for f in filters:
            sql_fragment, value = f.to_sql()
            conditions.append(sql_fragment)

            # Handle IN/NOT IN which have list values
            if isinstance(value, (list, tuple)):
                parameters.extend(value)
            else:
                parameters.append(value)

        where_clause = " AND ".join(conditions)

        return where_clause, parameters


class FilteredSearcher:
    """
    Performs two-stage filtered search:
    1. Filter products in PostgreSQL based on business logic
    2. Search only the filtered product embeddings in FAISS

    This is more efficient than searching all products and filtering after.
    """

    def __init__(self, db_session_factory=None):
        """
        Initialize filtered searcher.

        Args:
            db_session_factory: Factory function to create database sessions
        """
        self.db_session_factory = db_session_factory
        logger.info("Filtered searcher initialized")

    def get_filtered_product_ids(
        self, session, filters: ProductFilters, limit: Optional[int] = None
    ) -> List[int]:
        """
        Get list of product IDs that match filters.

        Args:
            session: SQLAlchemy database session
            filters: ProductFilters object
            limit: Optional limit on number of products to return

        Returns:
            List of product IDs that match filters
        """
        # Build WHERE clause
        where_clause, parameters = filters.to_sql_where_clause()

        # Build SQL query
        sql = "SELECT id FROM products"

        if where_clause:
            sql += f" WHERE {where_clause}"

        sql += " ORDER BY id"

        if limit:
            sql += f" LIMIT {limit}"

        # Execute query
        result = session.execute(sql, parameters)
        product_ids = [row[0] for row in result.fetchall()]

        logger.info(f"Filtered to {len(product_ids)} products matching criteria")

        return product_ids

    def get_filtered_embeddings(
        self, session, filters: ProductFilters, limit: Optional[int] = None
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Get embeddings for products that match filters.

        Args:
            session: SQLAlchemy database session
            filters: ProductFilters object
            limit: Optional limit on number of products

        Returns:
            Tuple of (embeddings_array, product_ids)
        """
        # Build WHERE clause
        where_clause, parameters = filters.to_sql_where_clause()

        # Build SQL query to get embeddings
        sql = "SELECT id, embedding FROM products"

        if where_clause:
            sql += f" WHERE {where_clause}"

        sql += " ORDER BY id"

        if limit:
            sql += f" LIMIT {limit}"

        # Execute query
        result = session.execute(sql, parameters)
        rows = result.fetchall()

        if len(rows) == 0:
            logger.warning("No products match the specified filters")
            return np.array([]).reshape(0, 0), []

        # Extract embeddings and IDs
        product_ids = []
        embeddings_list = []

        for row in rows:
            product_id = row[0]
            embedding = row[1]

            # Convert pgvector to numpy array
            if isinstance(embedding, str):
                embedding = np.fromstring(embedding.strip("[]"), sep=",")
            elif isinstance(embedding, (list, tuple)):
                embedding = np.array(embedding)

            product_ids.append(product_id)
            embeddings_list.append(embedding)

        embeddings = np.vstack(embeddings_list).astype(np.float32)

        logger.info(f"Retrieved {len(product_ids)} embeddings matching filters")

        return embeddings, product_ids

    def build_subset_index(
        self, embeddings: np.ndarray, product_ids: List[int]
    ) -> Tuple["faiss.Index", Dict[int, int]]:
        """
        Build a temporary FAISS index for filtered products.

        Args:
            embeddings: Array of embeddings
            product_ids: List of product IDs

        Returns:
            Tuple of (faiss_index, id_mapping)
        """
        try:
            import faiss
        except ImportError:
            raise ImportError("FAISS not installed")

        if len(embeddings) == 0:
            raise ValueError("Cannot build index with no embeddings")

        # Create simple Flat index for subset
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)

        # Add embeddings
        index.add(embeddings)

        # Create ID mapping
        id_mapping = {i: pid for i, pid in enumerate(product_ids)}

        logger.info(f"Built subset index with {index.ntotal} vectors")

        return index, id_mapping

    def filter_product_ids_in_index(
        self, all_product_ids: List[int], allowed_product_ids: Set[int]
    ) -> Tuple[np.ndarray, Dict[int, int]]:
        """
        Filter product IDs to only those in allowed set.

        Args:
            all_product_ids: All product IDs from index (in FAISS order)
            allowed_product_ids: Set of allowed product IDs after filtering

        Returns:
            Tuple of (valid_indices, filtered_id_mapping)
            - valid_indices: Array of FAISS positions for allowed products
            - filtered_id_mapping: New mapping from subset position -> product_id
        """
        valid_indices = []
        filtered_mapping = {}
        new_position = 0

        for faiss_idx, product_id in enumerate(all_product_ids):
            if product_id in allowed_product_ids:
                valid_indices.append(faiss_idx)
                filtered_mapping[new_position] = product_id
                new_position += 1

        return np.array(valid_indices, dtype=np.int64), filtered_mapping


def create_price_filter(min_price: float = None, max_price: float = None) -> ProductFilters:
    """Convenience function to create price range filter."""
    return ProductFilters(min_price=min_price, max_price=max_price)


def create_merchant_filter(merchant_ids: List[int]) -> ProductFilters:
    """Convenience function to create merchant filter."""
    return ProductFilters(merchant_ids=merchant_ids)


def create_category_filter(category_ids: List[int]) -> ProductFilters:
    """Convenience function to create category filter."""
    return ProductFilters(category_ids=category_ids)


def combine_filters(*filter_objects: ProductFilters) -> ProductFilters:
    """
    Combine multiple ProductFilters objects into one.

    Args:
        *filter_objects: Multiple ProductFilters to combine

    Returns:
        Combined ProductFilters object
    """
    combined = ProductFilters()

    for f in filter_objects:
        # Combine price filters (use most restrictive)
        if f.min_price is not None:
            combined.min_price = max(combined.min_price or 0, f.min_price)
        if f.max_price is not None:
            if combined.max_price is None:
                combined.max_price = f.max_price
            else:
                combined.max_price = min(combined.max_price, f.max_price)

        # Combine stock filters (use most restrictive)
        combined.in_stock_only = combined.in_stock_only or f.in_stock_only
        combined.min_stock_quantity = max(combined.min_stock_quantity, f.min_stock_quantity)

        # Combine merchant filters (intersection)
        if f.merchant_ids:
            if combined.merchant_ids is None:
                combined.merchant_ids = f.merchant_ids
            else:
                combined.merchant_ids = list(set(combined.merchant_ids) & set(f.merchant_ids))

        # Combine exclusions (union)
        if f.exclude_merchant_ids:
            if combined.exclude_merchant_ids is None:
                combined.exclude_merchant_ids = f.exclude_merchant_ids
            else:
                combined.exclude_merchant_ids = list(
                    set(combined.exclude_merchant_ids) | set(f.exclude_merchant_ids)
                )

        # Similar for categories and brands...
        if f.category_ids:
            if combined.category_ids is None:
                combined.category_ids = f.category_ids
            else:
                combined.category_ids = list(set(combined.category_ids) & set(f.category_ids))

        if f.brand_ids:
            if combined.brand_ids is None:
                combined.brand_ids = f.brand_ids
            else:
                combined.brand_ids = list(set(combined.brand_ids) & set(f.brand_ids))

        # Combine custom filters
        combined.custom_filters.extend(f.custom_filters)

    return combined
