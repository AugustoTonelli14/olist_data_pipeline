"""Modeling layer: builds a star schema in DuckDB from processed Parquet files."""

import logging
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("modeling")

PROCESSED_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/olist.duckdb")


def get_connection() -> duckdb.DuckDBPyConnection:
    """Create or connect to the DuckDB database."""
    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(DUCKDB_PATH)
    logger.info("Connected to DuckDB: %s", DUCKDB_PATH)
    return conn


def build_dim_customers(conn: duckdb.DuckDBPyConnection) -> None:
    """Build the customer dimension table."""
    conn.execute("DROP TABLE IF EXISTS dim_customers")
    conn.execute(f"""
        CREATE TABLE dim_customers AS
        SELECT
            customer_id AS customer_key,
            customer_unique_id,
            customer_city,
            customer_state
        FROM read_parquet('{PROCESSED_DIR}/customers.parquet')
    """)
    count = conn.execute("SELECT COUNT(*) FROM dim_customers").fetchone()[0]
    logger.info("dim_customers: %d rows", count)


def build_dim_products(conn: duckdb.DuckDBPyConnection) -> None:
    """Build the product dimension table."""
    conn.execute("DROP TABLE IF EXISTS dim_products")
    conn.execute(f"""
        CREATE TABLE dim_products AS
        SELECT
            product_id AS product_key,
            product_category_name_english AS category_name,
            product_weight_g AS weight_g,
            product_length_cm AS length_cm,
            product_height_cm AS height_cm,
            product_width_cm AS width_cm,
            product_photos_qty AS photo_count
        FROM read_parquet('{PROCESSED_DIR}/products.parquet')
    """)
    count = conn.execute("SELECT COUNT(*) FROM dim_products").fetchone()[0]
    logger.info("dim_products: %d rows", count)


def build_dim_sellers(conn: duckdb.DuckDBPyConnection) -> None:
    """Build the seller dimension table."""
    conn.execute("DROP TABLE IF EXISTS dim_sellers")
    conn.execute(f"""
        CREATE TABLE dim_sellers AS
        SELECT
            seller_id AS seller_key,
            seller_city,
            seller_state
        FROM read_parquet('{PROCESSED_DIR}/sellers.parquet')
    """)
    count = conn.execute("SELECT COUNT(*) FROM dim_sellers").fetchone()[0]
    logger.info("dim_sellers: %d rows", count)


def build_dim_date(conn: duckdb.DuckDBPyConnection) -> None:
    """Build the date dimension from the range of order purchase dates."""
    conn.execute("DROP TABLE IF EXISTS dim_date")
    pq = f"{PROCESSED_DIR}/orders.parquet"
    conn.execute(f"""
        CREATE TABLE dim_date AS
        WITH date_range AS (
            SELECT UNNEST(
                generate_series(
                    (SELECT MIN(order_purchase_timestamp)::DATE
                     FROM read_parquet('{pq}')),
                    (SELECT MAX(order_purchase_timestamp)::DATE
                     FROM read_parquet('{pq}')),
                    INTERVAL '1 day'
                )
            ) AS full_date
        )
        SELECT
            CAST(strftime(full_date, '%Y%m%d') AS INTEGER) AS date_key,
            full_date::DATE AS full_date,
            YEAR(full_date) AS year,
            QUARTER(full_date) AS quarter,
            MONTH(full_date) AS month,
            DAY(full_date) AS day,
            DAYOFWEEK(full_date) AS day_of_week,
            strftime(full_date, '%B') AS month_name,
            CASE WHEN DAYOFWEEK(full_date) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend
        FROM date_range
    """)
    count = conn.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0]
    logger.info("dim_date: %d rows", count)


def build_dim_location(conn: duckdb.DuckDBPyConnection) -> None:
    """Build the location dimension from deduplicated geolocation data."""
    conn.execute("DROP TABLE IF EXISTS dim_location")
    conn.execute(f"""
        CREATE TABLE dim_location AS
        SELECT
            geolocation_zip_code_prefix AS location_key,
            geolocation_zip_code_prefix AS zip_code_prefix,
            geolocation_city AS city,
            geolocation_state AS state,
            geolocation_lat AS latitude,
            geolocation_lng AS longitude
        FROM read_parquet('{PROCESSED_DIR}/geolocation.parquet')
    """)
    count = conn.execute("SELECT COUNT(*) FROM dim_location").fetchone()[0]
    logger.info("dim_location: %d rows", count)


def build_fact_orders(conn: duckdb.DuckDBPyConnection) -> None:
    """Build the central fact table by joining orders, items, payments, and reviews."""
    conn.execute("DROP TABLE IF EXISTS fact_orders")
    conn.execute(f"""
        CREATE TABLE fact_orders AS
        WITH order_payments AS (
            SELECT
                order_id,
                payment_type,
                payment_installments,
                SUM(payment_value) AS payment_value
            FROM read_parquet('{PROCESSED_DIR}/payments.parquet')
            GROUP BY order_id, payment_type, payment_installments
        ),
        order_reviews AS (
            SELECT
                order_id,
                review_score,
                ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_creation_date DESC) AS rn
            FROM read_parquet('{PROCESSED_DIR}/reviews.parquet')
        )
        SELECT
            oi.order_id,
            o.customer_id AS customer_key,
            oi.seller_id AS seller_key,
            oi.product_id AS product_key,
            c.customer_zip_code_prefix AS location_key,
            CAST(strftime(o.order_purchase_timestamp, '%Y%m%d') AS INTEGER) AS date_key,
            o.order_status,
            COALESCE(p.payment_type, 'unknown') AS payment_type,
            COALESCE(p.payment_installments, 1) AS payment_installments,
            COALESCE(p.payment_value, 0.0) AS payment_value,
            oi.price,
            oi.freight_value,
            COALESCE(r.review_score, 0) AS review_score,
            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL
                     AND o.order_purchase_timestamp IS NOT NULL
                THEN DATE_DIFF('day',
                    o.order_purchase_timestamp::DATE,
                    o.order_delivered_customer_date::DATE)
                ELSE NULL
            END AS delivery_days,
            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL
                     AND o.order_estimated_delivery_date IS NOT NULL
                     AND o.order_delivered_customer_date <= o.order_estimated_delivery_date
                THEN TRUE
                ELSE FALSE
            END AS delivered_on_time
        FROM read_parquet('{PROCESSED_DIR}/order_items.parquet') oi
        JOIN read_parquet('{PROCESSED_DIR}/orders.parquet') o ON oi.order_id = o.order_id
        JOIN read_parquet('{PROCESSED_DIR}/customers.parquet') c ON o.customer_id = c.customer_id
        LEFT JOIN order_payments p ON o.order_id = p.order_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id AND r.rn = 1
    """)
    count = conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    logger.info("fact_orders: %d rows", count)


def run_modeling() -> None:
    """Build the complete star schema."""
    logger.info("=" * 60)
    logger.info("MODELING PIPELINE START")
    logger.info("=" * 60)

    parquet_files = list(PROCESSED_DIR.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No Parquet files in {PROCESSED_DIR}. Run transformation first.")

    conn = get_connection()

    build_dim_customers(conn)
    build_dim_products(conn)
    build_dim_sellers(conn)
    build_dim_date(conn)
    build_dim_location(conn)
    build_fact_orders(conn)

    tables = conn.execute("SHOW TABLES").fetchall()
    logger.info("Schema complete — tables: %s", [t[0] for t in tables])

    conn.close()
    logger.info("MODELING COMPLETE")


if __name__ == "__main__":
    run_modeling()
