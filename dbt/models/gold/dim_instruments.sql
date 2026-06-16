SELECT
    instrument_id,
    asset_class,
    symbol,
    display_name,
    exchange_name,
    COALESCE(industry_name, asset_class) AS industry_name,
    COALESCE(sector_name, asset_class) AS sector_name,
    COALESCE(umbrella_sector, asset_class) AS umbrella_sector
FROM {{ref('silver_instruments')}}
QUALIFY ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY LOADED_AT DESC) = 1