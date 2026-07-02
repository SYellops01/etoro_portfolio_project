import json
import math
import sys
import os
import uuid
import requests
import snowflake.connector
import airflow
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from snowflake_credentials import (
    get_snowflake_account,
    get_snowflake_password,
    get_snowflake_username,
)
from src.producer.credentials import get_api_key, get_user_key

# ── Config ────────────────────────────────────────────────────────────────────

url = "https://public-api.etoro.com/api/v1/market-data/search"
page_size   = 2000
TMP_FILE    = "/tmp/instruments.json"

SNOWFLAKE_USER      = get_snowflake_username()
SNOWFLAKE_PASSWORD  = get_snowflake_password()
SNOWFLAKE_ACCOUNT   = get_snowflake_account()
SNOWFLAKE_WAREHOUSE = "LOAD_WH"
SNOWFLAKE_DB        = "ETORO_PORTFOLIO"
SNOWFLAKE_SCHEMA    = "BRONZE"
STAGE               = "STG_INSTRUMENTS"

# ── Task callable ─────────────────────────────────────────────────────────────

def fetch_and_stage_instruments(**kwargs):
    """
    Fetches all instruments from the eToro API, writes them as a single JSON
    array to a tmp file, PUTs it into the Snowflake internal stage, then cleans up.
    """
    fetched_at = int(time.time())
    headers = {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": get_api_key(),
        "x-user-key": get_user_key(),
    }
    all_instruments = []
    # ── Fetch all pages ───────────────────────────────────────────────────────
    try:
        response = requests.get(url, headers=headers, params={"page": 1, "pageSize": page_size})
        response.raise_for_status()
        data = response.json()
 
        total_pages = math.ceil(data["totalItems"] / page_size)
        all_instruments = data["items"]
 
        for page in range(2, total_pages + 1):
            response = requests.get(url, headers=headers, params={"page": page, "pageSize": page_size})
            response.raise_for_status()
            all_instruments.extend(response.json()["items"])
 
    except Exception as e:
        print(f"Error loading instruments: {e}")
    
    if all_instruments:
        for instrument in all_instruments:
            instrument["fetched_at"] = fetched_at
    else:
        print("No instruments to load")

    print(f">> Fetched {len(all_instruments)} instruments from eToro")

    # ── Write single JSON file ────────────────────────────────────────────────
    with open(TMP_FILE, "w") as f:
        json.dump(all_instruments, f)

    print(f">> Written to {TMP_FILE}")

    # ── PUT to Snowflake stage ────────────────────────────────────────────────
    conn = snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DB,
        schema=SNOWFLAKE_SCHEMA,
    )
    cur = conn.cursor()

    try:
        cur.execute(
            f"PUT file://{TMP_FILE} "
            f"@{SNOWFLAKE_DB}.{SNOWFLAKE_SCHEMA}.{STAGE} "
            f"AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
        )
        print(f">> PUT instruments.json -> @{STAGE}")
    finally:
        cur.close()
        conn.close()
        os.remove(TMP_FILE)
        print(f">> Cleaned up {TMP_FILE}")


# ── DAG definition ────────────────────────────────────────────────────────────

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "bronze_instruments_load",
    default_args=default_args,
    schedule="* 23 * * *",
    catchup=False,
    tags=["bronze", "instruments"],
) as dag:

    fetch_and_stage = PythonOperator(
        task_id="fetch_and_stage_instruments",
        python_callable=fetch_and_stage_instruments,
    )
