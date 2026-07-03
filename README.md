# Project Overview

This project builds an end-to-end pipeline identifying all positions (including mirror positions) that an individual holds in their eToro portfolio. Dockerized infrastructure pulls live stock prices from several eToro APIs into minIO storage, with Airflow used to schedule loads from minIO into Snowflake. dbt Cloud is used for transformation and the final output is a Streamlit-in-Snowflake app showcasing the end user's portfolio, with the ability to filter by industry, sector or position type (mirror/single position). 

In eToro, it is not currently possible to view exposure across direct positions and those held within 'mirrors' and this project therefore addresses this shortcoming, allowing the end-user to view exposure across their whole portfolio. 

***Note - Positions below have been altered and are not real, nor are they financial advice.**
<img width="1747" height="799" alt="image" src="https://github.com/user-attachments/assets/7d2ef458-db04-48e3-a0cd-68aa91890724" />
<img width="1728" height="571" alt="image" src="https://github.com/user-attachments/assets/d5b91f7a-a213-4e0b-b754-8cd96bb4e833" />
<img width="1710" height="521" alt="image" src="https://github.com/user-attachments/assets/3b7cb8ab-b06a-4dcf-920b-ebddc6b9009f" />


# Key Features
- Fetching live stock market data from eToro API.
- Real-time streaming pipeline into minIO with Kafka.
- Orchestrated ETL workflow from minIO to Snowflake using Airflow.
- Transformations in Snowflake using dbt Cloud.
- Scalable cloud warehouse powered by Snowflake.

# Setup
## Prerequisites
- VS Code Extensions - Python, Docker
- Docker Desktop (https://docs.docker.com/get-started/get-docker/)
- eToro Trading account and API Key (https://www.etoro.com/settings/trade)
- dbt Cloud Account (https://www.getdbt.com/)
- Snowflake Account (https://signup.snowflake.com/)

## Initialisation.cmd
- The initialisation.cmd file in this repository details steps required to run in VS Code CLI to ensure correct setup.
- Credentials for eToro API should be added in src > producer > credentials.py
- Credentials for Snowflake should be added in dags > snowflake_credentials.py

## API Documentation
- Collect all instruments - https://api-portal.etoro.com/api-reference/market-data/search-for-instruments
- Get Account Portfolio - https://api-portal.etoro.com/api-reference/trading-real/get-portfolio-breakdown#get-portfolio-breakdown
- Get Live Market Rates - https://api-portal.etoro.com/api-reference/market-data/get-instrument-market-rates#get-instrument-market-rates
- Get Backfilled Price History - https://api-portal.etoro.com/api-reference/market-data/get-instrument-candle-history#get-instrument-candle-history

# Solution Architecture
## Overall Architecture
*Diagram*

## Naming Conventions
- Stages are prefixed with 'stg_'
- Within the ETORO_PORTFOLIO database, schemas follow the following naming: ETORO_PORTFOLIO_<LAYER>, where <LAYER> is bronze, silver, gold or marts.
- Tables/views are prefixed in silver layer with 'silver_'. In gold layer, fact tables are prefixed with 'fct_' and dimension tables are prefixed with 'dim_'

## dbt Transformation and Tests
dbt Cloud is used to transform data between our bronze and marts layer and automate testing, ensuring data accuracy, validating primary/foreign key constraints and ensuring uniqueness of primary keys. 
<img width="1264" height="581" alt="image" src="https://github.com/user-attachments/assets/bcfb6a1a-0476-4162-a939-2f21871e87a7" />
<img width="1012" height="627" alt="image" src="https://github.com/user-attachments/assets/f805ae04-bd62-4ce4-be1e-7cc2b14abb51" />
A number of generic tests are included:
- Test for uniqueness of instrument id's in Gold Layer
- Relationship testing between instrument id's across dimensions and fact tables.
- Not null tests implemented across required columns.
- dbt Expectations used to ensure values fall in expected range (positive/negative)

Several singular tests are also included:
- Assert that amount of any open positions is positive.
- Assert that opening price is positive.
- Assert that live stock price is positive.

## Snowflake Semantic Layer

