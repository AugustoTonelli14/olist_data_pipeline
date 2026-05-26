-- Staging model: customers

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
from read_parquet('../../data/processed/customers.parquet')
