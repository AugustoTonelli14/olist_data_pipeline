-- Fact: orders
-- Grain: one row per order-item with payment, delivery, and review metrics

with order_payments as (
    select
        order_id,
        payment_type,
        payment_installments,
        sum(payment_value) as payment_value
    from {{ ref('stg_payments') }}
    group by order_id, payment_type, payment_installments
),

order_reviews as (
    select
        order_id,
        review_score,
        row_number() over (
            partition by order_id
            order by review_creation_date desc
        ) as rn
    from {{ ref('stg_reviews') }}
)

select
    oi.order_id,
    o.customer_id as customer_key,
    oi.seller_id as seller_key,
    oi.product_id as product_key,
    c.customer_zip_code_prefix as location_key,
    cast(strftime(o.order_purchase_timestamp, '%Y%m%d') as integer) as date_key,
    o.order_status,
    coalesce(p.payment_type, 'unknown') as payment_type,
    coalesce(p.payment_installments, 1) as payment_installments,
    coalesce(p.payment_value, 0.0) as payment_value,
    oi.price,
    oi.freight_value,
    coalesce(r.review_score, 0) as review_score,
    case
        when o.order_delivered_customer_date is not null
             and o.order_purchase_timestamp is not null
        then date_diff('day',
            o.order_purchase_timestamp::date,
            o.order_delivered_customer_date::date)
        else null
    end as delivery_days,
    case
        when o.order_delivered_customer_date is not null
             and o.order_estimated_delivery_date is not null
             and o.order_delivered_customer_date <= o.order_estimated_delivery_date
        then true
        else false
    end as delivered_on_time
from {{ ref('stg_order_items') }} oi
join {{ ref('stg_orders') }} o on oi.order_id = o.order_id
join {{ ref('stg_customers') }} c on o.customer_id = c.customer_id
left join order_payments p on o.order_id = p.order_id
left join order_reviews r on o.order_id = r.order_id and r.rn = 1
