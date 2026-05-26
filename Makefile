.PHONY: install ingest transform model analytics test lint run clean help
.PHONY: storage-up storage-down upload-raw upload-processed
.PHONY: dbt-run dbt-test dbt-docs format

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dependencies
	pip install -r requirements.txt

ingest:  ## Download and ingest raw data from Kaggle
	python -m ingestion.ingest

transform:  ## Clean and transform raw data to Parquet
	python -m transformation.transform

model:  ## Build star schema in DuckDB
	python -m modeling.model

analytics:  ## Run analytical SQL queries
	python -m analytics.run_queries

test:  ## Run pytest test suite
	pytest tests/ -v --tb=short

lint:  ## Run ruff linter
	ruff check ingestion/ transformation/ modeling/ pipeline/ analytics/ storage/ tests/

format:  ## Auto-format code with ruff
	ruff format ingestion/ transformation/ modeling/ pipeline/ analytics/ storage/ tests/

run:  ## Execute full pipeline end-to-end
	python -m pipeline.pipeline

clean:  ## Remove processed data and DuckDB files
	rm -rf data/processed/*
	rm -f data/olist.duckdb
	rm -f data/olist_dbt.duckdb

# --- Cloud Storage (MinIO / S3) ---

storage-up:  ## Start MinIO container (local S3)
	docker compose up -d

storage-down:  ## Stop MinIO container
	docker compose down

upload-raw:  ## Upload raw CSVs to S3 bucket
	python -c "from storage.cloud_storage import upload_raw; upload_raw()"

upload-processed:  ## Upload processed Parquets to S3 bucket
	python -c "from storage.cloud_storage import upload_processed; upload_processed()"

# --- dbt ---

dbt-run:  ## Run dbt models (staging + marts)
	cd dbt/olist_dbt && dbt run --profiles-dir .

dbt-test:  ## Run dbt tests
	cd dbt/olist_dbt && dbt test --profiles-dir .

dbt-docs:  ## Generate and serve dbt documentation
	cd dbt/olist_dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .
