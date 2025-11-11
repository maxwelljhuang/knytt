"""
Data Ingestion Package
Handles CSV data ingestion, validation, and processing for product data.
"""

from .csv_processor import CSVIngestionPipeline

__all__ = ["CSVIngestionPipeline"]
