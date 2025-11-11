#!/usr/bin/env python3
"""
Product Ingestion Script
Loads CSV product data into the database using the CSV ingestion pipeline.

Usage:
    python -m backend.scripts.ingest_products data/products.csv --merchant-id 1 --merchant-name "Test Merchant"

Or inside Docker:
    docker exec greenthumb-api python -m backend.scripts.ingest_products /app/data/test_sample.csv
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ingestion.csv_processor import CSVIngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run CSV ingestion."""
    parser = argparse.ArgumentParser(description="Ingest product data from CSV")
    parser.add_argument("csv_path", type=str, help="Path to CSV file containing product data")
    parser.add_argument("--merchant-id", type=int, default=1, help="Merchant ID (default: 1)")
    parser.add_argument(
        "--merchant-name",
        type=str,
        default="Default Merchant",
        help="Merchant name (default: Default Merchant)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Number of rows to process at once (default: 1000)",
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=0.3,
        help="Minimum quality score to accept products (0-1, default: 0.3)",
    )
    parser.add_argument(
        "--enable-dedup",
        action="store_true",
        default=True,
        help="Enable deduplication (default: True)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Run validation only without database writes"
    )

    args = parser.parse_args()

    # Validate CSV file exists
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        sys.exit(1)

    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    logger.info(f"Starting ingestion of {csv_path}")
    logger.info(f"Merchant: {args.merchant_name} (ID: {args.merchant_id})")
    logger.info(f"Chunk size: {args.chunk_size}, Quality threshold: {args.quality_threshold}")

    try:
        # Create ingestion pipeline
        pipeline = CSVIngestionPipeline(
            db_url=db_url,
            chunk_size=args.chunk_size,
            quality_threshold=args.quality_threshold,
            enable_dedup=args.enable_dedup,
        )

        # Process CSV file
        if args.dry_run:
            logger.info("Running in DRY RUN mode - no database writes")
            # For dry run, we'd need to modify the pipeline to support validation-only mode
            # For now, just read and validate the first chunk
            import pandas as pd

            df = pd.read_csv(str(csv_path), nrows=100)
            logger.info(f"CSV preview - Shape: {df.shape}")
            logger.info(f"Columns: {list(df.columns)}")
            logger.info(f"First row: {df.iloc[0].to_dict()}")
        else:
            stats = pipeline.process_csv(
                file_path=str(csv_path),
                merchant_id=args.merchant_id,
                merchant_name=args.merchant_name,
            )

            # Display results
            logger.info("=" * 60)
            logger.info("INGESTION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Total rows processed: {stats.get('total_rows', 0)}")
            logger.info(f"Valid products: {stats.get('valid_products', 0)}")
            logger.info(f"Invalid products: {stats.get('invalid_products', 0)}")
            logger.info(f"Duplicates found: {stats.get('duplicates', 0)}")
            logger.info(f"Products inserted: {stats.get('inserted', 0)}")
            logger.info(f"Products updated: {stats.get('updated', 0)}")
            logger.info(f"Quality issues: {stats.get('quality_issues', 0)}")
            logger.info(f"Processing time: {stats.get('processing_time', 0):.2f} seconds")

            if stats.get("errors"):
                logger.warning(f"Errors encountered: {len(stats['errors'])}")
                for error in stats["errors"][:5]:  # Show first 5 errors
                    logger.warning(f"  - {error}")

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
