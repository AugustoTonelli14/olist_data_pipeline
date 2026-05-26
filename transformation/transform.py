"""Transformation layer: cleans, casts, deduplicates, and outputs Parquet files."""

import logging
import os
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("transformation")

RAW_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))

DATE_COLUMNS = {
    "olist_orders_dataset": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_order_reviews_dataset": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
}

NUMERIC_COLUMNS = {
    "olist_order_items_dataset": ["price", "freight_value"],
    "olist_order_payments_dataset": ["payment_sequential", "payment_installments", "payment_value"],
    "olist_products_dataset": [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
}


def load_raw_csv(filename: str) -> pd.DataFrame:
    """Load a CSV from the raw data directory."""
    path = RAW_DIR / filename
    df = pd.read_csv(path, low_memory=False)
    logger.info("Loaded %s: %d rows x %d cols", filename, len(df), len(df.columns))
    return df


def clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and normalize string columns to lowercase."""
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip().str.lower()
    return df


def cast_dates(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Parse date strings into datetime objects."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            null_count = df[col].isna().sum()
            if null_count > 0:
                logger.warning("  %s: %d null values after date parsing", col, null_count)
    return df


def cast_numerics(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Coerce numeric columns and fill missing with 0 where appropriate."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def deduplicate(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Remove exact duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed > 0:
        logger.info("  %s: removed %d duplicate rows", name, removed)
    return df


def transform_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Apply order-specific transformations."""
    df = cast_dates(df, DATE_COLUMNS["olist_orders_dataset"])
    df["order_status"] = df["order_status"].fillna("unknown")
    return df


def transform_order_items(df: pd.DataFrame) -> pd.DataFrame:
    """Apply order items transformations."""
    df = cast_numerics(df, NUMERIC_COLUMNS["olist_order_items_dataset"])
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    return df


def transform_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Apply payment-specific transformations."""
    df = cast_numerics(df, NUMERIC_COLUMNS["olist_order_payments_dataset"])
    df["payment_type"] = df["payment_type"].fillna("unknown")
    return df


def transform_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Apply review-specific transformations."""
    df = cast_dates(df, DATE_COLUMNS["olist_order_reviews_dataset"])
    df["review_comment_title"] = df["review_comment_title"].fillna("")
    df["review_comment_message"] = df["review_comment_message"].fillna("")
    return df


def transform_products(df: pd.DataFrame, translations: pd.DataFrame) -> pd.DataFrame:
    """Merge English category names and clean product dimensions."""
    df = cast_numerics(df, NUMERIC_COLUMNS["olist_products_dataset"])
    df = df.merge(translations, on="product_category_name", how="left")
    df["product_category_name_english"] = df["product_category_name_english"].fillna("other")
    return df


def transform_geolocation(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate geolocations — keep one entry per zip code prefix."""
    df = df.drop_duplicates(subset=["geolocation_zip_code_prefix"], keep="first")
    logger.info("  Geolocation deduplicated to %d unique zip codes", len(df))
    return df


def save_parquet(df: pd.DataFrame, name: str) -> Path:
    """Write DataFrame to Parquet in the processed directory."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False, engine="pyarrow")
    size_mb = path.stat().st_size / 1e6
    logger.info("Saved %s: %d rows, %.2f MB", path.name, len(df), size_mb)
    return path


def save_partitioned_parquet(
    df: pd.DataFrame, name: str, partition_cols: list[str]
) -> Path:
    """Write DataFrame as a partitioned Parquet dataset using PyArrow."""
    output_dir = PROCESSED_DIR / name
    output_dir.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_to_dataset(
        table,
        root_path=str(output_dir),
        partition_cols=partition_cols,
    )
    total_files = len(list(output_dir.rglob("*.parquet")))
    logger.info(
        "Saved partitioned %s: %d rows, %d partitions, cols=%s",
        name,
        len(df),
        total_files,
        partition_cols,
    )
    return output_dir


def build_fact_orders_parquet(datasets: dict[str, pd.DataFrame]) -> None:
    """Build a denormalized fact_orders DataFrame and save as partitioned Parquet."""
    logger.info("Building partitioned fact_orders Parquet...")
    orders = datasets["orders"]
    items = datasets["order_items"]
    payments = datasets["payments"]
    reviews = datasets["reviews"]
    customers = datasets["customers"]

    # Aggregate payments per order
    pay_agg = (
        payments.groupby("order_id")
        .agg(
            payment_type=("payment_type", "first"),
            payment_installments=("payment_installments", "first"),
            payment_value=("payment_value", "sum"),
        )
        .reset_index()
    )

    # Keep latest review per order
    rev_dedup = (
        reviews.sort_values("review_creation_date", ascending=False)
        .drop_duplicates(subset=["order_id"], keep="first")[
            ["order_id", "review_score"]
        ]
    )

    # Build fact
    fact = items.merge(orders, on="order_id", how="inner")
    fact = fact.merge(
        customers[["customer_id", "customer_zip_code_prefix"]],
        on="customer_id",
        how="inner",
    )
    fact = fact.merge(pay_agg, on="order_id", how="left")
    fact = fact.merge(rev_dedup, on="order_id", how="left")

    # Derived columns
    fact["review_score"] = fact["review_score"].fillna(0).astype(int)
    fact["payment_type"] = fact["payment_type"].fillna("unknown")
    fact["payment_installments"] = (
        fact["payment_installments"].fillna(1).astype(int)
    )
    fact["payment_value"] = fact["payment_value"].fillna(0.0)

    # Extract year/month for partitioning
    fact["year"] = fact["order_purchase_timestamp"].dt.year.astype("Int64")
    fact["month"] = fact["order_purchase_timestamp"].dt.month.astype("Int64")

    # Drop rows without valid dates (needed for partitioning)
    fact = fact.dropna(subset=["year", "month"])
    fact["year"] = fact["year"].astype(int)
    fact["month"] = fact["month"].astype(int)

    save_partitioned_parquet(fact, "fact_orders", ["year", "month"])


def run_transformation() -> dict[str, pd.DataFrame]:
    """Execute all transformations and return processed DataFrames."""
    logger.info("=" * 60)
    logger.info("TRANSFORMATION PIPELINE START")
    logger.info("=" * 60)

    translations = load_raw_csv("product_category_name_translation.csv")
    translations = clean_strings(translations)

    datasets = {}
    transforms = {
        "orders": ("olist_orders_dataset.csv", transform_orders),
        "order_items": ("olist_order_items_dataset.csv", transform_order_items),
        "payments": ("olist_order_payments_dataset.csv", transform_payments),
        "reviews": ("olist_order_reviews_dataset.csv", transform_reviews),
        "customers": ("olist_customers_dataset.csv", None),
        "sellers": ("olist_sellers_dataset.csv", None),
        "geolocation": ("olist_geolocation_dataset.csv", transform_geolocation),
    }

    for name, (filename, transform_fn) in transforms.items():
        logger.info("Processing: %s", name)
        df = load_raw_csv(filename)
        df = clean_strings(df)
        df = deduplicate(df, name)

        if name == "products":
            df = transform_fn(df, translations)
        elif transform_fn:
            df = transform_fn(df)

        save_parquet(df, name)
        datasets[name] = df

    # Products handled separately due to translation merge
    logger.info("Processing: products")
    df_products = load_raw_csv("olist_products_dataset.csv")
    df_products = clean_strings(df_products)
    df_products = deduplicate(df_products, "products")
    df_products = transform_products(df_products, translations)
    save_parquet(df_products, "products")
    datasets["products"] = df_products

    save_parquet(translations, "category_translations")
    datasets["translations"] = translations

    # Build partitioned fact_orders Parquet (year/month partitioning)
    build_fact_orders_parquet(datasets)

    logger.info("TRANSFORMATION COMPLETE — %d datasets processed", len(datasets))
    return datasets


if __name__ == "__main__":
    run_transformation()
