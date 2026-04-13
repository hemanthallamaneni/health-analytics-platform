import os
import json
import time
import requests
from dotenv import load_dotenv, set_key
import snowflake.connector

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("STRAVA_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")
TOKEN_EXPIRES_AT = int(os.getenv("STRAVA_TOKEN_EXPIRES_AT"))

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")

ENV_PATH = os.path.join(os.path.dirname(__file__), "../../.env")

def refresh_token_if_expired():
    if time.time() > TOKEN_EXPIRES_AT:
        print("Access token expired, refreshing...")
        response = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token"
        })
        data = response.json()
        new_access_token = data["access_token"]
        new_refresh_token = data["refresh_token"]
        new_expires_at = str(data["expires_at"])
        set_key(ENV_PATH, "STRAVA_ACCESS_TOKEN", new_access_token)
        set_key(ENV_PATH, "STRAVA_REFRESH_TOKEN", new_refresh_token)
        set_key(ENV_PATH, "STRAVA_TOKEN_EXPIRES_AT", new_expires_at)
        return new_access_token
    return ACCESS_TOKEN

def get_last_activity_date(cursor):
    try:
        cursor.execute("""
            SELECT MAX(start_date)
            FROM HEALTH_ANALYTICS.RAW_STRAVA.RAW_ACTIVITIES
        """)
        result = cursor.fetchone()[0]
        return result
    except Exception:
        return None

def fetch_strava_activities(access_token, after_timestamp=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    activities = []
    page = 1
    while True:
        params = {"per_page": 100, "page": page}
        if after_timestamp:
            params["after"] = after_timestamp
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params=params
        )
        data = response.json()
        if not data:
            break
        activities.extend(data)
        page += 1
        print(f"Fetched page {page}, {len(activities)} activities so far...")
    return activities

def write_to_snowflake(records, cursor, conn):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS HEALTH_ANALYTICS.RAW_STRAVA.RAW_ACTIVITIES (
            id STRING,
            name STRING,
            sport_type STRING,
            start_date TIMESTAMP,
            elapsed_time INTEGER,
            distance FLOAT,
            raw_json STRING,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        values = [
            (
                str(r.get("id")),
                r.get("name"),
                r.get("sport_type"),
                r.get("start_date"),
                r.get("elapsed_time"),
                r.get("distance"),
                json.dumps(r)
            )
            for r in batch
        ]
        cursor.executemany(
            """MERGE INTO HEALTH_ANALYTICS.RAW_STRAVA.RAW_ACTIVITIES AS target
            USING (SELECT %s AS id, %s AS name, %s AS sport_type, %s AS start_date,
                          %s AS elapsed_time, %s AS distance, %s AS raw_json) AS source
            ON target.id = source.id
            WHEN MATCHED THEN UPDATE SET
                name = source.name,
                sport_type = source.sport_type,
                start_date = source.start_date,
                elapsed_time = source.elapsed_time,
                distance = source.distance,
                raw_json = source.raw_json,
                loaded_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (id, name, sport_type, start_date, elapsed_time, distance, raw_json)
                VALUES (source.id, source.name, source.sport_type, source.start_date,
                        source.elapsed_time, source.distance, source.raw_json)""",
            values
        )
        print(f"MERGE batch {i // batch_size + 1}")
    conn.commit()

if __name__ == "__main__":
    access_token = refresh_token_if_expired()
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema="RAW_STRAVA"
    )
    cursor = conn.cursor()
    last_date = get_last_activity_date(cursor)
    if last_date:
        after_timestamp = int(last_date.timestamp())
        print(f"Incremental run — fetching activities after {last_date}")
    else:
        after_timestamp = None
        print("First run — fetching all activities")
    activities = fetch_strava_activities(access_token, after_timestamp)
    print(f"Fetched {len(activities)} activities")
    write_to_snowflake(activities, cursor, conn)
    cursor.close()
    conn.close()
    print("Done")
