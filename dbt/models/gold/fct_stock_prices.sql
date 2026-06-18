--fct_stock_prices
with price_history AS
(
    SELECT
        instrument_id,
        price_timestamp_5_min,
        live_price
    FROM {{ ref('silver_price_series') }}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY instrument_id, price_timestamp_5_min ORDER BY price_timestamp DESC) = 1
)
,price_history_scaffold AS
(
    SELECT
        sc.instrument_id,
        sc.price_timestamp_5_min as price_timestamp,
        hist.live_price
    FROM {{ ref('silver_price_scaffold') }} sc
    LEFT JOIN price_history hist
        ON sc.instrument_id = hist.instrument_id
        AND sc.price_timestamp_5_min = hist.price_timestamp_5_min
)
,
scaffold_filled AS
(
    SELECT
        instrument_id, 
        price_timestamp,
        live_price,
        LAST_VALUE(live_price ignore nulls) OVER (PARTITION BY instrument_id ORDER BY price_timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS live_price_filled
    FROM price_history_scaffold
)
select * from scaffold_filled