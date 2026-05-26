-- ============================================================
-- Olist E-Commerce Analytics Queries
-- Run against the DuckDB star schema (fact_orders + dimensions)
-- ============================================================


-- Q1: Monthly revenue trend
-- Business question: How has revenue evolved month-over-month?
SELECT
    d.year,
    d.month,
    d.month_name,
    ROUND(SUM(f.payment_value), 2) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(SUM(f.payment_value) / COUNT(DISTINCT f.order_id), 2) AS avg_order_value
FROM fact_orders f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- Q2: Top 10 product categories by revenue
-- Business question: Which product categories drive the most revenue?
SELECT
    p.category_name,
    ROUND(SUM(f.payment_value), 2) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(AVG(f.review_score), 2) AS avg_review_score
FROM fact_orders f
JOIN dim_products p ON f.product_key = p.product_key
GROUP BY p.category_name
ORDER BY total_revenue DESC
LIMIT 10;


-- Q3: Revenue by state with ranking
-- Business question: Which states generate the most revenue, and what's each state's share?
WITH state_revenue AS (
    SELECT
        c.customer_state AS state,
        ROUND(SUM(f.payment_value), 2) AS total_revenue,
        COUNT(DISTINCT f.order_id) AS orders
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    GROUP BY c.customer_state
)
SELECT
    state,
    total_revenue,
    orders,
    RANK() OVER (ORDER BY total_revenue DESC) AS revenue_rank,
    ROUND(100.0 * total_revenue / SUM(total_revenue) OVER (), 2) AS pct_of_total
FROM state_revenue
ORDER BY revenue_rank;


-- Q4: Seller performance — top 15 sellers by volume with delivery metrics
-- Business question: Who are our highest-volume sellers, and how reliable are they?
SELECT
    s.seller_key,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.payment_value), 2) AS total_revenue,
    ROUND(AVG(f.delivery_days), 1) AS avg_delivery_days,
    ROUND(100.0 * SUM(CASE WHEN f.delivered_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct
FROM fact_orders f
JOIN dim_sellers s ON f.seller_key = s.seller_key
GROUP BY s.seller_key, s.seller_city, s.seller_state
HAVING COUNT(DISTINCT f.order_id) >= 10
ORDER BY total_orders DESC
LIMIT 15;


-- Q5: Payment method analysis
-- Business question: How are customers paying, and does payment method affect order value?
SELECT
    f.payment_type,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(SUM(f.payment_value), 2) AS total_revenue,
    ROUND(AVG(f.payment_value), 2) AS avg_payment_value,
    ROUND(AVG(f.payment_installments), 1) AS avg_installments,
    ROUND(100.0 * COUNT(DISTINCT f.order_id) / SUM(COUNT(DISTINCT f.order_id)) OVER (), 1) AS pct_of_orders
FROM fact_orders f
GROUP BY f.payment_type
ORDER BY order_count DESC;


-- Q6: Delivery SLA compliance by month
-- Business question: Are we getting better or worse at on-time delivery?
SELECT
    d.year,
    d.month,
    d.month_name,
    COUNT(*) AS total_deliveries,
    SUM(CASE WHEN f.delivered_on_time THEN 1 ELSE 0 END) AS on_time,
    ROUND(100.0 * SUM(CASE WHEN f.delivered_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct,
    ROUND(AVG(f.delivery_days), 1) AS avg_delivery_days
FROM fact_orders f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.delivery_days IS NOT NULL
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- Q7: Customer review score distribution with revenue impact
-- Business question: How do review scores correlate with order value and freight?
SELECT
    f.review_score,
    COUNT(*) AS order_count,
    ROUND(AVG(f.payment_value), 2) AS avg_order_value,
    ROUND(AVG(f.freight_value), 2) AS avg_freight,
    ROUND(AVG(f.delivery_days), 1) AS avg_delivery_days,
    ROUND(100.0 * SUM(CASE WHEN f.delivered_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct
FROM fact_orders f
WHERE f.review_score > 0
GROUP BY f.review_score
ORDER BY f.review_score;


-- Q8: Freight cost analysis — ratio of freight to product price by category
-- Business question: Which categories have disproportionately high shipping costs?
SELECT
    p.category_name,
    COUNT(*) AS items_sold,
    ROUND(AVG(f.price), 2) AS avg_price,
    ROUND(AVG(f.freight_value), 2) AS avg_freight,
    ROUND(100.0 * AVG(f.freight_value) / NULLIF(AVG(f.price), 0), 1) AS freight_to_price_pct
FROM fact_orders f
JOIN dim_products p ON f.product_key = p.product_key
GROUP BY p.category_name
HAVING COUNT(*) >= 50
ORDER BY freight_to_price_pct DESC
LIMIT 15;


-- Q9: Weekend vs weekday ordering patterns
-- Business question: Do ordering patterns differ between weekdays and weekends?
SELECT
    CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.payment_value), 2) AS total_revenue,
    ROUND(AVG(f.payment_value), 2) AS avg_order_value,
    ROUND(AVG(f.review_score), 2) AS avg_review
FROM fact_orders f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.review_score > 0
GROUP BY day_type;


-- Q10: Month-over-month revenue growth rate
-- Business question: What is the revenue growth trajectory?
WITH monthly AS (
    SELECT
        d.year,
        d.month,
        ROUND(SUM(f.payment_value), 2) AS revenue
    FROM fact_orders f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year, d.month
)
SELECT
    year,
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY year, month) AS prev_month_revenue,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year, month))
          / NULLIF(LAG(revenue) OVER (ORDER BY year, month), 0), 1) AS mom_growth_pct
FROM monthly
ORDER BY year, month;


-- Q11: Customer concentration — Pareto analysis (top 20% of customers)
-- Business question: What percentage of revenue comes from the top 20% of customers?
WITH customer_revenue AS (
    SELECT
        c.customer_unique_id,
        ROUND(SUM(f.payment_value), 2) AS total_spent,
        ROW_NUMBER() OVER (ORDER BY SUM(f.payment_value) DESC) AS rn,
        COUNT(*) OVER () AS total_customers
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    GROUP BY c.customer_unique_id
)
SELECT
    CASE
        WHEN rn <= total_customers * 0.20 THEN 'Top 20%'
        ELSE 'Bottom 80%'
    END AS customer_segment,
    COUNT(*) AS customer_count,
    ROUND(SUM(total_spent), 2) AS segment_revenue,
    ROUND(100.0 * SUM(total_spent) / (SELECT SUM(total_spent) FROM customer_revenue), 1) AS pct_of_revenue
FROM customer_revenue
GROUP BY customer_segment;


-- Q12: Product weight vs delivery time correlation buckets
-- Business question: Does product weight affect delivery time?
SELECT
    CASE
        WHEN p.weight_g IS NULL THEN 'Unknown'
        WHEN p.weight_g < 500 THEN '< 500g'
        WHEN p.weight_g < 2000 THEN '500g - 2kg'
        WHEN p.weight_g < 5000 THEN '2kg - 5kg'
        ELSE '5kg+'
    END AS weight_bucket,
    COUNT(*) AS order_count,
    ROUND(AVG(f.delivery_days), 1) AS avg_delivery_days,
    ROUND(AVG(f.freight_value), 2) AS avg_freight,
    ROUND(100.0 * SUM(CASE WHEN f.delivered_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct
FROM fact_orders f
JOIN dim_products p ON f.product_key = p.product_key
WHERE f.delivery_days IS NOT NULL
GROUP BY weight_bucket
ORDER BY avg_delivery_days;
