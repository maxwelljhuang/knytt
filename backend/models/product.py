"""
Product validation models for CSV ingestion.
Handles validation, quality scoring, and deduplication prep.
"""

from pydantic import BaseModel, Field, field_validator, HttpUrl, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import hashlib
import re
from enum import Enum


class StockStatus(str, Enum):
    """Product stock status options."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"


class ProductIngestion(BaseModel):
    """
    Validates raw product data from CSV feeds.
    Maps directly to CSV columns from your merchant feeds.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,  # Auto-strip whitespace
        populate_by_name=True,  # Allow field aliases
        use_enum_values=True,  # Use string values for enums
    )

    # === REQUIRED FIELDS (will fail if missing) ===
    aw_product_id: str
    merchant_product_id: str
    merchant_id: int
    product_name: str

    # === IDENTIFIERS ===
    aw_deep_link: Optional[HttpUrl] = None
    merchant_deep_link: Optional[HttpUrl] = None
    basket_link: Optional[HttpUrl] = None

    # === CORE PRODUCT INFO ===
    description: Optional[str] = None
    product_short_description: Optional[str] = None
    specifications: Optional[str] = None
    product_model: Optional[str] = None
    model_number: Optional[str] = None
    keywords: Optional[str] = None
    promotional_text: Optional[str] = None
    product_type: Optional[str] = None

    # === CATEGORIZATION ===
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    category_name: Optional[str] = None
    category_id: Optional[int] = None
    merchant_product_category_path: Optional[str] = None
    merchant_product_second_category: Optional[str] = None
    merchant_product_third_category: Optional[str] = None

    # === PRICING (all converted to Decimal for accuracy) ===
    search_price: Optional[Decimal] = None
    store_price: Optional[Decimal] = None
    rrp_price: Optional[Decimal] = None
    base_price: Optional[Decimal] = None
    base_price_amount: Optional[Decimal] = None
    currency: str = Field(default="GBP")
    delivery_cost: Optional[Decimal] = None
    saving: Optional[Decimal] = None
    savings_percent: Optional[Decimal] = None
    product_price_old: Optional[Decimal] = None

    # === IMAGES ===
    merchant_image_url: Optional[HttpUrl] = None
    aw_image_url: Optional[HttpUrl] = None
    large_image: Optional[HttpUrl] = None
    merchant_thumb_url: Optional[HttpUrl] = None
    aw_thumb_url: Optional[HttpUrl] = None
    alternate_image: Optional[HttpUrl] = None
    alternate_image_two: Optional[HttpUrl] = None
    alternate_image_three: Optional[HttpUrl] = None
    alternate_image_four: Optional[HttpUrl] = None

    # === BRAND INFO ===
    brand_name: Optional[str] = None
    brand_id: Optional[int] = None

    # === FASHION SPECIFIC (using aliases for colon fields) ===
    fashion_suitable_for: Optional[str] = Field(None, alias="Fashion:suitable_for")
    fashion_category: Optional[str] = Field(None, alias="Fashion:category")
    fashion_size: Optional[str] = Field(None, alias="Fashion:size")
    fashion_material: Optional[str] = Field(None, alias="Fashion:material")
    fashion_pattern: Optional[str] = Field(None, alias="Fashion:pattern")
    fashion_swatch: Optional[str] = Field(None, alias="Fashion:swatch")
    colour: Optional[str] = None

    # === STOCK & AVAILABILITY ===
    in_stock: Optional[str] = None
    stock_quantity: Optional[int] = None
    stock_status: Optional[str] = None
    size_stock_status: Optional[str] = None
    size_stock_amount: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_for_sale: Optional[str] = None
    web_offer: Optional[str] = None
    pre_order: Optional[str] = None
    number_available: Optional[int] = None

    # === ADDITIONAL IDENTIFIERS ===
    ean: Optional[str] = None
    isbn: Optional[str] = None
    upc: Optional[str] = None
    mpn: Optional[str] = None
    parent_product_id: Optional[str] = None
    product_gtin: Optional[str] = None

    # === CUSTOM FIELDS ===
    custom_1: Optional[str] = None
    custom_2: Optional[str] = None
    custom_3: Optional[str] = None
    custom_4: Optional[str] = None
    custom_5: Optional[str] = None
    custom_6: Optional[str] = None
    custom_7: Optional[str] = None
    custom_8: Optional[str] = None
    custom_9: Optional[str] = None

    # === REVIEWS & RATINGS ===
    reviews: Optional[int] = None
    average_rating: Optional[Decimal] = None
    rating: Optional[Decimal] = None

    # === SHIPPING & DELIVERY ===
    delivery_restrictions: Optional[str] = None
    delivery_weight: Optional[Decimal] = None
    delivery_time: Optional[str] = None
    warranty: Optional[str] = None
    terms_of_contract: Optional[str] = None
    condition: Optional[str] = None

    # === METADATA ===
    last_updated: Optional[datetime] = None
    data_feed_id: Optional[str] = None
    language: Optional[str] = None
    commission_group: Optional[str] = None

    # === CALCULATED FIELDS (not in CSV) ===
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_issues: List[Dict[str, Any]] = Field(default_factory=list)
    is_valid: bool = Field(default=True)
    dedup_hash: Optional[str] = None

    # === VALIDATORS ===

    @field_validator(
        "aw_product_id",
        "merchant_product_id",
        "data_feed_id",
        "is_for_sale",
        "web_offer",
        "pre_order",
        "commission_group",
        mode="before",
    )
    @classmethod
    def convert_to_string(cls, v):
        """Convert numeric values to strings."""
        if v is None or v == "":
            return None
        return str(v)

    @field_validator("brand_id", "category_id", mode="before")
    @classmethod
    def convert_to_int(cls, v):
        """Convert string IDs to integers."""
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator(
        "search_price",
        "store_price",
        "rrp_price",
        "delivery_cost",
        "saving",
        "base_price",
        "product_price_old",
        mode="before",
    )
    @classmethod
    def clean_price(cls, v):
        """Clean and validate price fields."""
        if v is None or v == "" or v == "N/A":
            return None

        if isinstance(v, str):
            # Remove currency symbols and whitespace
            v = re.sub(r"[£$€,\s]", "", v)
            if not v:
                return None

            try:
                return Decimal(v)
            except:
                return None

        try:
            return Decimal(str(v))
        except:
            return None

    @field_validator("in_stock", mode="before")
    @classmethod
    def parse_in_stock(cls, v):
        """Parse various in_stock representations."""
        if v is None:
            return None

        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower in ["1", "true", "yes", "y", "in stock", "available"]:
                return "yes"
            elif v_lower in ["0", "false", "no", "n", "out of stock", "unavailable"]:
                return "no"

        return str(v) if v else None

    @field_validator("stock_quantity", mode="before")
    @classmethod
    def parse_stock_quantity(cls, v):
        """Parse stock quantity, handling various formats."""
        if v is None or v == "":
            return None

        if isinstance(v, str):
            # Extract numbers from strings like "10 in stock"
            match = re.search(r"\d+", v)
            if match:
                return int(match.group())

        try:
            return int(v)
        except:
            return None

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, v, info):
        """Validate product name and flag issues."""
        if not v or len(v.strip()) < 2:
            if "quality_issues" not in info.data:
                info.data["quality_issues"] = []
            info.data["quality_issues"].append(
                {"field": "product_name", "issue": "too_short", "severity": "critical"}
            )
            raise ValueError("Product name too short")

        # Check for spam patterns
        spam_patterns = [
            r"(click here|buy now|limited time)",
            r"(\$\$\$|!!!|###){3,}",
            r"(FREE SHIPPING){2,}",
        ]

        v_lower = v.lower()
        for pattern in spam_patterns:
            if re.search(pattern, v_lower, re.IGNORECASE):
                if "quality_issues" not in info.data:
                    info.data["quality_issues"] = []
                info.data["quality_issues"].append(
                    {"field": "product_name", "issue": "spam_pattern", "severity": "warning"}
                )

        return v

    @field_validator("merchant_image_url", "aw_image_url", "large_image", mode="before")
    @classmethod
    def validate_image_url(cls, v):
        """Validate and clean image URLs."""
        if not v or v == "N/A" or v == "":
            return None

        # Basic URL cleaning
        if isinstance(v, str):
            v = v.strip()
            if not v.startswith(("http://", "https://")):
                # Try to fix common issues
                if v.startswith("//"):
                    v = "https:" + v
                elif v.startswith("www."):
                    v = "https://" + v
                else:
                    return None  # Invalid URL

        return v

    # === METHODS ===

    def calculate_quality_score(self) -> float:
        """
        Calculate quality score based on data completeness.
        Returns score between 0.0 and 1.0.
        """
        score = 0.0

        # Weight distribution for different fields
        weights = {
            "product_name": 0.15,
            "description": 0.10,
            "search_price": 0.15,
            "merchant_image_url": 0.15,
            "brand_name": 0.10,
            "category_name": 0.05,
            "in_stock": 0.05,
            "merchant_name": 0.05,
            "colour": 0.05,
            "has_multiple_images": 0.05,
            "has_reviews": 0.05,
            "has_savings_info": 0.05,
        }

        # Check each field
        if self.product_name and len(self.product_name) > 5:
            score += weights["product_name"]

        if self.description and len(self.description) > 20:
            score += weights["description"]

        if self.search_price and self.search_price > 0:
            score += weights["search_price"]

        if self.merchant_image_url or self.aw_image_url:
            score += weights["merchant_image_url"]

        if self.brand_name:
            score += weights["brand_name"]

        if self.category_name or self.merchant_category:
            score += weights["category_name"]

        if self.in_stock:
            score += weights["in_stock"]

        if self.merchant_name:
            score += weights["merchant_name"]

        if self.colour:
            score += weights["colour"]

        # Bonus for multiple images
        image_count = sum(
            1
            for img in [
                self.merchant_image_url,
                self.aw_image_url,
                self.large_image,
                self.alternate_image,
                self.alternate_image_two,
            ]
            if img
        )
        if image_count >= 2:
            score += weights["has_multiple_images"]

        # Bonus for reviews
        if self.reviews and self.reviews > 0:
            score += weights["has_reviews"]

        # Bonus for savings information
        if self.rrp_price and self.search_price and self.rrp_price > self.search_price:
            score += weights["has_savings_info"]

        # Cap at 1.0
        self.quality_score = min(score, 1.0)
        return self.quality_score

    def generate_dedup_hash(self) -> str:
        """
        Generate hash for deduplication.
        Uses key fields to identify similar products.
        """
        # Normalize key fields for consistent hashing
        key_parts = []

        # Brand (normalized)
        if self.brand_name:
            brand = re.sub(r"[^a-z0-9]", "", self.brand_name.lower())
            key_parts.append(brand)

        # Product name (first 50 chars, normalized)
        if self.product_name:
            name = re.sub(r"[^a-z0-9]", "", self.product_name.lower())[:50]
            key_parts.append(name)

        # Color (normalized)
        if self.colour:
            color = re.sub(r"[^a-z]", "", self.colour.lower())
            key_parts.append(color)

        # Size (for fashion)
        if self.fashion_size:
            size = self.fashion_size.upper().replace(" ", "")
            key_parts.append(size)

        # Model number (if available)
        if self.model_number:
            key_parts.append(self.model_number.upper())

        # Create hash
        hash_input = "|".join(key_parts)
        self.dedup_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        return self.dedup_hash

    def get_alternate_images(self) -> List[str]:
        """Collect all alternate image URLs."""
        images = []
        for field in [
            "alternate_image",
            "alternate_image_two",
            "alternate_image_three",
            "alternate_image_four",
        ]:
            img = getattr(self, field)
            if img:
                images.append(str(img))
        return images

    def check_spam_indicators(self) -> List[str]:
        """Check for spam/low-quality content indicators."""
        spam_indicators = []

        # Check product name
        if self.product_name:
            if len(self.product_name) > 200:
                spam_indicators.append("excessive_title_length")

            if self.product_name.isupper():
                spam_indicators.append("all_caps_title")

            spam_keywords = ["viagra", "casino", "forex", "bitcoin", "cbd"]
            for keyword in spam_keywords:
                if keyword in self.product_name.lower():
                    spam_indicators.append(f"spam_keyword_{keyword}")

        # Check description
        if self.description:
            if self.description.count("!") > 5:
                spam_indicators.append("excessive_exclamation")

            if len(re.findall(r"https?://", self.description)) > 3:
                spam_indicators.append("excessive_links_in_description")

        # Price anomalies
        if self.search_price:
            if self.search_price < Decimal("0.01"):
                spam_indicators.append("suspiciously_low_price")

            if self.search_price > Decimal("100000"):
                spam_indicators.append("suspiciously_high_price")

        return spam_indicators

    def is_fashion_product(self) -> bool:
        """Determine if this is a fashion product."""
        fashion_indicators = [
            self.fashion_category,
            self.fashion_size,
            self.fashion_material,
            self.fashion_suitable_for,
        ]
        return any(fashion_indicators)

    def model_post_init(self, __context):
        """Run after model initialization."""
        # Calculate quality score
        self.calculate_quality_score()

        # Generate deduplication hash
        self.generate_dedup_hash()

        # Check for spam
        spam_indicators = self.check_spam_indicators()
        if spam_indicators:
            self.quality_issues.append(
                {
                    "field": "general",
                    "issue": "spam_indicators",
                    "details": spam_indicators,
                    "severity": "warning",
                }
            )


