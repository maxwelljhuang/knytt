"""
Google Cloud Storage utilities for ML artifacts.

This module provides functions to interact with GCS for downloading
and uploading ML artifacts like FAISS indices.
"""

import logging
import os
from pathlib import Path
from typing import Optional

try:
    from google.cloud import storage
    from google.api_core import exceptions as gcp_exceptions
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    logging.warning("google-cloud-storage not installed. GCS functionality will be disabled.")

logger = logging.getLogger(__name__)


class GCSError(Exception):
    """Base exception for GCS operations."""
    pass


def download_faiss_index_from_gcs(
    bucket_name: str,
    gcs_path: str,
    local_path: Path,
    required_files: Optional[list] = None
) -> bool:
    """
    Download FAISS index files from GCS to local directory.

    Args:
        bucket_name: Name of the GCS bucket
        gcs_path: Path prefix in GCS bucket (e.g., 'faiss_index')
        local_path: Local directory to download files to
        required_files: List of required files. Defaults to FAISS index files.

    Returns:
        True if all files downloaded successfully, False otherwise

    Raises:
        GCSError: If GCS operations fail critically
    """
    if not GCS_AVAILABLE:
        logger.error("google-cloud-storage library not available")
        return False

    if required_files is None:
        required_files = ['index.faiss', 'id_mapping.npz', 'metadata.npy']

    try:
        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # Create local directory if it doesn't exist
        local_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading FAISS index from gs://{bucket_name}/{gcs_path}/ to {local_path}")

        # Download each required file
        downloaded_files = []
        for filename in required_files:
            blob_path = f"{gcs_path}/{filename}" if gcs_path else filename
            blob = bucket.blob(blob_path)
            local_file_path = local_path / filename

            try:
                # Check if blob exists
                if not blob.exists():
                    logger.error(f"File not found in GCS: gs://{bucket_name}/{blob_path}")
                    return False

                # Download the file
                logger.info(f"Downloading {filename}...")
                blob.download_to_filename(str(local_file_path))

                # Verify file was created
                if not local_file_path.exists():
                    logger.error(f"Failed to create local file: {local_file_path}")
                    return False

                file_size = local_file_path.stat().st_size
                logger.info(f"✓ Downloaded {filename} ({file_size / 1024:.1f} KB)")
                downloaded_files.append(filename)

            except gcp_exceptions.NotFound:
                logger.error(f"File not found in GCS: gs://{bucket_name}/{blob_path}")
                return False
            except gcp_exceptions.Forbidden:
                logger.error(f"Access denied to gs://{bucket_name}/{blob_path}")
                return False
            except Exception as e:
                logger.error(f"Failed to download {filename}: {e}")
                return False

        logger.info(f"Successfully downloaded {len(downloaded_files)} files from GCS")
        return True

    except gcp_exceptions.NotFound:
        logger.error(f"Bucket not found: {bucket_name}")
        return False
    except gcp_exceptions.Forbidden:
        logger.error(f"Access denied to bucket: {bucket_name}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading FAISS index from GCS: {e}", exc_info=True)
        return False


def upload_faiss_index_to_gcs(
    local_path: Path,
    bucket_name: str,
    gcs_path: str,
    files_to_upload: Optional[list] = None
) -> bool:
    """
    Upload FAISS index files from local directory to GCS.

    Args:
        local_path: Local directory containing index files
        bucket_name: Name of the GCS bucket
        gcs_path: Path prefix in GCS bucket (e.g., 'faiss_index')
        files_to_upload: List of files to upload. Defaults to FAISS index files.

    Returns:
        True if all files uploaded successfully, False otherwise

    Raises:
        GCSError: If GCS operations fail critically
    """
    if not GCS_AVAILABLE:
        logger.error("google-cloud-storage library not available")
        return False

    if files_to_upload is None:
        files_to_upload = ['index.faiss', 'id_mapping.npz', 'metadata.npy']

    try:
        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        logger.info(f"Uploading FAISS index from {local_path} to gs://{bucket_name}/{gcs_path}/")

        # Upload each file
        uploaded_files = []
        for filename in files_to_upload:
            local_file_path = local_path / filename

            if not local_file_path.exists():
                logger.warning(f"Local file not found, skipping: {local_file_path}")
                continue

            blob_path = f"{gcs_path}/{filename}" if gcs_path else filename
            blob = bucket.blob(blob_path)

            try:
                logger.info(f"Uploading {filename}...")
                blob.upload_from_filename(str(local_file_path))

                file_size = local_file_path.stat().st_size
                logger.info(f"✓ Uploaded {filename} ({file_size / 1024:.1f} KB)")
                uploaded_files.append(filename)

            except Exception as e:
                logger.error(f"Failed to upload {filename}: {e}")
                return False

        if not uploaded_files:
            logger.error("No files were uploaded")
            return False

        logger.info(f"Successfully uploaded {len(uploaded_files)} files to GCS")
        return True

    except gcp_exceptions.Forbidden:
        logger.error(f"Access denied to bucket: {bucket_name}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading FAISS index to GCS: {e}", exc_info=True)
        return False


def delete_faiss_index_from_gcs(bucket_name: str, gcs_path: str) -> bool:
    """
    Delete FAISS index files from GCS.

    Args:
        bucket_name: Name of the GCS bucket
        gcs_path: Path prefix in GCS bucket

    Returns:
        True if deletion successful, False otherwise
    """
    if not GCS_AVAILABLE:
        logger.error("google-cloud-storage library not available")
        return False

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        required_files = ['index.faiss', 'id_mapping.npz', 'metadata.npy']
        deleted_files = []

        for filename in required_files:
            blob_path = f"{gcs_path}/{filename}" if gcs_path else filename
            blob = bucket.blob(blob_path)

            try:
                if blob.exists():
                    blob.delete()
                    logger.info(f"Deleted {filename} from GCS")
                    deleted_files.append(filename)
                else:
                    logger.debug(f"File not found (skipping): gs://{bucket_name}/{blob_path}")
            except Exception as e:
                logger.warning(f"Failed to delete {filename}: {e}")

        if deleted_files:
            logger.info(f"Deleted {len(deleted_files)} files from GCS: {deleted_files}")

        return True

    except Exception as e:
        logger.error(f"Error deleting FAISS index from GCS: {e}", exc_info=True)
        return False


def check_gcs_index_exists(bucket_name: str, gcs_path: str) -> bool:
    """
    Check if FAISS index files exist in GCS.

    Args:
        bucket_name: Name of the GCS bucket
        gcs_path: Path prefix in GCS bucket

    Returns:
        True if all required files exist, False otherwise
    """
    if not GCS_AVAILABLE:
        return False

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        required_files = ['index.faiss', 'id_mapping.npz', 'metadata.npy']

        for filename in required_files:
            blob_path = f"{gcs_path}/{filename}" if gcs_path else filename
            blob = bucket.blob(blob_path)

            if not blob.exists():
                logger.debug(f"GCS file not found: gs://{bucket_name}/{blob_path}")
                return False

        return True

    except Exception as e:
        logger.error(f"Error checking GCS index existence: {e}")
        return False
