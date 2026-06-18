with latest_load as
(
    SELECT 
        *
    FROM {{ ref('silver_open_positions') }}
        WHERE LOADED_AT = (SELECT MAX(LOADED_AT) FROM {{ ref('silver_open_positions') }})
)
SELECT
    mirror_name,
    order_id,
    amount as opening_amount,
    open_datetime,
    is_buy,
    instrument_id,
    leverage,
    open_rate,
    total_fees,
FROM latest_load
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY LOADED_AT DESC) = 1