"""Data validation contracts for pipeline quality gates."""

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger("validators")


@dataclass
class ValidationResult:
    """Outcome of a single validation check."""

    name: str
    passed: bool
    message: str


def check_not_null(df: pd.DataFrame, column: str) -> ValidationResult:
    """Verify a column has no null values."""
    null_count = df[column].isna().sum()
    passed = null_count == 0
    return ValidationResult(
        name=f"not_null:{column}",
        passed=passed,
        message=f"{null_count} nulls found" if not passed else "OK",
    )


def check_unique(df: pd.DataFrame, column: str) -> ValidationResult:
    """Verify a column has no duplicate values."""
    dupe_count = df[column].duplicated().sum()
    passed = dupe_count == 0
    return ValidationResult(
        name=f"unique:{column}",
        passed=passed,
        message=f"{dupe_count} duplicates found" if not passed else "OK",
    )


def check_min_rows(df: pd.DataFrame, min_count: int) -> ValidationResult:
    """Verify a DataFrame has at least min_count rows."""
    actual = len(df)
    passed = actual >= min_count
    return ValidationResult(
        name=f"min_rows:{min_count}",
        passed=passed,
        message=f"Expected >={min_count}, got {actual}" if not passed else "OK",
    )


def check_accepted_values(
    df: pd.DataFrame, column: str, accepted: set[str]
) -> ValidationResult:
    """Verify all values in a column are within an accepted set."""
    invalid = set(df[column].dropna().unique()) - accepted
    passed = len(invalid) == 0
    return ValidationResult(
        name=f"accepted_values:{column}",
        passed=passed,
        message=f"Invalid values: {invalid}" if not passed else "OK",
    )


def check_positive(df: pd.DataFrame, column: str) -> ValidationResult:
    """Verify all values in a numeric column are non-negative."""
    negative_count = (df[column].dropna() < 0).sum()
    passed = negative_count == 0
    return ValidationResult(
        name=f"positive:{column}",
        passed=passed,
        message=f"{negative_count} negative values" if not passed else "OK",
    )


def run_validations(
    df: pd.DataFrame, checks: list[ValidationResult]
) -> list[ValidationResult]:
    """Run a list of pre-computed validation results and log outcomes."""
    failures = [c for c in checks if not c.passed]
    for check in checks:
        level = logging.WARNING if not check.passed else logging.DEBUG
        status = "FAIL" if not check.passed else "PASS"
        logger.log(level, "  [%s] %s — %s", status, check.name, check.message)

    if failures:
        logger.warning("%d/%d validations failed", len(failures), len(checks))
    else:
        logger.info("All %d validations passed", len(checks))

    return failures
