WITH full_price_series AS
(
    SELECT
        p.*,
        sc.price_timestamp,
        sc.live_price_filled as live_price
    FROM {{ ref('fct_live_portfolio') }} AS p
    INNER JOIN {{ ref('fct_stock_prices') }} AS sc
        ON p.instrument_id=sc.instrument_id
    WHERE sc.price_timestamp >= p.open_datetime
)
,current_pl AS
(
SELECT
    *,
    (opening_amount * live_price * leverage / open_rate) + total_fees AS current_amount,       
    CASE
        WHEN is_buy = TRUE THEN current_amount - opening_amount
        ELSE -(current_amount - opening_amount)
    END AS profit_loss,
    current_amount / SUM(current_amount) OVER (PARTITION BY price_timestamp) as gross_exposure
FROM full_price_series
)
SELECT * FROM current_pl