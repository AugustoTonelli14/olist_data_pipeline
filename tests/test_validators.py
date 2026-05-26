"""Unit tests for the data validation module."""

import pandas as pd

from pipeline.validators import (
    check_accepted_values,
    check_min_rows,
    check_not_null,
    check_positive,
    check_unique,
)


class TestCheckNotNull:
    def test_passes_when_no_nulls(self):
        df = pd.DataFrame({"id": [1, 2, 3]})
        result = check_not_null(df, "id")
        assert result.passed

    def test_fails_when_nulls_exist(self):
        df = pd.DataFrame({"id": [1, None, 3]})
        result = check_not_null(df, "id")
        assert not result.passed


class TestCheckUnique:
    def test_passes_when_unique(self):
        df = pd.DataFrame({"id": [1, 2, 3]})
        result = check_unique(df, "id")
        assert result.passed

    def test_fails_when_duplicates(self):
        df = pd.DataFrame({"id": [1, 1, 3]})
        result = check_unique(df, "id")
        assert not result.passed


class TestCheckMinRows:
    def test_passes_above_threshold(self):
        df = pd.DataFrame({"a": range(100)})
        result = check_min_rows(df, 50)
        assert result.passed

    def test_fails_below_threshold(self):
        df = pd.DataFrame({"a": range(10)})
        result = check_min_rows(df, 50)
        assert not result.passed


class TestCheckAcceptedValues:
    def test_passes_with_valid_values(self):
        df = pd.DataFrame({"status": ["delivered", "shipped"]})
        result = check_accepted_values(df, "status", {"delivered", "shipped", "canceled"})
        assert result.passed

    def test_fails_with_invalid_values(self):
        df = pd.DataFrame({"status": ["delivered", "invalid"]})
        result = check_accepted_values(df, "status", {"delivered", "shipped"})
        assert not result.passed


class TestCheckPositive:
    def test_passes_with_positive_values(self):
        df = pd.DataFrame({"price": [10.0, 20.0, 0.0]})
        result = check_positive(df, "price")
        assert result.passed

    def test_fails_with_negative_values(self):
        df = pd.DataFrame({"price": [10.0, -5.0]})
        result = check_positive(df, "price")
        assert not result.passed
