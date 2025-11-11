#!/usr/bin/env python
"""
Test the product validation models with sample data.
"""

import sys
from pathlib import Path
from decimal import Decimal
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.product import ProductIngestion
from backend.models.quality import ContentModerator, PriceValidator


def test_valid_product():
    """Test with a valid product."""
    print("\n=== Testing Valid Product ===")

    data = {
        "aw_product_id": "AW123456",
        "merchant_product_id": "MERCH789",
        "merchant_id": 1234,
        "product_name": "Nike Air Max 90 Essential Mens Trainers",
        "description": "Classic Nike Air Max 90 trainers in black and white colorway",
        "search_price": "89.99",
        "rrp_price": "119.99",
        "brand_name": "Nike",
        "category_name": "Shoes",
        "merchant_image_url": "https://example.com/images/nike-air-max.jpg",
        "in_stock": "1",
        "colour": "Black/White",
        "Fashion:size": "UK 9",
        "Fashion:category": "Footwear",
    }

    try:
        product = ProductIngestion(**data)
        print(f"✓ Validation passed")
        print(f"  Quality Score: {product.quality_score:.2f}")
        print(f"  Dedup Hash: {product.dedup_hash[:16]}...")
        print(f"  Issues: {product.quality_issues}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")


def test_low_quality_product():
    """Test with a low quality product."""
    print("\n=== Testing Low Quality Product ===")

    data = {
        "aw_product_id": "AW999",
        "merchant_product_id": "BAD001",
        "merchant_id": 999,
        "product_name": "Product",  # Too short
        "search_price": "0.01",  # Suspiciously cheap
        "in_stock": "no",
    }

    try:
        product = ProductIngestion(**data)
        print(f"✓ Validation passed (with issues)")
        print(f"  Quality Score: {product.quality_score:.2f}")
        print(f"  Issues: {json.dumps(product.quality_issues, indent=2)}")

        # Check for spam
        spam_indicators = product.check_spam_indicators()
        if spam_indicators:
            print(f"  Spam Indicators: {spam_indicators}")

    except Exception as e:
        print(f"✗ Validation failed: {e}")


def test_price_validation():
    """Test price validation."""
    print("\n=== Testing Price Validation ===")

    test_cases = [
        {"search_price": Decimal("99.99"), "rrp_price": Decimal("149.99")},  # Good
        {"search_price": Decimal("0.001")},  # Too cheap
        {"search_price": Decimal("99999")},  # Too expensive
        {"search_price": Decimal("150"), "rrp_price": Decimal("100")},  # Price > RRP
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n  Test Case {i}: {case}")
        issues = PriceValidator.check_price_anomalies(case)
        if issues:
            print(f"    Issues: {issues}")
        else:
            print(f"    ✓ No issues")


def test_content_moderation():
    """Test content moderation."""
    print("\n=== Testing Content Moderation ===")

    products = [
        {"product_name": "Normal T-Shirt", "description": "Cotton t-shirt"},
        {"product_name": "CLICK HERE!!! BEST PRICE!!!", "description": "BUY NOW!!!"},
        {"product_name": "Adult Content", "category_name": "Adult"},
    ]

    for product in products:
        print(f"\n  Product: {product['product_name']}")

        # Check NSFW
        is_nsfw, reason = ContentModerator.check_nsfw(product)
        if is_nsfw:
            print(f"    ⚠ NSFW: {reason}")

        # Check spam
        spam_issues = ContentModerator.check_spam(product)
        if spam_issues:
            print(f"    ⚠ Spam: {spam_issues}")

        # Trust score
        trust = ContentModerator.calculate_trust_score(product)
        print(f"    Trust Score: {trust:.2f}")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Product Validation Tests")
    print("=" * 50)

    test_valid_product()
    test_low_quality_product()
    test_price_validation()
    test_content_moderation()

    print("\n" + "=" * 50)
    print("Tests Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
