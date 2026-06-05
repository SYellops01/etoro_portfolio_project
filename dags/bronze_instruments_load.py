import os
import boto3
import snowflake.connector
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from snowflake_credentials import get_snowflake_account, get_snowflake_password, get_snowflake_username

# MinIO config
MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "password123"
LOCAL_DIR = "/tmp/minio_downloads"

# Snowflake config
SNOWFLAKE_USER = get_snowflake_username()
SNOWFLAKE_PASSWORD = get_snowflake_password()
SNOWFLAKE_ACCOUNT = get_snowflake_account()
SNOWFLAKE_WAREHOUSE = "LOAD_WH"
SNOWFLAKE_DB = "ETORO_PORTFOLIO"
SNOWFLAKE_SCHEMA = "BRONZE"

BUCKET = "bronze-instruments"
STAGE = "STG_INSTRUMENTS"

def download_from_minio():
    download_dir = os.path.join(LOCAL_DIR, BUCKET)
    os.makedirs(download_dir, exist_ok=True)

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY
    )

    objects = s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])
    local_files = []
    for obj in objects:
        key = obj["Key"]
        local_file = os.path.join(download_dir, key.replace("/", "_"))
        s3.download_file(BUCKET, key, local_file)
        print(f"Downloaded {key} -> {local_file}")
        local_files.append(local_file)

    print(f"Downloaded {len(local_files)} files from {BUCKET}")
    return local_files

def put_to_snowflake_stage(**kwargs):
    local_files = kwargs["ti"].xcom_pull(task_ids="download_instruments")

    if not local_files:
        print("No files to stage for INSTRUMENTS")
        return

    conn = snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DB,
        schema=SNOWFLAKE_SCHEMA
    )
    cur = conn.cursor()

    for f in local_files:
        cur.execute(f"PUT file://{f} @{SNOWFLAKE_DB}.{SNOWFLAKE_SCHEMA}.{STAGE} AUTO_COMPRESS=TRUE OVERWRITE=TRUE")
        print(f"PUT {f} -> @{STAGE}")

    cur.close()
    conn.close()

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    "bronze_instruments_load",
    default_args=default_args,
    schedule_interval="0 */1 * * *",
    catchup=False,
    tags=["bronze", "instruments"]
) as dag:

    download = PythonOperator(
        task_id="download_instruments",
        python_callable=download_from_minio
    )

    put = PythonOperator(
        task_id="put_instruments",
        python_callable=put_to_snowflake_stage,
        provide_context=True
    )

    download >> put
