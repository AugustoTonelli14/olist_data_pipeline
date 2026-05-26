-- Dimension: products
-- One row per product with category and physical attributes

select
    product_id as product_key,
    product_category_name_english as category_name,
    product_weight_g as weight_g,
    product_length_cm as length_cm,
    product_height_cm as height_cm,
    product_width_cm as width_cm,
    product_photos_qty as photo_count
from {{ ref('stg_products') }}
