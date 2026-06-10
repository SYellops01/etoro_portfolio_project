-- Fails if any live price snapshot contains a stock price <= 0
SELECT
    instrument_id,
    live_price, 
    loaded_at
FROM {{ ref('silver_price_series')}}
WHERE live_price <= 0