"""Ingestion layer: downloads Olist dataset from Kaggle and validates raw files."""

import json
import logging
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ingestion")

DATASET_SLUG = "olistbr/brazilian-ecommerce"

EXPECTED_FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]

RAW_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))


def download_dataset(target_dir: Path) -> Path:
    """Download the Olist dataset ZIP from Kaggle API."""
    from kaggle.api.kaggle_api_extended import KaggleApi

    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Authenticating with Kaggle API...")
    api = KaggleApi()
    api.authenticate()

    logger.info("Downloading dataset: %s", DATASET_SLUG)
    api.dataset_download_files(DATASET_SLUG, path=str(target_dir), unzip=False)

    zip_path = target_dir / "brazilian-ecommerce.zip"
    if not zip_path.exists():
        zip_candidates = list(target_dir.glob("*.zip"))
        if zip_candidates:
            zip_path = zip_candidates[0]
        else:
            raise FileNotFoundError(f"No ZIP file found in {target_dir}")

    logger.info("Downloaded ZIP: %s (%.1f MB)", zip_path.name, zip_path.stat().st_size / 1e6)
    return zip_path


def extract_zip(zip_path: Path, target_dir: Path) -> list[Path]:
    """Extract all CSV files from the downloaded ZIP archive."""
    logger.info("Extracting %s...", zip_path.name)
    extracted = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member.endswith(".csv"):
                zf.extract(member, target_dir)
                extracted.append(target_dir / member)
                logger.info("  Extracted: %s", member)
    zip_path.unlink()
    logger.info("Removed ZIP archive, extracted %d files", len(extracted))
    return extracted


def validate_files(data_dir: Path) -> bool:
    """Verify all expected CSV files are present after extraction."""
    missing = [f for f in EXPECTED_FILES if not (data_dir / f).exists()]
    if missing:
        logger.error("Missing files: %s", missing)
        return False
    logger.info("All %d expected files present", len(EXPECTED_FILES))
    return True


def write_metadata(data_dir: Path) -> None:
    """Write ingestion metadata with timestamps and file sizes."""
    metadata = {
        "ingested_at": datetime.now(UTC).isoformat(),
        "dataset": DATASET_SLUG,
        "files": {},
    }
    for f in sorted(data_dir.glob("*.csv")):
        metadata["files"][f.name] = {
            "size_bytes": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=UTC).isoformat(),
        }

    meta_path = data_dir / "ingestion_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Metadata written to %s", meta_path)


def run_ingestion() -> None:
    """Execute the full ingestion pipeline."""
    logger.info("=" * 60)
    logger.info("INGESTION PIPELINE START")
    logger.info("=" * 60)

    if validate_files(RAW_DIR):
        logger.info("Raw data already exists, skipping download")
    else:
        zip_path = download_dataset(RAW_DIR)
        extract_zip(zip_path, RAW_DIR)
        if not validate_files(RAW_DIR):
            raise RuntimeError("Validation failed after extraction")

    write_metadata(RAW_DIR)
    logger.info("INGESTION COMPLETE")


if __name__ == "__main__":
    run_ingestion()
