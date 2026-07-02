-- ============================================================
-- STEP 1: CREATE ROLES FOR CONSUMING AND TRANSFORMING DATA
-- ============================================================

USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS DB_LOADER
    COMMENT = 'Role for consuming data into Bronze Layer';
CREATE ROLE IF NOT EXISTS DB_ENGINEER
    COMMENT = 'Engineering role for transforming data';

-- ============================================================
-- STEP 2: CREATE WAREHOUSE FOR COMPUTE
-- ============================================================
USE ROLE SYSADMIN;

CREATE WAREHOUSE IF NOT EXISTS LOAD_WH
    WAREHOUSE_SIZE ='X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;

-- ============================================================
-- STEP 3: CREATE DATABASE AND MEDALLION SCHEMAS
-- ============================================================
CREATE DATABASE IF NOT EXISTS ETORO_PORTFOLIO
    COMMENT = 'Database schema for my eToro Project';
CREATE SCHEMA IF NOT EXISTS ETORO_PORTFOLIO.BRONZE
    COMMENT = 'Bronze schema for raw data from minIO';
CREATE SCHEMA IF NOT EXISTS ETORO_PORTFOLIO.SILVER
    COMMENT = 'Silver layer for data transfromation';
CREATE SCHEMA IF NOT EXISTS ETORO_PORTFOLIO.GOLD
    COMMENT = 'Gold layer for data consumption';

-- ============================================================
-- STEP 4: GRANTS TO USERS
-- ============================================================
USE ROLE SECURITYADMIN;

GRANT ROLE DB_LOADER TO USER SYELLOPS;
GRANT ROLE DB_ENGINEER TO USER SYELLOPS;

-- ============================================================
-- STEP 5: PERMISSIONS TO ROLES
-- ============================================================

GRANT ROLE DB_LOADER TO USER SYELLOPS;
GRANT ROLE DB_ENGINEER TO USER SYELLOPS;
GRANT ROLE DB_LOADER TO ROLE SYSADMIN;
GRANT ROLE DB_ENGINEER TO ROLE SYSADMIN;

-- Usage on warehouse
GRANT USAGE ON WAREHOUSE LOAD_WH TO ROLE DB_LOADER;
GRANT USAGE ON WAREHOUSE LOAD_WH TO ROLE DB_ENGINEER;

-- Grant database level permissions
GRANT ALL ON DATABASE ETORO_PORTFOLIO TO ROLE DB_LOADER;
GRANT ALL ON DATABASE ETORO_PORTFOLIO TO ROLE DB_ENGINEER;

-- Grant schema level permissions
GRANT ALL ON SCHEMA ETORO_PORTFOLIO.BRONZE TO ROLE DB_LOADER;
GRANT ALL ON ALL SCHEMAS IN DATABASE ETORO_PORTFOLIO TO ROLE DB_ENGINEER;

-- Grant table level permissions
GRANT ALL ON FUTURE TABLES IN SCHEMA ETORO_PORTFOLIO.BRONZE TO ROLE DB_LOADER;
GRANT ALL ON FUTURE TABLES IN DATABASE ETORO_PORTFOLIO TO ROLE DB_ENGINEER;

-- Grant task execution to both roles 
GRANT EXECUTE TASK ON ACCOUNT TO ROLE DB_LOADER;
GRANT EXECUTE TASK ON ACCOUNT TO ROLE DB_ENGINEER;

-- Grant stage permissions to DB_LOADER
GRANT READ ON FUTURE STAGES IN SCHEMA ETORO_PORTFOLIO.BRONZE TO ROLE DB_LOADER;

-- ============================================================
-- STEP 6: BRONZE TABLES
-- ============================================================
USE ROLE SYSADMIN;
USE SCHEMA ETORO_PORTFOLIO.BRONZE;

