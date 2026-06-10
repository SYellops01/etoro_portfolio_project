--asserts that all open positions have a positive open_rate
SELECT
    order_id, 
    instrument_id,
    open_rate
FROM {{ ref('silver_open_positions')}}
WHERE open_rate <= 0