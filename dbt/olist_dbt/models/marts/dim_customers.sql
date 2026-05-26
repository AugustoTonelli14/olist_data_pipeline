-- Dimension: customers
-- One row per customer with demographics

select
    customer_id as customer_key,
    customer_unique_id,
    customer_city,
    customer_state
from {{ ref('stg_customers') }}
