import os
import sys
import json
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import snowflake.connector

# TODO(audit H3): sys.path workaround removable once pyproject.toml declares
# [build-system] and `uv sync` installs the ingestion package into the venv.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ingestion.common.snowflake_auth import load_private_key

load_dotenv()

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PRIVATE_KEY_PATH = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")

XML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'data', 'raw', 'apple_health', 'apple_health_export', 'export.xml'
)

def fetch_heart_rate_data():
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    heart_rate_records = []
    for record in root.findall('Record[@type="HKQuantityTypeIdentifierHeartRate"]'):
        heart_rate_records.append({
            "id": f"{record.get('startDate')}_{record.get('sourceName')}",
            "source": record.get("sourceName"),
            "start_date": record.get("startDate"),
            "end_date": record.get("endDate"),
            "heart_rate": record.get("value"),
            "unit": record.get("unit"),
            "creation": record.get("creationDate"),
        })
    return heart_rate_records

def write_to_snowflake(records):
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        private_key=load_private_key(SNOWFLAKE_PRIVATE_KEY_PATH),
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema="RAW_APPLE_HEALTH"
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RAW_HEART_RATE (
            id STRING,
            source STRING,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            heart_rate FLOAT,
            unit STRING,
            creation TIMESTAMP,
            raw_json STRING,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    cursor.execute("TRUNCATE TABLE IF EXISTS RAW_HEART_RATE")

    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        values = [
            (
                r.get("id"),
                r.get("source"),
                r.get("start_date"),
                r.get("end_date"),
                float(r.get("heart_rate")),
                r.get("unit"),
                r.get("creation"),
                json.dumps(r)
            )
            for r in batch
        ]
        cursor.executemany(
                "INSERT INTO RAW_HEART_RATE (id, source, start_date, end_date, heart_rate, unit, creation, raw_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                values
        )
        print(f"Inserted batch {i // batch_size + 1} of {len(records) // batch_size + 1}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Wrote {len(records)} records to RAW_APPLE_HEALTH.RAW_HEART_RATE")

if __name__ == "__main__":
    print("Fetching Apple Health heart rate data...", flush=True)
    records = fetch_heart_rate_data()
    print(f"Fetched {len(records)} records", flush=True)
    write_to_snowflake(records)