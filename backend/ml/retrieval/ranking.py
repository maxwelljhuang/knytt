"""
Heuristic Ranking System
Multi-signal ranking combining similarity, popularity, price affinity, and brand preferences.

Ranking Formula:
score = 0.6 × similarity + 0.25 × popularity + 0.1 × price_affinity + 0.05 × brand_match
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter

from ..config import get_ml_config, MLConfig
from .similarity_search import SearchResult, SearchResults

logger = logging.getLogger(__name__)


@dataclass
class RankingConfig:
    """Configuration for ranking weights and parameters."""

    # Signal weights (must sum to 1.0)
    similarity_weight: float = 0.6
    popularity_weight: float = 0.25
    price_affinity_weight: float = 0.1
    brand_match_weight: float = 0.05

    # Popularity scoring parameters
    view_weight: float = 1.0
    like_weight: float = 2.0
    cart_weight: float = 3.0
    purchase_weight: float = 5.0

    # Recency decay for popularity (days)
    popularity_half_life_days: int = 30

    # Price affinity parameters
    price_tolerance: float = 0.3  # 30% tolerance from user's typical price

    def __post_init__(self):
        """Validate configuration."""
        total = (
            self.similarity_weight
            + self.popularity_weight
            + self.price_affinity_weight
            + self.brand_match_weight
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Ranking weights must sum to 1.0, got {total}")


class PopularityScorer:
    """
    Calculates popularity scores based on engagement metrics.

    Considers:
    - View count
    - Likes/favorites
    - Add to cart
    - Purchases
    - Recency (recent engagement weighted higher)
    """

    def __init__(self, config: Optional[RankingConfig] = None):
        """
        Initialize popularity scorer.

        Args:
            config: Ranking configuration
        """
        self.config = config or RankingConfig()
        logger.debug("Popularity scorer initialized")

    def score_product(
        self,
        product_id: int,
        views: int = 0,
        likes: int = 0,
        carts: int = 0,
        purchases: int = 0,
        last_interaction: Optional[datetime] = None,
    ) -> float:
        """
        Calculate popularity score for a single product.

        Args:
            product_id: Product ID
            views: Number of views
            likes: Number of likes/favorites
            carts: Number of add-to-cart events
            purchases: Number of purchases
            last_interaction: Timestamp of last interaction (for recency)

        Returns:
            Popularity score in [0, 1]
        """
        # Weighted engagement score
        engagement = (
            views * self.config.view_weight
            + likes * self.config.like_weight
            + carts * self.config.cart_weight
            + purchases * self.config.purchase_weight
        )

        # Apply recency decay
        if last_interaction is not None:
            recency_score = self._calculate_recency_score(last_interaction)
            engagement *= recency_score

        return engagement

    def score_batch(self, product_stats: Dict[int, Dict[str, Any]]) -> Dict[int, float]:
        """
        Calculate popularity scores for multiple products.

        Args:
            product_stats: Dict mapping product_id -> stats dict
                Stats dict should contain: views, likes, carts, purchases, last_interaction

        Returns:
            Dict mapping product_id -> normalized popularity score [0, 1]
        """
        scores = {}

        for product_id, stats in product_stats.items():
            score = self.score_product(
                product_id=product_id,
                views=stats.get("views", 0),
                likes=stats.get("likes", 0),
                carts=stats.get("carts", 0),
                purchases=stats.get("purchases", 0),
                last_interaction=stats.get("last_interaction"),
            )
            scores[product_id] = score

        # Normalize scores to [0, 1]
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {pid: score / max_score for pid, score in scores.items()}

        return scores

    def _calculate_recency_score(self, last_interaction: datetime) -> float:
        """
        Calculate recency decay factor.

        Uses exponential decay with configured half-life.

        Args:
            last_interaction: Timestamp of last interaction

        Returns:
            Decay factor in (0, 1]
        """
        days_ago = (datetime.utcnow() - last_interaction).days

        # Exponential decay: score = 0.5^(days / half_life)
        decay_factor = 0.5 ** (days_ago / self.config.popularity_half_life_days)

        return max(0.01, decay_factor)  # Floor at 1% to avoid zero


class PriceAffinityScorer:
    """
    Calculates price affinity based on user's historical price preferences.

    Scores products based on how well their price matches the user's
    typical spending patterns.
    """

    def __init__(self, config: Optional[RankingConfig] = None):
        """
        Initialize price affinity scorer.

        Args:
            config: Ranking configuration
        """
        self.config = config or RankingConfig()
        logger.debug("Price affinity scorer initialized")

    def calculate_user_price_profile(
        self, purchase_prices: List[float], view_prices: List[float] = None
    ) -> Dict[str, float]:
        """
        Calculate user's price preferences from history.

        Args:
            purchase_prices: List of prices of products user purchased
            view_prices: List of prices of products user viewed (optional)

        Returns:
            Dict with 'mean', 'std', 'min', 'max' price statistics
        """
        if not purchase_prices:
            # Fallback to view prices if no purchases
            if view_prices:
                purchase_prices = view_prices
            else:
                # No data, return neutral profile
                return {"mean": 0, "std": 0, "min": 0, "max": float("inf")}

        prices = np.array(purchase_prices)

        return {
            "mean": float(np.mean(prices)),
            "std": float(np.std(prices)),
            "min": float(np.min(prices)),
            "max": float(np.max(prices)),
        }

    def score_product(self, product_price: float, user_price_profile: Dict[str, float]) -> float:
        """
        Score a product based on price affinity to user's preferences.

        Args:
            product_price: Price of the product
            user_price_profile: User's price profile from calculate_user_price_profile()

        Returns:
            Price affinity score in [0, 1]
        """
        mean_price = user_price_profile["mean"]

        if mean_price == 0:
            # No price data, return neutral score
            return 0.5

        # Calculate relative price difference
        price_diff = abs(product_price - mean_price) / mean_price

        # Score inversely proportional to difference
        # Within tolerance: score = 1.0
        # At 2x tolerance: score = 0.0
        tolerance = self.config.price_tolerance

        if price_diff <= tolerance:
            score = 1.0
        elif price_diff >= 2 * tolerance:
            score = 0.0
        else:
            # Linear decay from tolerance to 2*tolerance
            score = 1.0 - (price_diff - tolerance) / tolerance

        return max(0.0, min(1.0, score))

    def score_batch(
        self, product_prices: Dict[int, float], user_price_profile: Dict[str, float]
    ) -> Dict[int, float]:
        """
        Score multiple products for price affinity.

        Args:
            product_prices: Dict mapping product_id -> price
            user_price_profile: User's price profile

        Returns:
            Dict mapping product_id -> price affinity score [0, 1]
        """
        scores = {}

        for product_id, price in product_prices.items():
            scores[product_id] = self.score_product(price, user_price_profile)

        return scores


class BrandMatchScorer:
    """
    Calculates brand preference scores based on user's brand history.
    """

    def __init__(self, config: Optional[RankingConfig] = None):
        """
        Initialize brand match scorer.

        Args:
            config: Ranking configuration
        """
        self.config = config or RankingConfig()
        logger.debug("Brand match scorer initialized")

    def calculate_user_brand_preferences(
        self, brand_interactions: List[int], interaction_weights: Optional[List[float]] = None
    ) -> Dict[int, float]:
        """
        Calculate user's brand preferences from interaction history.

        Args:
            brand_interactions: List of brand IDs user interacted with
            interaction_weights: Optional weights for each interaction
                                (e.g., purchase=5.0, like=2.0, view=1.0)

        Returns:
            Dict mapping brand_id -> preference score [0, 1]
        """
        if not brand_interactions:
            return {}

        if interaction_weights is None:
            interaction_weights = [1.0] * len(brand_interactions)

        # Calculate weighted brand counts
        brand_scores = {}
        for brand_id, weight in zip(brand_interactions, interaction_weights):
            brand_scores[brand_id] = brand_scores.get(brand_id, 0) + weight

        # Normalize to [0, 1]
        max_score = max(brand_scores.values())
        if max_score > 0:
            brand_scores = {bid: score / max_score for bid, score in brand_scores.items()}

        return brand_scores

    def score_product(
        self, product_brand_id: int, user_brand_preferences: Dict[int, float]
    ) -> float:
        """
        Score a product based on brand match.

        Args:
            product_brand_id: Brand ID of the product
            user_brand_preferences: User's brand preferences from calculate_user_brand_preferences()

        Returns:
            Brand match score in [0, 1]
        """
        if not user_brand_preferences:
            # No brand data, return neutral score
            return 0.5

        # Return preference score if brand is in user's history
        # Otherwise return 0 (unknown brand)
        return user_brand_preferences.get(product_brand_id, 0.0)

    def score_batch(
        self, product_brands: Dict[int, int], user_brand_preferences: Dict[int, float]
    ) -> Dict[int, float]:
        """
        Score multiple products for brand match.

        Args:
            product_brands: Dict mapping product_id -> brand_id
            user_brand_preferences: User's brand preferences

        Returns:
            Dict mapping product_id -> brand match score [0, 1]
        """
        scores = {}

        for product_id, brand_id in product_brands.items():
            scores[product_id] = self.score_product(brand_id, user_brand_preferences)

        return scores


class HeuristicRanker:
    """
    Combines multiple signals to produce final ranking scores.

    Formula: score = w1*similarity + w2*popularity + w3*price_affinity + w4*brand_match
    """

    def __init__(self, config: Optional[RankingConfig] = None):
        """
        Initialize heuristic ranker.

        Args:
            config: Ranking configuration
        """
        self.config = config or RankingConfig()
        self.popularity_scorer = PopularityScorer(self.config)
        self.price_scorer = PriceAffinityScorer(self.config)
        self.brand_scorer = BrandMatchScorer(self.config)

        logger.info(
            f"Heuristic ranker initialized with weights: "
            f"sim={self.config.similarity_weight}, "
            f"pop={self.config.popularity_weight}, "
            f"price={self.config.price_affinity_weight}, "
            f"brand={self.config.brand_match_weight}"
        )

    def rank_results(
        self,
        search_results: SearchResults,
        popularity_scores: Optional[Dict[int, float]] = None,
        price_affinity_scores: Optional[Dict[int, float]] = None,
        brand_match_scores: Optional[Dict[int, float]] = None,
    ) -> SearchResults:
        """
        Re-rank search results using multi-signal scoring.

        Args:
            search_results: Initial search results (sorted by similarity)
            popularity_scores: Optional popularity scores for products
            price_affinity_scores: Optional price affinity scores
            brand_match_scores: Optional brand match scores

        Returns:
            Re-ranked SearchResults
        """
        if len(search_results.results) == 0:
            return search_results

        # Calculate combined scores
        for result in search_results.results:
            pid = result.product_id

            # Get individual signal scores
            similarity = result.similarity
            popularity = popularity_scores.get(pid, 0.5) if popularity_scores else 0.5
            price_affinity = price_affinity_scores.get(pid, 0.5) if price_affinity_scores else 0.5
            brand_match = brand_match_scores.get(pid, 0.5) if brand_match_scores else 0.5

            # Calculate weighted score
            final_score = (
                self.config.similarity_weight * similarity
                + self.config.popularity_weight * popularity
                + self.config.price_affinity_weight * price_affinity
                + self.config.brand_match_weight * brand_match
            )

            # Store scores in metadata
            result.metadata["final_score"] = final_score
            result.metadata["similarity_score"] = similarity
            result.metadata["popularity_score"] = popularity
            result.metadata["price_affinity_score"] = price_affinity
            result.metadata["brand_match_score"] = brand_match

        # Sort by final score (descending)
        search_results.results.sort(key=lambda r: r.metadata["final_score"], reverse=True)

        # Update ranks
        for i, result in enumerate(search_results.results):
            result.rank = i

        logger.debug(f"Re-ranked {len(search_results.results)} results")

        return search_results

    def explain_ranking(self, result: SearchResult) -> str:
        """
        Generate human-readable explanation of ranking score.

        Args:
            result: SearchResult with metadata

        Returns:
            Explanation string
        """
        if "final_score" not in result.metadata:
            return "No ranking data available"

        explanation = f"Product {result.product_id} (Rank {result.rank + 1})\n"
        explanation += f"  Final Score: {result.metadata['final_score']:.4f}\n"
        explanation += f"  Components:\n"
        explanation += f"    Similarity:     {result.metadata['similarity_score']:.4f} × {self.config.similarity_weight} = {result.metadata['similarity_score'] * self.config.similarity_weight:.4f}\n"
        explanation += f"    Popularity:     {result.metadata['popularity_score']:.4f} × {self.config.popularity_weight} = {result.metadata['popularity_score'] * self.config.popularity_weight:.4f}\n"
        explanation += f"    Price Affinity: {result.metadata['price_affinity_score']:.4f} × {self.config.price_affinity_weight} = {result.metadata['price_affinity_score'] * self.config.price_affinity_weight:.4f}\n"
        explanation += f"    Brand Match:    {result.metadata['brand_match_score']:.4f} × {self.config.brand_match_weight} = {result.metadata['brand_match_score'] * self.config.brand_match_weight:.4f}\n"

        return explanation
