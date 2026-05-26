"""Test suite for the Olist data pipeline — transformation and modeling validation."""

import os
from pathlib import Path

import duckdb
import pandas as pd
import pytest

PROCESSED_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/olist.duckdb")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def processed_dir():
    """Return processed data directory, skip if not populated."""
    if not PROCESSED_DIR.exists() or not list(PROCESSED_DIR.glob("*.parquet")):
        pytest.skip("Processed data not available — run transformation first")
    return PROCESSED_DIR


@pytest.fixture(scope="session")
def duckdb_conn():
    """Provide a read-only DuckDB connection, skip if DB missing."""
    if not Path(DUCKDB_PATH).exists():
        pytest.skip("DuckDB not available — run modeling first")
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def orders_df(processed_dir):
    return pd.read_parquet(processed_dir / "orders.parquet")


@pytest.fixture(scope="session")
def customers_df(processed_dir):
    return pd.read_parquet(processed_dir / "customers.parquet")


@pytest.fixture(scope="session")
def products_df(processed_dir):
    return pd.read_parquet(processed_dir / "products.parquet")


@pytest.fixture(scope="session")
def payments_df(processed_dir):
    return pd.read_parquet(processed_dir / "payments.parquet")


@pytest.fixture(scope="session")
def geolocation_df(processed_dir):
    return pd.read_parquet(processed_dir / "geolocation.parquet")


# ---------------------------------------------------------------------------
# Transformation tests
# ---------------------------------------------------------------------------


class TestTransformationOutput:
    """Validate the Parquet files produced by the transformation layer."""

    def test_all_parquet_files_exist(self, processed_dir):
        """All expected Parquet files must be present."""
        expected = [
            "orders.parquet",
            "order_items.parquet",
            "payments.parquet",
            "reviews.parquet",
            "customers.parquet",
            "sellers.parquet",
            "geolocation.parquet",
            "products.parquet",
        ]
        for f in expected:
            assert (processed_dir / f).exists(), f"Missing: {f}"

    def test_orders_row_count(self, orders_df):
        """Orders table should have at least 90k rows (Olist has ~99k)."""
        assert len(orders_df) >= 90_000, f"Expected >=90k orders, got {len(orders_df)}"

    def test_orders_no_null_order_id(self, orders_df):
        """Order ID must never be null — it's the primary key."""
        assert orders_df["order_id"].isna().sum() == 0

    def test_orders_dates_are_datetime(self, orders_df):
        """Purchase timestamp must be parsed as datetime."""
        assert pd.api.types.is_datetime64_any_dtype(orders_df["order_purchase_timestamp"])

    def test_customers_no_null_keys(self, customers_df):
        """Customer ID and unique ID must not be null."""
        assert customers_df["customer_id"].isna().sum() == 0
        assert customers_df["customer_unique_id"].isna().sum() == 0

    def test_products_have_english_category(self, products_df):
        """Products must have the English category name column after translation merge."""
        assert "product_category_name_english" in products_df.columns
        null_pct = products_df["product_category_name_english"].isna().mean()
        assert null_pct < 0.05, f"Too many null English categories: {null_pct:.1%}"

    def test_payments_positive_values(self, payments_df):
        """Payment values should be non-negative."""
        assert (payments_df["payment_value"] >= 0).all()

    def test_geolocation_deduplicated(self, geolocation_df):
        """Geolocation should have unique zip code prefixes after dedup."""
        dupes = geolocation_df["geolocation_zip_code_prefix"].duplicated().sum()
        assert dupes == 0, f"Found {dupes} duplicate zip codes"

    def test_string_columns_lowercased(self, customers_df):
        """String columns should be lowercase after cleaning."""
        sample_cities = customers_df["customer_city"].dropna().head(100)
        for city in sample_cities:
            assert city == city.lower(), f"City not lowercased: {city}"


# ---------------------------------------------------------------------------
# Modeling tests
# ---------------------------------------------------------------------------


class TestStarSchema:
    """Validate the DuckDB star schema."""

    def test_all_tables_exist(self, duckdb_conn):
        """All dimension and fact tables must exist."""
        tables = [t[0] for t in duckdb_conn.execute("SHOW TABLES").fetchall()]
        expected = [
            "dim_customers",
            "dim_products",
            "dim_sellers",
            "dim_date",
            "dim_location",
            "fact_orders",
        ]
        for t in expected:
            assert t in tables, f"Missing table: {t}"

    def test_fact_orders_row_count(self, duckdb_conn):
        """Fact table should have substantial row count."""
        count = duckdb_conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
        assert count >= 90_000, f"Expected >=90k fact rows, got {count}"

    def test_fact_orders_referential_integrity(self, duckdb_conn):
        """All customer keys in fact table should exist in dim_customers."""
        orphans = duckdb_conn.execute("""
            SELECT COUNT(*)
            FROM fact_orders f
            LEFT JOIN dim_customers c ON f.customer_key = c.customer_key
            WHERE c.customer_key IS NULL
        """).fetchone()[0]
        assert orphans == 0, f"Found {orphans} orphan customer keys"

    def test_dim_date_no_gaps(self, duckdb_conn):
        """Date dimension should cover continuous range without gaps."""
        result = duckdb_conn.execute("""
            SELECT
                MIN(full_date) AS min_date,
                MAX(full_date) AS max_date,
                COUNT(*) AS actual_days,
                DATE_DIFF('day', MIN(full_date), MAX(full_date)) + 1 AS expected_days
            FROM dim_date
        """).fetchone()
        assert result[2] == result[3], f"Date gaps: {result[3] - result[2]} missing days"

    def test_fact_delivery_days_reasonable(self, duckdb_conn):
        """Delivery days should be within a reasonable range (0–120)."""
        outliers = duckdb_conn.execute("""
            SELECT COUNT(*)
            FROM fact_orders
            WHERE delivery_days IS NOT NULL
              AND (delivery_days < 0 OR delivery_days > 120)
        """).fetchone()[0]
        total = duckdb_conn.execute(
            "SELECT COUNT(*) FROM fact_orders WHERE delivery_days IS NOT NULL"
        ).fetchone()[0]
        outlier_pct = outliers / max(total, 1)
        assert outlier_pct < 0.01, f"Too many delivery outliers: {outlier_pct:.1%}"
