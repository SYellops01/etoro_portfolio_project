SELECT
    raw_data:instrumentId::INT as instrument_id,
    raw_data:assetClass::VARCHAR(20) as asset_class,
    raw_data:symbol::VARCHAR(20) as symbol,
    raw_data:displayName::VARCHAR(50) as display_name,
    raw_data:exchangeName::VARCHAR(30) as exchange_name, 
    raw_data:industryName::VARCHAR(50) as industry_name,
    raw_data:sectorName::VARCHAR(50) as sector_name,
    raw_data:umbrellaSector::VARCHAR(50) as umbrella_sector,
    loaded_at
FROM {{ source('bronze', 'instruments') }}