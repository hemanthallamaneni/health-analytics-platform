#!/bin/bash
set -e

echo "=== Health Analytics Pipeline ==="
cd "$(dirname "$0")"
source .venv/bin/activate

echo ""
echo "[1/6] Oura sleep ingestion..."
python ingestion/oura/ingest_sleep.py

echo ""
echo "[2/6] Oura readiness ingestion..."
python ingestion/oura/ingest_readiness.py

echo ""
echo "[3/6] Strava activity ingestion..."
python ingestion/strava/ingest_activities.py

echo ""
echo "[4/6] Strava streams ingestion..."
python ingestion/strava/ingest_streams.py

echo ""
echo "[5/6] Apple Health ingestion..."
echo "NOTE: Apple Health requires a manual export from iPhone."
echo "If you have a fresh export, press Enter to ingest. Otherwise press 's' to skip."
read -r response
if [[ "$response" != "s" ]]; then
    python ingestion/apple_health/ingest_heart_rate.py
    python ingestion/apple_health/ingest_body_composition.py
else
    echo "Skipping Apple Health ingestion."
fi

echo ""
echo "[6/6] Running dbt transformations..."
cd dbt
dbt run

echo ""
echo "=== Pipeline complete ==="
