SELECT
    order_id, 
    instrument_id,
    amount
FROM {{ ref('silver_open_positions')}}
WHERE amount <= 0