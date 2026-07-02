--scaffold containing every combination of 5 minute increment price timestamp and instrument.
SELECT
    i.instrument_id,
    t.price_timestamp_5_min
FROM {{ref('silver_price_series')}} i
CROSS JOIN {{ref('silver_price_series')}} t
GROUP BY 1,2