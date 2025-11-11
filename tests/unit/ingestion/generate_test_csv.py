#!/usr/bin/env python
"""
Generate test CSV data for pipeline testing.
"""

import pandas as pd
import random
from pathlib import Path


def generate_test_csv(num_rows: int = 100, output_file: str = "data/test/test_products.csv"):
    """Generate test CSV with various data quality levels."""

    brands = ["Nike", "Adidas", "Puma", "Reebok", "Under Armour", None, "No Brand"]
    categories = ["Shoes", "Clothing", "Accessories", None]
    colors = ["Black", "White", "Red", "Blue", None]

    data = []

    for i in range(num_rows):
        # Mix of good and bad quality products
        quality = random.choice(["good", "medium", "poor"])

        if quality == "good":
            row = {
                "aw_product_id": f"AW{i:06d}",
                "merchant_product_id": f"MP{i:06d}",
                "product_name": f"{random.choice(brands)} Product {i}",
                "description": f"This is a detailed description for product {i}. It has multiple sentences.",
                "search_price": round(random.uniform(10, 200), 2),
                "rrp_price": round(random.uniform(15, 250), 2),
                "brand_name": random.choice(brands[:-2]),
                "category_name": random.choice(categories[:-1]),
                "merchant_image_url": f"https://example.com/images/product_{i}.jpg",
                "in_stock": random.choice(["1", "yes", "true"]),
                "colour": random.choice(colors[:-1]),
            }
        elif quality == "medium":
            row = {
                "aw_product_id": f"AW{i:06d}",
                "merchant_product_id": f"MP{i:06d}",
                "product_name": f"Product {i}",
                "search_price": round(random.uniform(5, 100), 2),
                "brand_name": random.choice(brands),
                "category_name": random.choice(categories),
                "in_stock": random.choice(["1", "0", None]),
            }
        else:  # poor quality
            row = {
                "aw_product_id": f"AW{i:06d}",
                "merchant_product_id": f"MP{i:06d}",
                "product_name": random.choice(["", "X", None, "CLICK HERE!!!"]),
                "search_price": random.choice([0.01, -10, None, 99999]),
            }

        # Add some duplicates
        if i % 20 == 0 and i > 0:
            row = data[i - 1].copy()
            row["merchant_product_id"] = f"DUP{i:06d}"

        data.append(row)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Add required merchant_id column
    df["merchant_id"] = 1001

    # Save to CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"Generated {num_rows} test products in {output_file}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")

    # Show sample
    print("\nSample data:")
    print(df.head())

    return output_path


if __name__ == "__main__":
    # Generate small test file
    generate_test_csv(100, "data/test/test_100.csv")

    # Generate medium test file
    generate_test_csv(10000, "data/test/test_10k.csv")

    print("\nTest files generated!")
