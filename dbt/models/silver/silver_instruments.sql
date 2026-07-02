SELECT
    raw_data:instrumentId::INT as instrument_id,
    raw_data:internalAssetClassName::VARCHAR(20) as asset_class,
    raw_data:internalSymbolFull::VARCHAR(20) as symbol,
    raw_data:internalInstrumentDisplayName::VARCHAR(80) as display_name,
    raw_data:internalExchangeName::VARCHAR(30) as exchange_name, 
    raw_data:internalStockIndustryName::VARCHAR(50) as industry_name,
    raw_data:"sectorName-TTM"::VARCHAR(50) as sector_name,
    raw_data:umbrellaSector::VARCHAR(50) as umbrella_sector,
    raw_data:fetched_at::TIMESTAMP as loaded_at
FROM {{ source('bronze', 'instruments') }}
