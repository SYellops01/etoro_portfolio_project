SELECT
    mirror_name,
    display_name,
    amount
FROM {{ref('silver_available_credit')}}
QUALIFY ROW_NUMBER() OVER (PARTITION BY mirror_name ORDER BY LOADED_AT DESC) = 1