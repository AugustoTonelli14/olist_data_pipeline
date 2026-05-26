"""Cloud storage layer: uploads raw and processed data to S3-compatible storage.

Supports two modes via the CLOUD_PROVIDER env variable:
  - "local" (default): connects to a local MinIO instance via Docker
  - "aws": connects to real AWS S3 using credentials from .env
"""

import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("cloud_storage")

CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "local")
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))

RAW_BUCKET = os.getenv("S3_RAW_BUCKET", "olist-raw")
PROCESSED_BUCKET = os.getenv("S3_PROCESSED_BUCKET", "olist-processed")

# MinIO local defaults
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

# AWS credentials (used when CLOUD_PROVIDER=aws)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def get_s3_client():
    """Create an S3 client based on the configured cloud provider."""
    if CLOUD_PROVIDER == "local":
        logger.info("Connecting to MinIO at %s", MINIO_ENDPOINT)
        return boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
        )
    elif CLOUD_PROVIDER == "aws":
        logger.info("Connecting to AWS S3 (region: %s)", AWS_REGION)
        return boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION,
        )
    else:
        raise ValueError(
            f"Invalid CLOUD_PROVIDER: {CLOUD_PROVIDER}. Use 'local' or 'aws'."
        )


def ensure_bucket(client, bucket_name: str) -> None:
    """Create the S3 bucket if it does not already exist."""
    try:
        client.head_bucket(Bucket=bucket_name)
        logger.debug("Bucket %s already exists", bucket_name)
    except ClientError:
        logger.info("Creating bucket: %s", bucket_name)
        client.create_bucket(Bucket=bucket_name)


def upload_file(client, local_path: Path, bucket: str, s3_key: str) -> None:
    """Upload a single file to S3 and log the result."""
    size_mb = local_path.stat().st_size / 1e6
    client.upload_file(str(local_path), bucket, s3_key)
    logger.info(
        "Uploaded %s → s3://%s/%s (%.2f MB)",
        local_path.name,
        bucket,
        s3_key,
        size_mb,
    )


def upload_directory(
    client, local_dir: Path, bucket: str, pattern: str = "*"
) -> int:
    """Upload all matching files from a local directory to S3."""
    files = sorted(local_dir.glob(pattern))
    if not files:
        logger.warning("No files matching '%s' in %s", pattern, local_dir)
        return 0

    ensure_bucket(client, bucket)
    count = 0
    for f in files:
        if f.is_file() and f.name != ".gitkeep":
            upload_file(client, f, bucket, f.name)
            count += 1

    logger.info("Uploaded %d files to s3://%s/", count, bucket)
    return count


def upload_raw() -> int:
    """Upload raw CSV files to the raw data bucket."""
    logger.info("=" * 60)
    logger.info("UPLOADING RAW DATA TO S3")
    logger.info("=" * 60)
    client = get_s3_client()
    return upload_directory(client, RAW_DATA_DIR, RAW_BUCKET, "*.csv")


def upload_processed() -> int:
    """Upload processed Parquet files to the processed data bucket."""
    logger.info("=" * 60)
    logger.info("UPLOADING PROCESSED DATA TO S3")
    logger.info("=" * 60)
    client = get_s3_client()
    return upload_directory(
        client, PROCESSED_DATA_DIR, PROCESSED_BUCKET, "*.parquet"
    )


def list_bucket_contents(bucket: str) -> list[dict]:
    """List all objects in a bucket. Returns list of {key, size} dicts."""
    client = get_s3_client()
    try:
        response = client.list_objects_v2(Bucket=bucket)
        objects = response.get("Contents", [])
        return [{"key": o["Key"], "size": o["Size"]} for o in objects]
    except ClientError as e:
        logger.error("Failed to list bucket %s: %s", bucket, e)
        return []


if __name__ == "__main__":
    upload_raw()
    upload_processed()
