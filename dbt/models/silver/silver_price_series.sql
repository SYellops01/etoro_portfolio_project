with stock_hist as
(
    SELECT
        c.value:instrumentID::INT as instrument_id,
        TRY_TO_TIMESTAMP(c.value:fromDate::VARCHAR) as price_timestamp,
        c.value:open::NUMBER(10,3) AS live_price,
        c.value:high::NUMBER(10,3) AS high,
        c.value:low::NUMBER(10,3) AS low,
        hist.loaded_at
    FROM {{ source('bronze', 'stock_history') }} hist,
    LATERAL FLATTEN(INPUT=> hist.raw_data:candles) c
)
, stock_price as
(
    SELECT
        raw_data:instrumentID::INT as instrument_id,
        TRY_TO_TIMESTAMP(raw_data:date::VARCHAR) as price_timestamp,
        raw_data:bid::NUMBER(10,3) as live_price,
        raw_data:bid::NUMBER(10,3) AS high,
        raw_data:bid::NUMBER(10,3) AS low,
        loaded_at
    FROM {{ source('bronze', 'stock_prices') }}
)
,full_price as
(
    SELECT * FROM stock_hist
    UNION ALL
    SELECT * FROM stock_price
)
--Convert price timestamp into 5 minute windows (rounded down)
SELECT
    instrument_id,
    price_timestamp,
    DATEADD(minute,
        FLOOR(EXTRACT(minute from price_timestamp)/5)*5,
        DATE_TRUNC('hour',price_timestamp)
        ) AS price_timestamp_5_min,
    live_price,
    high,
    low,
    loaded_at
FROM full_price