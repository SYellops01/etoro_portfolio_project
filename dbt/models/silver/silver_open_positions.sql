with all_positions AS
(
    SELECT
        raw_data:mirrors AS mirrors_array,
        raw_data:positions AS direct_positions_array,
        loaded_at
    FROM {{ source('bronze', 'portfolio') }}
)
-- Mirror positions: flatten mirrors, then flatten positions within each mirror
, mirror_positions AS (
    SELECT
        m.value:parentUsername::VARCHAR(30) AS mirror_name,
        p.value:orderID::INT AS order_id,
        p.value:amount::NUMBER(10,3) AS amount,
        p.value:isBuy::BOOLEAN AS is_buy,
        p.value:instrumentID::INT AS instrument_id,
        p.value:leverage::NUMBER(10,3) AS leverage,
        TRY_TO_TIMESTAMP(p.value:openDateTime::VARCHAR) AS open_datetime,
        p.value:openRate::NUMBER(10,3) AS open_rate,
        p.value:totalFees::NUMBER(10,3) AS total_fees,
        p.value:units::NUMBER(10,3) AS units,
        a.loaded_at
    FROM all_positions a,
    LATERAL FLATTEN(input => a.mirrors_array) m,
    LATERAL FLATTEN(input => m.value:positions) p
)
, direct_positions AS (
    SELECT
        'Direct Position' AS mirror_name,
        p.value:orderID::INT AS order_id,
        p.value:amount::NUMBER(10,3) AS amount,
        p.value:isBuy::BOOLEAN AS is_buy,
        p.value:instrumentID::INT AS instrument_id,
        p.value:leverage::NUMBER(10,3) AS leverage,
        TRY_TO_TIMESTAMP(p.value:openDateTime::VARCHAR) AS open_datetime,
        p.value:openRate::NUMBER(10,3) AS open_rate,
        p.value:totalFees::NUMBER(10,3) AS total_fees,
        p.value:units::NUMBER(10,3) AS units,
        a.loaded_at
    FROM all_positions a,
    LATERAL FLATTEN(input => a.direct_positions_array) p
)
SELECT * FROM mirror_positions
UNION ALL
SELECT * FROM direct_positions