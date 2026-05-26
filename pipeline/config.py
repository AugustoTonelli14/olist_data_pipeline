"""Shared configuration and logging setup for the pipeline."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/olist.duckdb")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DATASET_SLUG = "olistbr/brazilian-ecommerce"

EXPECTED_RAW_FILES = [
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


def setup_logging(name: str) -> logging.Logger:
    """Configure and return a named logger with consistent formatting."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    return logging.getLogger(name)
