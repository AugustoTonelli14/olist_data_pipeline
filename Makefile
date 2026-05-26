.PHONY: install ingest transform model analytics test lint run clean help

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

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
	ruff check ingestion/ transformation/ modeling/ pipeline/ tests/

format:  ## Auto-format code with ruff
	ruff format ingestion/ transformation/ modeling/ pipeline/ tests/

run:  ## Execute full pipeline end-to-end
	python -m pipeline.pipeline

clean:  ## Remove processed data and DuckDB files
	rm -rf data/processed/*
	rm -f data/olist.duckdb
