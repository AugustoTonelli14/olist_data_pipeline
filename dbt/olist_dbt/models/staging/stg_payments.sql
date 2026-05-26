-- Staging model: payments

select
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
from read_parquet('../../data/processed/payments.parquet')
