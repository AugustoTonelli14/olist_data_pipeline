"""Tests for Parquet partitioning output."""

import os
from pathlib import Path

import pytest

PROCESSED_DIR = Path(os.getenv("PROCESSED_DATA_DIR", "data/processed"))


@pytest.fixture(scope="session")
def fact_orders_dir():
    """Return the partitioned fact_orders directory."""
    d = PROCESSED_DIR / "fact_orders"
    if not d.exists():
        pytest.skip("Partitioned fact_orders not available — run transformation first")
    return d


class TestPartitioning:
    """Validate partitioned Parquet output."""

    def test_partitioned_directory_exists(self, fact_orders_dir):
        """The fact_orders directory should exist."""
        assert fact_orders_dir.is_dir()

    def test_has_year_partitions(self, fact_orders_dir):
        """Should contain year= partition directories."""
        year_dirs = [
            d for d in fact_orders_dir.iterdir()
            if d.is_dir() and d.name.startswith("year=")
        ]
        assert len(year_dirs) >= 2, "Expected at least 2 year partitions"

    def test_has_month_partitions(self, fact_orders_dir):
        """Each year should contain month= partition directories."""
        year_dirs = [
            d for d in fact_orders_dir.iterdir()
            if d.is_dir() and d.name.startswith("year=")
        ]
        for year_dir in year_dirs:
            month_dirs = [
                d for d in year_dir.iterdir()
                if d.is_dir() and d.name.startswith("month=")
            ]
            assert len(month_dirs) >= 1, f"No month partitions in {year_dir.name}"

    def test_parquet_files_in_partitions(self, fact_orders_dir):
        """Leaf partition directories should contain .parquet files."""
        parquet_files = list(fact_orders_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 10, (
            f"Expected >=10 partition files, got {len(parquet_files)}"
        )
