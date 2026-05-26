# Pipeline Architecture

## High-Level Data Flow

```mermaid
flowchart LR
    subgraph Sources["Data Sources"]
        K[Kaggle API]
        CSV[9 CSV Files]
    end

    subgraph Ingestion["Ingestion Layer"]
        DL[Download & Validate]
        META[Metadata Logging]
        RAW[(data/raw/)]
    end

    subgraph Transformation["Transformation Layer"]
        CLEAN[Null Handling<br/>Type Casting<br/>Deduplication]
        ENRICH[Date Normalization<br/>String Cleaning<br/>Translation Merge]
        PQ[(data/processed/<br/>Parquet)]
    end

    subgraph Modeling["Modeling Layer"]
        STAR[Star Schema Design]
        FACT[Fact Tables]
        DIM[Dimension Tables]
        DB[(DuckDB)]
    end

    subgraph Analytics["Analytics Layer"]
        SQL[10+ Business Queries]
        KPI[KPI Aggregations]
        WIN[Window Functions & CTEs]
    end

    subgraph Quality["Quality & CI"]
        TEST[pytest Suite]
        LINT[ruff Linting]
        CI[GitHub Actions]
    end

    K --> DL --> META --> RAW
    RAW --> CLEAN --> ENRICH --> PQ
    PQ --> STAR --> FACT & DIM --> DB
    DB --> SQL --> KPI & WIN
    PQ --> TEST
    DB --> TEST
    TEST --> CI
    LINT --> CI
```

## Star Schema Design

```mermaid
erDiagram
    FACT_ORDERS {
        varchar order_id PK
        varchar customer_key FK
        varchar seller_key FK
        varchar product_key FK
        varchar location_key FK
        int date_key FK
        varchar payment_type
        int payment_installments
        decimal payment_value
        decimal price
        decimal freight_value
        int review_score
        int delivery_days
        boolean delivered_on_time
    }

    DIM_CUSTOMERS {
        varchar customer_key PK
        varchar customer_unique_id
        varchar customer_city
        varchar customer_state
    }

    DIM_PRODUCTS {
        varchar product_key PK
        varchar category_name_english
        decimal weight_g
        decimal length_cm
        decimal height_cm
        decimal width_cm
        int photo_count
    }

    DIM_SELLERS {
        varchar seller_key PK
        varchar seller_city
        varchar seller_state
    }

    DIM_DATE {
        int date_key PK
        date full_date
        int year
        int quarter
        int month
        int day
        int day_of_week
        varchar month_name
        boolean is_weekend
    }

    DIM_LOCATION {
        varchar location_key PK
        varchar zip_code_prefix
        varchar city
        varchar state
        decimal latitude
        decimal longitude
    }

    FACT_ORDERS ||--o{ DIM_CUSTOMERS : customer_key
    FACT_ORDERS ||--o{ DIM_PRODUCTS : product_key
    FACT_ORDERS ||--o{ DIM_SELLERS : seller_key
    FACT_ORDERS ||--o{ DIM_DATE : date_key
    FACT_ORDERS ||--o{ DIM_LOCATION : location_key
```

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Ingestion | Python + Kaggle API | Programmatic data download |
| Transformation | Pandas | Cleaning, type casting, enrichment |
| Storage (Raw) | CSV | Original format preservation |
| Storage (Processed) | Parquet | Columnar, compressed, partitioned |
| Modeling | DuckDB | Local analytical database |
| Analytics | SQL | Business intelligence queries |
| Testing | pytest | Pipeline validation |
| CI/CD | GitHub Actions | Automated testing and linting |
| Linting | ruff | Code quality enforcement |
| Orchestration | Python + Makefile | Pipeline execution |
