-- Dimension: sellers
-- One row per seller with location

select
    seller_id as seller_key,
    seller_city,
    seller_state
from {{ ref('stg_sellers') }}
