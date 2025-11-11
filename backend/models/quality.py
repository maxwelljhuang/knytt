"""
Quality assessment and content moderation for products.
"""

from typing import Dict, List, Tuple, Optional
import re
from decimal import Decimal
from enum import Enum


class QualitySeverity(str, Enum):
    """Severity levels for quality issues."""

    CRITICAL = "critical"  # Product should be rejected
    WARNING = "warning"  # Product can be used but has issues
    INFO = "info"  # Minor issue, informational only


class ContentModerator:
    """Check products for inappropriate or low-quality content."""

    # NSFW keywords (extend this list based on your needs)
    NSFW_KEYWORDS = [
        "adult",
        "xxx",
        "porn",
        "sex toy",
        "erotic",
        "nude",
        "explicit",
        "escort",
        "dating",
    ]

    # Spam indicators
    SPAM_PATTERNS = [
        r"(click here|buy now|act now|limited time){2,}",
        r"[A-Z\s]{20,}",  # Excessive caps
        r"(\$\$\$|!!!|###){3,}",
        r"(best|cheap|discount|free|guarantee){4,}",
    ]

    # Suspicious brands (known dropshipping/low quality)
    SUSPICIOUS_BRANDS = ["no brand", "unknown", "generic", "oem", "china brand", "factory direct"]

    @classmethod
    def check_nsfw(cls, product: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if product contains NSFW content.
        Returns (is_nsfw, reason)
        """
        text_to_check = " ".join(
            [
                str(product.get("product_name", "")),
                str(product.get("description", "")),
                str(product.get("category_name", "")),
                str(product.get("keywords", "")),
            ]
        ).lower()

        for keyword in cls.NSFW_KEYWORDS:
            if keyword in text_to_check:
                return True, f"Contains NSFW keyword: {keyword}"

        return False, None

    @classmethod
    def check_spam(cls, product: Dict) -> List[str]:
        """Check for spam indicators."""
        issues = []

        name = product.get("product_name", "")
        desc = product.get("description", "")

        # Check spam patterns
        for pattern in cls.SPAM_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                issues.append(f"Spam pattern in name: {pattern}")
            if desc and re.search(pattern, desc, re.IGNORECASE):
                issues.append(f"Spam pattern in description: {pattern}")

        # Check suspicious brands
        brand = str(product.get("brand_name", "")).lower()
        if brand in cls.SUSPICIOUS_BRANDS:
            issues.append(f"Suspicious brand: {brand}")

        return issues

    @classmethod
    def calculate_trust_score(cls, product: Dict) -> float:
        """
        Calculate trust score (0-1) based on various factors.
        Higher score = more trustworthy.
        """
        score = 1.0

        # Penalize missing important fields
        if not product.get("brand_name"):
            score -= 0.1

        if not product.get("description"):
            score -= 0.15

        if not product.get("merchant_image_url"):
            score -= 0.2

        # Penalize suspicious prices
        price = product.get("search_price")
        if price:
            if price < 0.01:
                score -= 0.3  # Too cheap
            elif price > 10000:
                score -= 0.1  # Very expensive (could be valid)

        # Boost for having reviews
        if product.get("reviews", 0) > 0:
            score += 0.1

        # Boost for having multiple images
        if product.get("alternate_images") and len(product.get("alternate_images", [])) > 0:
            score += 0.05

        # Check spam indicators
        spam_issues = cls.check_spam(product)
        score -= len(spam_issues) * 0.1

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))


class PriceValidator:
    """Validate and analyze product pricing."""

    @staticmethod
    def check_price_anomalies(product: Dict) -> List[Dict]:
        """Check for pricing issues."""
        issues = []

        search_price = product.get("search_price")
        rrp_price = product.get("rrp_price")
        store_price = product.get("store_price")

        # Check for negative or zero prices
        if search_price is not None:
            if search_price <= 0:
                issues.append(
                    {
                        "field": "search_price",
                        "issue": "invalid_price",
                        "value": str(search_price),
                        "severity": QualitySeverity.CRITICAL,
                    }
                )

            # Check for suspiciously low price
            elif search_price < Decimal("0.10"):
                issues.append(
                    {
                        "field": "search_price",
                        "issue": "suspiciously_low",
                        "value": str(search_price),
                        "severity": QualitySeverity.WARNING,
                    }
                )

            # Check for suspiciously high price
            elif search_price > Decimal("50000"):
                issues.append(
                    {
                        "field": "search_price",
                        "issue": "suspiciously_high",
                        "value": str(search_price),
                        "severity": QualitySeverity.WARNING,
                    }
                )

        # Check price consistency
        if rrp_price and search_price:
            # Check for impossible discount
            if search_price > rrp_price * Decimal("1.1"):  # 10% tolerance
                issues.append(
                    {
                        "field": "pricing",
                        "issue": "search_price_exceeds_rrp",
                        "severity": QualitySeverity.WARNING,
                    }
                )

            # Check for unrealistic discount
            discount_pct = ((rrp_price - search_price) / rrp_price * 100) if rrp_price > 0 else 0
            if discount_pct > 95:
                issues.append(
                    {
                        "field": "pricing",
                        "issue": "unrealistic_discount",
                        "value": f"{discount_pct:.1f}%",
                        "severity": QualitySeverity.WARNING,
                    }
                )

        return issues


class ImageValidator:
    """Validate product images."""

    @staticmethod
    def validate_image_urls(product: Dict) -> List[Dict]:
        """Check image URLs for common issues."""
        issues = []

        image_fields = [
            "merchant_image_url",
            "aw_image_url",
            "large_image",
            "alternate_image",
            "alternate_image_two",
        ]

        for field in image_fields:
            url = product.get(field)
            if url:
                # Check for placeholder images
                if any(
                    placeholder in str(url).lower()
                    for placeholder in [
                        "no-image",
                        "noimage",
                        "placeholder",
                        "coming-soon",
                        "default",
                        "blank",
                    ]
                ):
                    issues.append(
                        {
                            "field": field,
                            "issue": "placeholder_image",
                            "severity": QualitySeverity.INFO,
                        }
                    )

                # Check for suspicious domains
                if any(
                    domain in str(url).lower()
                    for domain in ["dropbox.com", "drive.google.com", "temporary"]
                ):
                    issues.append(
                        {
                            "field": field,
                            "issue": "suspicious_image_host",
                            "severity": QualitySeverity.WARNING,
                        }
                    )

        # Check if no images at all
        has_any_image = any(product.get(field) for field in image_fields)
        if not has_any_image:
            issues.append(
                {"field": "images", "issue": "no_images", "severity": QualitySeverity.WARNING}
            )

        return issues
