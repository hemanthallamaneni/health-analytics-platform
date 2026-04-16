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

RECORD_TYPES = [
    "HKQuantityTypeIdentifierBodyMass",
    "HKQuantityTypeIdentifierBodyMassIndex",
    "HKQuantityTypeIdentifierLeanBodyMass",
    "HKQuantityTypeIdentifierBodyFatPercentage"
]

XML_PATH = '/home/hemu/work/personal/health-analytics-platform/data/raw/apple_health/apple_health_export/export.xml'

tree = ET.parse(XML_PATH)
root = tree.getroot()

def fetch_body_composition_data():
    records = []
    for record_type in RECORD_TYPES:
        for record in root.findall(f'Record[@type="{record_type}"]'):
            records.append({
                "id": f"{record.get('startDate')}_{record.get('sourceName')}_{record_type}",
                "type": record_type,
                "source": record.get("sourceName"),
                "start_date": record.get("startDate"),
                "end_date": record.get("endDate"),
                "value": record.get("value"),
                "unit": record.get("unit"),
                "creation": record.get("creationDate")
            })
    return records

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
        CREATE TABLE IF NOT EXISTS RAW_BODY_COMPOSITION (
            id STRING,
            type STRING,
            source STRING,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            value FLOAT,
            unit STRING,
            creation TIMESTAMP,
            raw_json STRING,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)

    cursor.execute("TRUNCATE TABLE IF EXISTS RAW_BODY_COMPOSITION")

    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        values = [
            (
                r.get("id"),
                r.get("type"),
                r.get("source"),
                r.get("start_date"),
                r.get("end_date"),
                float(r.get("value")) if r.get("value") else None,
                r.get("unit"),
                r.get("creation"),
                json.dumps(r)
            )
            for r in batch
        ]
        cursor.executemany(
            """INSERT INTO RAW_BODY_COMPOSITION 
            (id, type, source, start_date, end_date, value, unit, creation, raw_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            values
        )
        print(f"Inserted batch {i // batch_size + 1}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Wrote {len(records)} records to RAW_APPLE_HEALTH.RAW_BODY_COMPOSITION")

if __name__ == "__main__":
    print("Parsing Apple Health body composition data...")
    records = fetch_body_composition_data()
    print(f"Fetched {len(records)} records")
    write_to_snowflake(records)