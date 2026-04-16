import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import snowflake.connector

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ingestion.common.snowflake_auth import load_private_key

load_dotenv()

OURA_PAT = os.getenv("OURA_PAT")
OURA_START_DATE = os.getenv("OURA_START_DATE", "2024-01-01")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PRIVATE_KEY_PATH = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")

start_date = OURA_START_DATE
end_date = datetime.today().strftime("%Y-%m-%d")

def fetch_oura_sleep(start, end):
    """Fetch all sleep records from Oura API v2, handling pagination via next_token."""
    url = "https://api.ouraring.com/v2/usercollection/sleep"
    headers = {"Authorization": f"Bearer {OURA_PAT}"}
    params = {"start_date": start, "end_date": end}

    all_records = []
    page = 1

    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        body = response.json()

        records = body.get("data", [])
        all_records.extend(records)
        print(f"  Page {page}: fetched {len(records)} records ({len(all_records)} total)")

        next_token = body.get("next_token")
        if not next_token:
            break

        # For subsequent pages, use next_token instead of date params
        params = {"next_token": next_token}
        page += 1

    return all_records

def write_to_snowflake(records):
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        private_key=load_private_key(SNOWFLAKE_PRIVATE_KEY_PATH),
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema="RAW_OURA"
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RAW_SLEEP (
            id STRING,
            day DATE,
            raw_json STRING,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    # MERGE upsert — idempotent, no duplicates on re-run
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        values = [
            (record.get("id"), record.get("day"), json.dumps(record))
            for record in batch
        ]
        cursor.executemany(
            """MERGE INTO RAW_SLEEP AS target
            USING (SELECT %s AS id, %s AS day, %s AS raw_json) AS source
            ON target.id = source.id
            WHEN MATCHED THEN UPDATE SET
                day = source.day,
                raw_json = source.raw_json,
                loaded_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (id, day, raw_json)
                VALUES (source.id, source.day, source.raw_json)""",
            values
        )
        print(f"  MERGE batch {i // batch_size + 1} of {(len(records) - 1) // batch_size + 1}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Wrote {len(records)} records to RAW_OURA.RAW_SLEEP (MERGE upsert)")

if __name__ == "__main__":
    print(f"Fetching Oura sleep data from {start_date} to {end_date}...")
    records = fetch_oura_sleep(start_date, end_date)
    print(f"Fetched {len(records)} total records")
    write_to_snowflake(records)