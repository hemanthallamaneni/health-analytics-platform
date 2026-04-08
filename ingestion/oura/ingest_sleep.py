import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

OURA_PAT = os.getenv("OURA_PAT")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")

# Pull last 30 days of sleep data
end_date = datetime.today().strftime("%Y-%m-%d")
start_date = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")

def fetch_oura_sleep(start, end):
    url = "https://api.ouraring.com/v2/usercollection/sleep"
    headers = {"Authorization": f"Bearer {OURA_PAT}"}
    params = {"start_date": start, "end_date": end}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("data", [])

def write_to_snowflake(records):
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema="RAW_OURA"
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RAW_SLEEP (
            id STRING,
            day DATE,
            raw_json VARIANT,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    for record in records:
        cursor.execute(
            "INSERT INTO RAW_SLEEP (id, day, raw_json) SELECT %s, %s, PARSE_JSON(%s)",
            (record.get("id"), record.get("day"), json.dumps(record))
        )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Wrote {len(records)} records to RAW_OURA.RAW_SLEEP")

if __name__ == "__main__":
    print(f"Fetching Oura sleep data from {start_date} to {end_date}...")
    records = fetch_oura_sleep(start_date, end_date)
    print(f"Fetched {len(records)} records")
    write_to_snowflake(records)