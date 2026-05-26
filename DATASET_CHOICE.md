# Dataset Choice: Brazilian E-Commerce (Olist)

## Selected Dataset

**Brazilian E-Commerce Public Dataset by Olist**
Source: [Kaggle - Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

## Why This Dataset

### Volume & Scale
- **100,000+ orders** spanning 2016–2018
- **9 relational CSV files** totaling ~120MB uncompressed
- Enough volume to demonstrate meaningful pipeline work without requiring cloud infrastructure

### Relational Complexity
The dataset consists of 9 interconnected tables:

| Table | Rows (approx) | Description |
|---|---|---|
| olist_orders | 99,441 | Core order data with timestamps |
| olist_order_items | 112,650 | Line items per order |
| olist_order_payments | 103,886 | Payment methods and values |
| olist_order_reviews | 99,224 | Customer reviews and scores |
| olist_products | 32,951 | Product catalog |
| olist_sellers | 3,095 | Seller information |
| olist_customers | 99,441 | Customer demographics |
| olist_geolocation | 1,000,163 | Zip code lat/long (1M+ rows) |
| product_category_name_translation | 71 | Portuguese to English mapping |

This structure requires multi-table joins, foreign key management, and careful schema design — exactly what DE roles demand.

### Domain Relevance
E-commerce is one of the most common domains in Data Engineering job postings. This dataset covers:
- Order lifecycle management
- Payment processing
- Customer segmentation
- Seller performance analytics
- Geographic distribution
- Review sentiment patterns

### Real-World Messiness
- Missing values in product dimensions, review comments, and delivery dates
- Type inconsistencies in date fields (string vs. datetime)
- Duplicate geolocation entries per zip code
- Portuguese text requiring translation mapping
- Null delivery timestamps for undelivered orders

### Format Variety Demonstration
- Raw ingestion: CSV files (original format)
- Transformation output: Parquet with partitioning
- Modeling layer: Star schema in DuckDB

### Analytics Richness
Supports business-critical KPIs:
- Revenue by category, seller, region, time period
- Delivery performance and SLA compliance
- Customer lifetime value and retention
- Payment method distribution
- Review score correlation with delivery time

## Alternatives Considered

| Dataset | Pros | Cons | Verdict |
|---|---|---|---|
| NYC Taxi Trips | Massive volume (100M+ rows) | Single table, limited joins | Too simple relationally |
| Instacart Market Basket | Good relational structure | Anonymized, limited business context | Less analytics depth |
| Airline On-Time Performance | Large and messy | Primarily single-table analysis | Weak modeling potential |

## Conclusion

The Olist dataset strikes the optimal balance: enough volume to be meaningful, enough relational complexity to demonstrate modeling skills, enough messiness to show data quality handling, and enough business context to write compelling analytics queries. It is the strongest choice for a recruiter-ready Data Engineering portfolio project.
