# Health Analytics Platform

A personal health data pipeline that ingests, transforms, and analyzes data from Oura Ring, Apple Health (including RENPHO body composition), and Strava using a modern ELT stack.

## Why this exists

Personal health data lives in siloed apps. Oura tracks sleep and recovery, Apple Health collects heart rate and biometrics, Strava captures workouts. Each app has its own dashboard, but none of them talk to each other — and none of them support cross-source questions like "how does sleep quality two nights before a long run correlate with run performance?"

This project consolidates all sources into a single warehouse, builds a unified daily metrics model, and creates the foundation for physiological modeling and analysis that no individual app supports natively.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Source Systems                   │
│                                                     │
│   Oura API v2  •  Apple Health XML  •  Strava API   │
│                 (incl. RENPHO via HealthKit)        │
└────────────────────────┬────────────────────────────┘
                         │
                         │  Python ingestion scripts
                         │  (incremental & full-refresh)
                         ▼
┌─────────────────────────────────────────────────────┐
│                 Snowflake Warehouse                 │
│                                                     │
│   RAW_OURA  •  RAW_APPLE_HEALTH  •  RAW_STRAVA      │
└────────────────────────┬────────────────────────────┘
                         │
                         │  dbt transformation
                         │  (staging → marts)
                         ▼
┌─────────────────────────────────────────────────────┐
│                   MART_HEALTH                       │
│                                                     │
│   DAILY_HEALTH_SUMMARY — one row per day            │
│   Sleep · HRV · Heart Rate · Body Composition       │
│   Workouts · Training Load                          │
└─────────────────────────────────────────────────────┘
```

## Tech stack

| Tool | Purpose |
|------|---------|
| Python 3.12.13 | Ingestion scripts |
| pyenv | Python version management |
| uv | Dependency and virtual environment management |
| Snowflake | Analytical warehouse |
| dbt | SQL transformation, staging, and marts |
| Oura API v2 | Sleep, HRV, readiness data |
| Apple Health XML | Heart rate and body composition via HealthKit |
| RENPHO (via HealthKit) | Weight, BMI, body fat %, lean body mass |
| Strava API v3 | Workout data with OAuth2 and incremental ingestion |

## Repository structure

```
health-analytics-platform/
├── pyproject.toml                        # Project metadata and dependencies
├── uv.lock                               # Exact dependency versions
├── .python-version                       # Python version pin (3.12.13)
├── .env.example                          # Credential template — copy to .env
├── run_pipeline.sh                       # Unified pipeline runner
├── README.md
├── ingestion/
│   ├── oura/
│   │   └── ingest_sleep.py               # Oura API — last 30 days of sleep
│   ├── apple_health/
│   │   ├── ingest_heart_rate.py          # Apple Health XML — full history
│   │   └── ingest_body_composition.py    # RENPHO body metrics via HealthKit
│   └── strava/
│       └── ingest_activities.py          # Strava OAuth2 — incremental
├── dbt/
│   ├── dbt_project.yml
│   ├── macros/
│   │   └── generate_schema_name.sql      # Schema naming override
│   └── models/
│       ├── staging/
│       │   ├── stg_oura_sleep.sql
│       │   ├── stg_apple_health_heart_rate.sql
│       │   ├── stg_apple_health_body_composition.sql
│       │   └── stg_strava_activities.sql
│       └── marts/
│           └── daily_health_summary.sql  # Unified daily metrics table
├── data/                                 # Gitignored — local data only
│   └── raw/
│       └── apple_health/                 # Apple Health XML export
├── docs/
└── tests/
```

## Environment setup

### Prerequisites

- Linux or macOS
- pyenv with Python 3.12.13
- uv for dependency management
- Snowflake account (free tier sufficient)
- Oura Ring with a personal access token
- Strava account with an API application registered at strava.com/settings/api

### Installation

```bash
git clone https://github.com/hemanthallamaneni/health-analytics-platform.git
cd health-analytics-platform
pyenv local 3.12.13
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
```

### Credentials

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

Required fields:

```
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=
OURA_PAT=
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_ACCESS_TOKEN=
STRAVA_REFRESH_TOKEN=
STRAVA_TOKEN_EXPIRES_AT=
```

For Strava, the access token, refresh token, and expiry are obtained via a one-time OAuth2 authorization flow. After that the script handles token refresh automatically on every run.

### Snowflake setup

The pipeline expects the following structure in Snowflake:

- Database: `HEALTH_ANALYTICS`
- Raw schemas: `RAW_OURA`, `RAW_APPLE_HEALTH`, `RAW_STRAVA`
- Mart schema: `MART_HEALTH`

To create these, run the following in a Snowflake worksheet:

```sql
CREATE DATABASE IF NOT EXISTS HEALTH_ANALYTICS;
CREATE SCHEMA IF NOT EXISTS HEALTH_ANALYTICS.RAW_OURA;
CREATE SCHEMA IF NOT EXISTS HEALTH_ANALYTICS.RAW_APPLE_HEALTH;
CREATE SCHEMA IF NOT EXISTS HEALTH_ANALYTICS.RAW_STRAVA;
CREATE SCHEMA IF NOT EXISTS HEALTH_ANALYTICS.MART_HEALTH;
```

### dbt setup

```bash
cd dbt
dbt debug    # verify Snowflake connection
dbt run      # build all models
```

## Running the pipeline

### Unified runner (recommended)

```bash
./run_pipeline.sh
```

Runs in sequence:

1. **Oura** — pulls last 30 days of sleep data (automatic)
2. **Strava** — fetches new activities since last run (automatic, incremental)
3. **Apple Health** — prompts before running. Press `Enter` if you have a fresh export, or `s` to skip
4. **dbt** — refreshes all staging models and the daily summary mart

### Individual scripts

```bash
source .venv/bin/activate

