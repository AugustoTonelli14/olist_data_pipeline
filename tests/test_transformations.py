"""Unit tests for individual transformation functions."""

import pandas as pd

from transformation.transform import (
    cast_dates,
    cast_numerics,
    clean_strings,
    deduplicate,
    transform_geolocation,
    transform_payments,
    transform_reviews,
)


class TestCleanStrings:
    """Tests for the string cleaning function."""

    def test_strips_whitespace(self):
        df = pd.DataFrame({"city": ["  São Paulo  ", "  Rio  "]})
        result = clean_strings(df)
        assert result["city"].tolist() == ["são paulo", "rio"]

    def test_lowercases_strings(self):
        df = pd.DataFrame({"name": ["HELLO", "World", "tEsT"]})
        result = clean_strings(df)
        assert result["name"].tolist() == ["hello", "world", "test"]

    def test_preserves_numeric_columns(self):
        df = pd.DataFrame({"value": [1.5, 2.0], "label": ["A", "B"]})
        result = clean_strings(df)
        assert result["value"].tolist() == [1.5, 2.0]


class TestCastDates:
    """Tests for date parsing."""

    def test_parses_valid_dates(self):
        df = pd.DataFrame({"dt": ["2023-01-15 10:30:00", "2023-06-20 14:00:00"]})
        result = cast_dates(df, ["dt"])
        assert pd.api.types.is_datetime64_any_dtype(result["dt"])

    def test_coerces_invalid_dates_to_nat(self):
        df = pd.DataFrame({"dt": ["2023-01-15", "not_a_date", None]})
        result = cast_dates(df, ["dt"])
        assert result["dt"].isna().sum() == 2

    def test_ignores_missing_columns(self):
        df = pd.DataFrame({"other": [1, 2]})
        result = cast_dates(df, ["nonexistent"])
        assert "other" in result.columns


class TestCastNumerics:
    """Tests for numeric coercion."""

    def test_coerces_string_numbers(self):
        df = pd.DataFrame({"price": ["10.5", "20.0", "30"]})
        result = cast_numerics(df, ["price"])
        assert result["price"].dtype == float

    def test_coerces_invalid_to_nan(self):
        df = pd.DataFrame({"price": ["10.5", "abc", None]})
        result = cast_numerics(df, ["price"])
        assert result["price"].isna().sum() == 2


class TestDeduplicate:
    """Tests for deduplication."""

    def test_removes_exact_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
        result = deduplicate(df, "test")
        assert len(result) == 2

    def test_no_change_when_no_duplicates(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = deduplicate(df, "test")
        assert len(result) == 3


class TestTransformPayments:
    """Tests for payment-specific transformations."""

    def test_fills_null_payment_type(self):
        df = pd.DataFrame({
            "payment_type": ["credit_card", None, "boleto"],
            "payment_sequential": [1, 1, 1],
            "payment_installments": [3, 1, 1],
            "payment_value": [100.0, 50.0, 75.0],
        })
        result = transform_payments(df)
        assert result["payment_type"].isna().sum() == 0
        assert result.loc[1, "payment_type"] == "unknown"


class TestTransformReviews:
    """Tests for review-specific transformations."""

    def test_fills_null_comments(self):
        df = pd.DataFrame({
            "review_comment_title": ["good", None],
            "review_comment_message": [None, "great"],
            "review_creation_date": ["2023-01-01", "2023-02-01"],
            "review_answer_timestamp": ["2023-01-02", "2023-02-02"],
        })
        result = transform_reviews(df)
        assert result["review_comment_title"].iloc[1] == ""
        assert result["review_comment_message"].iloc[0] == ""


class TestTransformGeolocation:
    """Tests for geolocation deduplication."""

    def test_keeps_one_per_zip_code(self):
        df = pd.DataFrame({
            "geolocation_zip_code_prefix": ["01001", "01001", "02002"],
            "geolocation_lat": [-23.5, -23.6, -22.9],
            "geolocation_lng": [-46.6, -46.7, -43.2],
            "geolocation_city": ["sp", "sp", "rj"],
            "geolocation_state": ["sp", "sp", "rj"],
        })
        result = transform_geolocation(df)
        assert len(result) == 2
        assert result["geolocation_zip_code_prefix"].nunique() == 2
