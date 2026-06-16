with latest_load as
(
    SELECT 
        *
    FROM {{ref('silver_open_positions')}}
    WHERE LOADED_AT = (SELECT MAX(LOADED_AT) FROM {{ref('silver_open_positions')}})
)
, current_portfolio AS
(
    SELECT
        mirror_name,
        amount as opening_amount,
        is_buy,
        instrument_id,
        leverage,
        open_rate,
        total_fees,
    FROM latest_load
    QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY LOADED_AT DESC) = 1
)
,price_history AS
(
    SELECT
        instrument_id,
        price_timestamp,
        live_price
    FROM {{ref('silver_price_series')}}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY instrument_id, price_timestamp ORDER BY price_timestamp DESC) = 1
)
,current_state_series AS
(
    SELECT
        p.*,
        ph.price_timestamp,
        ph.live_price
    FROM current_portfolio p
    JOIN price_history ph on p.instrument_id=ph.instrument_id
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
FROM current_state_series
)
select * from current_pl