python ingestion/oura/ingest_sleep.py
python ingestion/strava/ingest_activities.py
python ingestion/apple_health/ingest_heart_rate.py
python ingestion/apple_health/ingest_body_composition.py

cd dbt && dbt run
```

## Updating Apple Health data

Apple Health has no API. Data is exported manually from the iPhone and re-ingested as a full refresh.

**Step 1 — Export from iPhone:**

1. Open the Health app
2. Tap your profile picture → Export All Health Data
3. Share the ZIP to your machine via AirDrop, email, or iCloud Drive

**Step 2 — Replace the existing export:**

```bash
cd ~/work/personal/health-analytics-platform/data/raw/apple_health
unzip ~/Downloads/export.zip -d apple_health_export_new
rm -rf apple_health_export
mv apple_health_export_new apple_health_export
```

**Step 3 — Re-ingest:**

```bash
source .venv/bin/activate
python ingestion/apple_health/ingest_heart_rate.py
python ingestion/apple_health/ingest_body_composition.py
cd dbt && dbt run
```

RENPHO body composition data (weight, BMI, body fat %, lean body mass) syncs automatically from the RENPHO app into Apple Health and is captured in step 3 above. No separate RENPHO integration is needed.

## Data sources and ingestion patterns

| Source | Method | Pattern | Schema |
|--------|--------|---------|--------|
| Oura Ring | REST API (PAT auth) | Full refresh, last 30 days | RAW_OURA |
| Apple Health heart rate | XML export (HealthKit) | Full refresh on demand | RAW_APPLE_HEALTH |
| RENPHO body composition | XML export (via HealthKit) | Full refresh on demand | RAW_APPLE_HEALTH |
| Strava workouts | REST API (OAuth2) | Incremental | RAW_STRAVA |

## dbt model lineage

```
RAW_OURA.RAW_SLEEP
    └── stg_oura_sleep (view)
            └── daily_health_summary (table)

RAW_APPLE_HEALTH.RAW_HEART_RATE
    └── stg_apple_health_heart_rate (view)
            └── daily_health_summary (table)

RAW_APPLE_HEALTH.RAW_BODY_COMPOSITION
    └── stg_apple_health_body_composition (view)
            └── daily_health_summary (table)

RAW_STRAVA.RAW_ACTIVITIES
    └── stg_strava_activities (view)
            └── daily_health_summary (table)
```

The mart table `DAILY_HEALTH_SUMMARY` contains one row per day anchored to Oura sleep dates. Body composition metrics are forward-filled across days without a scale measurement.

## Current status

- [x] Project scaffolded with uv and Python 3.12.13
- [x] Snowflake warehouse configured with raw and mart schemas
- [x] Oura sleep ingestion
- [x] Apple Health heart rate ingestion
- [x] Apple Health body composition ingestion (RENPHO via HealthKit)
- [x] Strava activity ingestion with OAuth2 and incremental logic
- [x] dbt staging models for all four sources
- [x] Unified daily health summary mart with forward-filled body metrics
- [x] Unified pipeline runner script
- [ ] dbt tests (not-null, unique, accepted values)
- [ ] Orchestration (scheduled runs)
- [ ] Analytical models (Projects 1–5)

## Data privacy

No health data, credentials, or personally identifiable information is committed to this repository. All files in `data/` are gitignored. Secrets live in a local `.env` file excluded from version control.

## Author

Hemanth Allamaneni · [github.com/hemanthallamaneni](https://github.com/hemanthallamaneni)