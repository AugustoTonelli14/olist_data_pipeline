-- Dimension: date
-- One row per day covering the full order date range

with date_range as (
    select unnest(
        generate_series(
            (select min(order_purchase_timestamp)::date from {{ ref('stg_orders') }}),
            (select max(order_purchase_timestamp)::date from {{ ref('stg_orders') }}),
            interval '1 day'
        )
    ) as full_date
)

select
    cast(strftime(full_date, '%Y%m%d') as integer) as date_key,
    full_date::date as full_date,
    year(full_date) as year,
    quarter(full_date) as quarter,
    month(full_date) as month,
    day(full_date) as day,
    dayofweek(full_date) as day_of_week,
    strftime(full_date, '%B') as month_name,
    case when dayofweek(full_date) in (0, 6) then true else false end as is_weekend
from date_range
