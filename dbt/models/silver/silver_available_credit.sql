with all_positions as
(   SELECT
        raw_data:credit::NUMBER(10,3) AS credit,
        'Available Cash' AS display_name,
        raw_data:mirrors AS mirrors_array,
        loaded_at
    FROM {{ source('bronze', 'portfolio') }}
)
, mirror_credit AS 
(
    SELECT
        m.value:parentUsername::VARCHAR(30) AS mirror_name,
        'Available Cash' AS display_name,
        m.value:availableAmount::NUMBER(10,3) AS amount,
        loaded_at
    FROM all_positions a,
    LATERAL FLATTEN(input => a.mirrors_array) m
)
, direct_credit AS 
(
    SELECT
        'Direct Position' AS mirror_name,
        'Available Cash' AS display_name,
        credit AS amount,
        loaded_at
    FROM all_positions
)
SELECT * FROM mirror_credit
UNION ALL
SELECT * FROM direct_credit