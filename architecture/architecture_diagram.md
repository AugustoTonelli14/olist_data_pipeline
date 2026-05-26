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
        PART[(fact_orders/<br/>year=*/month=*)]
    end

    subgraph Modeling["Modeling Layer"]
        direction TB
        PY[Python Star Schema]
        DBT[dbt Models<br/>staging → marts]
        DB[(DuckDB)]
    end

    subgraph Analytics["Analytics Layer"]
        SQL[12 Business Queries]
        KPI[KPI Aggregations]
        WIN[Window Functions & CTEs]
    end

    subgraph Cloud["Cloud Storage Layer"]
        S3R[(s3://olist-raw/)]
        S3P[(s3://olist-processed/)]
        MINIO[MinIO / AWS S3]
    end

    subgraph Quality["Quality & CI"]
        TEST[pytest Suite]
        DBTT[dbt Tests]
        LINT[ruff Linting]
        CI[GitHub Actions]
    end

    K --> DL --> META --> RAW
    RAW --> CLEAN --> ENRICH --> PQ
    ENRICH --> PART
    PQ --> PY --> DB
    PQ --> DBT --> DB
    DB --> SQL --> KPI & WIN
    RAW --> S3R --> MINIO
    PQ --> S3P --> MINIO
    PQ --> TEST
    DB --> TEST
    DBT --> DBTT
    TEST --> CI
    DBTT --> CI
    LINT --> CI
```

## Cloud Storage Architecture

```mermaid
flowchart TB
    subgraph Local["Local Development"]
        RAW[data/raw/ CSVs]
        PROC[data/processed/ Parquet]
    end

    subgraph Toggle["CLOUD_PROVIDER config"]
        LOCAL["local → MinIO Docker"]
        AWS["aws → Real AWS S3"]
    end

    subgraph MinIO["MinIO Container"]
        MR[(olist-raw bucket)]
        MP[(olist-processed bucket)]
        MC[Console :9001]
    end

    subgraph S3["AWS S3"]
        SR[(s3://olist-raw/)]
        SP[(s3://olist-processed/)]
    end

    RAW --> Toggle
    PROC --> Toggle
    LOCAL --> MR & MP
    AWS --> SR & SP
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

## dbt Model Lineage

```mermaid
flowchart LR
    subgraph Staging["models/staging/"]
        S1[stg_orders]
        S2[stg_customers]
        S3[stg_products]
        S4[stg_sellers]
        S5[stg_order_items]
        S6[stg_payments]
        S7[stg_reviews]
    end

    subgraph Marts["models/marts/"]
        D1[dim_customers]
        D2[dim_products]
        D3[dim_sellers]
        D4[dim_date]
        D5[dim_location]
        F1[fact_orders]
    end

    S1 --> D4
    S1 --> F1
    S2 --> D1
    S2 --> F1
    S3 --> D2
    S4 --> D3
    S5 --> F1
    S6 --> F1
    S7 --> F1
```

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Ingestion | Python + Kaggle API | Programmatic data download |
| Transformation | Pandas + PyArrow | Cleaning, type casting, enrichment |
| Partitioning | PyArrow write_to_dataset | Year/month partitioned Parquet |
| Storage (Raw) | CSV | Original format preservation |
| Storage (Processed) | Parquet | Columnar, compressed, partitioned |
| Cloud Storage | MinIO / AWS S3 + boto3 | S3-compatible object storage |
| Modeling (Python) | DuckDB | Local analytical database |
| Modeling (dbt) | dbt-core + dbt-duckdb | SQL-based staging → marts |
| Analytics | SQL | Business intelligence queries |
| Testing | pytest + dbt test | Pipeline and schema validation |
| CI/CD | GitHub Actions | Automated testing and linting |
| Linting | ruff | Code quality enforcement |
| Orchestration | Python + Makefile | Pipeline execution |
| Infrastructure | Docker Compose | Local MinIO for cloud simulation |
