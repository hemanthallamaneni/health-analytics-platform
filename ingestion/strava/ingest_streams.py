"""
Strava activity streams ingestion.

Pulls per-second telemetry (heart rate, cadence, velocity, GPS, altitude, grade)
for Run-type activities and stores as long-format raw rows in
RAW_STRAVA.RAW_STREAMS, one row per (activity_id, stream_type).

Incremental: skips activities whose streams are already present.

Designed to run after ingest_activities.py in run_pipeline.sh.
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv, set_key
import snowflake.connector

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ingestion.common.snowflake_auth import load_private_key

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PRIVATE_KEY_PATH = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")

ENV_PATH = os.path.join(os.path.dirname(__file__), "../../.env")

# Stream types we want for the heat acclimation analysis.
# 'time' is always returned and we use it as the index.
STREAM_KEYS = ["time", "heartrate", "cadence", "velocity_smooth",
               "latlng", "altitude", "grade_smooth", "moving"]

# Activity types we ingest streams for. Limit to running for now;
# expand later if cycling/other becomes relevant.
RUN_TYPES = ("Run", "TrailRun", "VirtualRun")


def refresh_token_if_expired():
    """Refresh access token if expired. Re-reads expiry from .env each call
    so it stays correct when run after another script in the same shell."""
    expires_at = int(os.getenv("STRAVA_TOKEN_EXPIRES_AT"))
    access_token = os.getenv("STRAVA_ACCESS_TOKEN")
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    if time.time() > expires_at:
        print("Access token expired, refreshing...")
        response = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        data = response.json()
        new_access_token = data["access_token"]
        new_refresh_token = data["refresh_token"]
        new_expires_at = str(data["expires_at"])
        set_key(ENV_PATH, "STRAVA_ACCESS_TOKEN", new_access_token)
        set_key(ENV_PATH, "STRAVA_REFRESH_TOKEN", new_refresh_token)
        set_key(ENV_PATH, "STRAVA_TOKEN_EXPIRES_AT", new_expires_at)
        return new_access_token
    return access_token


def get_activities_needing_streams(cursor):
    """Return list of (activity_id, start_date) for Run-type activities
    that don't yet have any stream rows in RAW_STREAMS."""
    placeholders = ",".join(["%s"] * len(RUN_TYPES))
    cursor.execute(f"""
        SELECT a.id, a.start_date
        FROM RAW_ACTIVITIES a
        WHERE a.sport_type IN ({placeholders})
        AND NOT EXISTS (
            SELECT 1 FROM RAW_STREAMS s WHERE s.activity_id = a.id
        )
        ORDER BY a.start_date
    """, RUN_TYPES)
    return cursor.fetchall()


def ensure_streams_table(cursor):
    """Create the streams table if it doesn't exist. One row per
    (activity_id, stream_type), JSON column holds the array of values."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RAW_STREAMS (
            activity_id STRING,
            stream_type STRING,
            stream_json STRING,
            original_size INTEGER,
            resolution STRING,
            series_type STRING,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """)


def fetch_streams(activity_id, access_token):
    """Pull all requested streams for one activity at full resolution.
    Returns dict keyed by stream type, or None if the activity has no streams
    (e.g. manual entry, treadmill with no sensors)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    params = {
        "keys": ",".join(STREAM_KEYS),
        "key_by_type": "true",
        "series_type": "time",
        "resolution": "high",
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 404:
        return None
    if response.status_code == 429:
        # Rate limited. Strava: 200/15min, 2000/day.
        # Sleep until the 15-min window resets and let the caller retry.
        print("  Rate limited (429). Sleeping 15 minutes...")
        time.sleep(15 * 60)
        return fetch_streams(activity_id, access_token)
    response.raise_for_status()
    data = response.json()
    if not data:
        return None
    return data


def write_streams(activity_id, streams, cursor):
    """Insert one row per stream type for this activity."""
    rows = []
    for stream_type, payload in streams.items():
        rows.append((
            str(activity_id),
            stream_type,
            json.dumps(payload.get("data")),
            payload.get("original_size"),
            payload.get("resolution"),
            payload.get("series_type"),
        ))
    cursor.executemany(
        """INSERT INTO RAW_STREAMS
        (activity_id, stream_type, stream_json, original_size, resolution, series_type)
        VALUES (%s, %s, %s, %s, %s, %s)""",
        rows,
    )


if __name__ == "__main__":
    access_token = refresh_token_if_expired()
    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        private_key=load_private_key(SNOWFLAKE_PRIVATE_KEY_PATH),
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema="RAW_STRAVA",
    )
    cursor = conn.cursor()
    ensure_streams_table(cursor)

    pending = get_activities_needing_streams(cursor)
    print(f"Found {len(pending)} run-type activities needing streams")

    success_count = 0
    no_streams_count = 0
    error_count = 0

    for i, (activity_id, start_date) in enumerate(pending, start=1):
        print(f"[{i}/{len(pending)}] Activity {activity_id} ({start_date})...", end=" ")
        try:
            streams = fetch_streams(activity_id, access_token)
            if streams is None:
                print("no streams available, skipping")
                no_streams_count += 1
                continue
            write_streams(activity_id, streams, cursor)
            conn.commit()
            stream_types = list(streams.keys())
            print(f"ingested {len(stream_types)} streams: {stream_types}")
            success_count += 1
        except Exception as e:
            print(f"ERROR: {e}")
            error_count += 1
            # Continue rather than abort — one bad activity shouldn't kill the batch.
            continue
        # Be polite to Strava: ~6 req/sec is well under the 200/15min limit.
        time.sleep(0.2)

    cursor.close()
    conn.close()
    print(f"\nDone. Success: {success_count}, No streams: {no_streams_count}, Errors: {error_count}")