class ProductCanonical(BaseModel):
    """
    Canonical product model for database storage.
    This is the cleaned, validated version ready for the database.
    """

    # Core fields (matching database schema)
    id: Optional[str] = None
    merchant_product_id: str
    merchant_id: int
    product_name: str

    # All other fields from database
    merchant_name: Optional[str] = None
    aw_product_id: Optional[str] = None
    brand_name: Optional[str] = None
    brand_id: Optional[int] = None
    description: Optional[str] = None
    category_name: Optional[str] = None
    category_id: Optional[int] = None

    # Prices
    search_price: Optional[Decimal] = None
    store_price: Optional[Decimal] = None
    rrp_price: Optional[Decimal] = None
    currency: str = "GBP"

    # Images
    merchant_image_url: Optional[str] = None
    aw_image_url: Optional[str] = None
    alternate_images: List[str] = Field(default_factory=list)

    # Fashion attributes
    fashion_category: Optional[str] = None
    fashion_size: Optional[str] = None
    colour: Optional[str] = None

    # Stock
    in_stock: bool = True
    stock_quantity: Optional[int] = None

    # Quality and deduplication
    quality_score: float
    quality_issues: List[Dict] = Field(default_factory=list)
    dedup_hash: str
    is_duplicate: bool = False
    canonical_product_id: Optional[str] = None

    @classmethod
    def from_ingestion(cls, ingestion: ProductIngestion) -> "ProductCanonical":
        """Create canonical product from ingestion model."""
        return cls(
            merchant_product_id=ingestion.merchant_product_id,
            merchant_id=ingestion.merchant_id,
            product_name=ingestion.product_name,
            merchant_name=ingestion.merchant_name,
            aw_product_id=ingestion.aw_product_id,
            brand_name=ingestion.brand_name,
            brand_id=ingestion.brand_id,
            description=ingestion.description,
            category_name=ingestion.category_name,
            category_id=ingestion.category_id,
            search_price=ingestion.search_price,
            store_price=ingestion.store_price,
            rrp_price=ingestion.rrp_price,
            currency=ingestion.currency,
            merchant_image_url=(
                str(ingestion.merchant_image_url) if ingestion.merchant_image_url else None
            ),
            aw_image_url=str(ingestion.aw_image_url) if ingestion.aw_image_url else None,
            alternate_images=ingestion.get_alternate_images(),
            fashion_category=ingestion.fashion_category,
            fashion_size=ingestion.fashion_size,
            colour=ingestion.colour,
            in_stock=ingestion.in_stock == "yes" if ingestion.in_stock else True,
            stock_quantity=ingestion.stock_quantity,
            quality_score=ingestion.quality_score,
            quality_issues=ingestion.quality_issues,
            dedup_hash=ingestion.dedup_hash,
        )