CREATE TABLE IF NOT EXISTS INSTRUMENTS (
    raw_data VARIANT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Bronze table for collecting raw data about instruments and key details about these';

CREATE TABLE IF NOT EXISTS PORTFOLIO (
    raw_data VARIANT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Bronze table for collecting raw data about current user portfolio and instruments within this';

CREATE TABLE IF NOT EXISTS STOCK_PRICES (
    raw_data VARIANT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Bronze table for collecting raw data about current stock price of instruments within the user portfolio';

CREATE TABLE IF NOT EXISTS STOCK_HISTORY (
    raw_data VARIANT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Bronze table for collecting raw data about historic stock price of instruments within the user portfolio';

-- ============================================================
-- STEP 7: CREATE INTERNAL STAGES TO PUT DATA TO
-- ============================================================

CREATE STAGE IF NOT EXISTS ETORO_PORTFOLIO.BRONZE.STG_INSTRUMENTS
    FILE_FORMAT = (
        TYPE = JSON,
        STRIP_OUTER_ARRAY = TRUE
    );

CREATE STAGE IF NOT EXISTS ETORO_PORTFOLIO.BRONZE.STG_PORTFOLIO
    FILE_FORMAT = (
        TYPE = JSON,
        STRIP_OUTER_ARRAY = TRUE
    );

CREATE STAGE IF NOT EXISTS ETORO_PORTFOLIO.BRONZE.STG_STOCK_PRICES
    FILE_FORMAT = (
        TYPE = JSON,
        STRIP_OUTER_ARRAY = TRUE
    );

CREATE STAGE IF NOT EXISTS ETORO_PORTFOLIO.BRONZE.STG_STOCK_HISTORY
    FILE_FORMAT = (
        TYPE = JSON,
        STRIP_OUTER_ARRAY = TRUE
    );

-- ============================================================
-- STEP 8: SCHEDULE COPY INTO FROM INTERNAL STAGE USING TASKS
-- ============================================================
USE ROLE DB_LOADER;

-- Instrument task (midnight every day)
CREATE OR REPLACE TASK ETORO_PORTFOLIO.BRONZE.LOAD_INSTRUMENTS_TASK
    WAREHOUSE = LOAD_WH
    SCHEDULE = 'USING CRON * 00 * * * UTC'
AS
COPY INTO ETORO_PORTFOLIO.BRONZE.INSTRUMENTS
FROM
    (SELECT 
        $1 AS raw_data,
        CURRENT_TIMESTAMP() AS loaded_at
    FROM @ETORO_PORTFOLIO.BRONZE.STG_INSTRUMENTS
    )
;

-- Portfolio task (every 5 minutes)
CREATE OR REPLACE TASK ETORO_PORTFOLIO.BRONZE.LOAD_PORTFOLIO_TASK
    WAREHOUSE = LOAD_WH
    SCHEDULE = 'USING CRON */5 * * * * UTC'
AS
COPY INTO ETORO_PORTFOLIO.BRONZE.PORTFOLIO
FROM
    (SELECT 
        $1 AS raw_data,
        CURRENT_TIMESTAMP() AS loaded_at
    FROM @ETORO_PORTFOLIO.BRONZE.STG_PORTFOLIO
    )
;

-- Stock history task (every 5 minutes)
CREATE OR REPLACE TASK ETORO_PORTFOLIO.BRONZE.LOAD_HISTORY_TASK
    WAREHOUSE = LOAD_WH
    SCHEDULE = 'USING CRON */5 * * * * UTC'
AS
COPY INTO ETORO_PORTFOLIO.BRONZE.STOCK_HISTORY
FROM
    (SELECT
        $1 AS raw_data,
        CURRENT_TIMESTAMP() AS loaded_at
    FROM @ETORO_PORTFOLIO.BRONZE.STG_STOCK_HISTORY
    )
;

-- Stock prices task (every 5 minutes)
CREATE OR REPLACE TASK ETORO_PORTFOLIO.BRONZE.LOAD_PRICES_TASK
    WAREHOUSE = LOAD_WH
    SCHEDULE = 'USING CRON */5 * * * * UTC'
AS
COPY INTO ETORO_PORTFOLIO.BRONZE.STOCK_PRICES
FROM
    (SELECT
        $1 AS raw_data,
        CURRENT_TIMESTAMP() AS loaded_at
    FROM @ETORO_PORTFOLIO.BRONZE.STG_STOCK_PRICES
    )
;

-- Resume tasks
ALTER TASK ETORO_PORTFOLIO.BRONZE.LOAD_INSTRUMENTS_TASK RESUME;
ALTER TASK ETORO_PORTFOLIO.BRONZE.LOAD_PORTFOLIO_TASK RESUME;
ALTER TASK ETORO_PORTFOLIO.BRONZE.LOAD_HISTORY_TASK RESUME;
ALTER TASK ETORO_PORTFOLIO.BRONZE.LOAD_PRICES_TASK RESUME;
