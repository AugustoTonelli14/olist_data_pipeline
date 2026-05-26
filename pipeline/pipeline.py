"""Pipeline orchestrator: runs ingestion, transformation, and modeling end-to-end."""

import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("pipeline")

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5


def run_step(name: str, func, *args, retries: int = MAX_RETRIES) -> None:
    """Execute a pipeline step with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            logger.info("Step [%s] — attempt %d/%d", name, attempt, retries)
            start = time.time()
            func(*args)
            elapsed = time.time() - start
            logger.info("Step [%s] completed in %.1fs", name, elapsed)
            return
        except Exception as e:
            logger.error("Step [%s] failed (attempt %d): %s", name, attempt, e)
            if attempt < retries:
                logger.info("Retrying in %ds...", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                logger.critical("Step [%s] failed after %d attempts", name, retries)
                raise


def run_pipeline() -> None:
    """Execute the full data pipeline."""
    logger.info("=" * 60)
    logger.info("OLIST DATA PIPELINE — FULL RUN")
    logger.info("=" * 60)
    pipeline_start = time.time()

    from ingestion.ingest import run_ingestion
    from modeling.model import run_modeling
    from transformation.transform import run_transformation

    run_step("ingestion", run_ingestion)
    run_step("transformation", run_transformation)
    run_step("modeling", run_modeling)

    total_time = time.time() - pipeline_start
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE — total time: %.1fs", total_time)
    logger.info("=" * 60)

    db_path = Path(os.getenv("DUCKDB_PATH", "data/olist.duckdb"))
    if db_path.exists():
        size_mb = db_path.stat().st_size / 1e6
        logger.info("Output database: %s (%.1f MB)", db_path, size_mb)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.critical("Pipeline failed: %s", e)
        sys.exit(1)
