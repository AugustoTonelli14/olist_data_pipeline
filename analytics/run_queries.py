"""Analytics runner: executes SQL queries against the DuckDB star schema."""

import logging
import os
import re
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("analytics")

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/olist.duckdb")
QUERIES_PATH = Path("analytics/queries.sql")


def parse_queries(sql_path: Path) -> list[tuple[str, str]]:
    """Parse the SQL file into (comment_header, query) tuples.

    Splits on lines starting with '-- Q' to separate individual queries.
    """
    content = sql_path.read_text(encoding="utf-8")
    chunks = re.split(r"\n(?=-- Q\d+:)", content)

    queries = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        lines = chunk.split("\n")
        comment_lines = []
        sql_lines = []
        in_sql = False

        for line in lines:
            stripped = line.strip()
            if not in_sql and stripped.startswith("--"):
                cleaned = stripped.lstrip("- ").strip()
                if cleaned:
                    comment_lines.append(cleaned)
            elif stripped:
                in_sql = True
                sql_lines.append(line)
            elif in_sql:
                sql_lines.append(line)

        comment = "\n".join(comment_lines)
        sql = "\n".join(sql_lines).strip().rstrip(";")

        if comment and sql:
            queries.append((comment, sql))

    return queries


def run_queries() -> None:
    """Execute all analytics queries and print results."""
    logger.info("=" * 60)
    logger.info("ANALYTICS QUERIES")
    logger.info("=" * 60)

    if not Path(DUCKDB_PATH).exists():
        raise FileNotFoundError(f"DuckDB not found at {DUCKDB_PATH}. Run modeling first.")

    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    queries = parse_queries(QUERIES_PATH)

    logger.info("Parsed %d queries from %s", len(queries), QUERIES_PATH)

    for i, (comment, sql) in enumerate(queries, 1):
        logger.info("-" * 50)
        logger.info("Q%d: %s", i, comment.split("\n")[0])
        logger.info("-" * 50)
        try:
            result = conn.execute(sql).fetchdf()
            print(f"\n{'='*60}")
            print(f"Q{i}: {comment.split(chr(10))[0]}")
            print(f"{'='*60}")
            print(result.to_string(index=False))
            print()
        except Exception as e:
            logger.error("Query Q%d failed: %s", i, e)

    conn.close()
    logger.info("ANALYTICS COMPLETE — %d queries executed", len(queries))


if __name__ == "__main__":
    run_queries()
