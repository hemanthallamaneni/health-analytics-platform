# Setup and Reproduction

Instructions for setting up the development environment and reproducing the
analytical results in this repository.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12.13 | Managed via pyenv |
| pyenv | Latest | [Installation guide](https://github.com/pyenv/pyenv#installation) |
| uv | Latest | [Installation guide](https://docs.astral.sh/uv/getting-started/installation/) |
| Docker Engine | 20.10+ | Required for Metabase stack only |
| Docker Compose | v2+ | Required for Metabase stack only |
| Snowflake account | — | With key pair authentication configured |

---

## Environment Setup

### 1. Clone and enter the repository

```bash
git clone https://github.com/hemanthallamaneni/health-analytics-platform.git
cd health-analytics-platform
```

### 2. Set up Python

```bash
pyenv install 3.12.13
pyenv local 3.12.13
```

### 3. Create the virtual environment and install dependencies

```bash
uv venv
source .venv/bin/activate
uv sync
```

### 4. Configure environment variables

Copy the example and populate with your credentials:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|---|---|
| `SNOWFLAKE_ACCOUNT` | Snowflake account identifier (e.g. `abc12345.us-east-1`) |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PRIVATE_KEY_PATH` | Absolute path to unencrypted PKCS#8 RSA private key (`.p8` file) |
| `SNOWFLAKE_WAREHOUSE` | Compute warehouse name |
| `SNOWFLAKE_DATABASE` | Target database (e.g. `HEALTH_ANALYTICS`) |
| `OURA_PAT` | Oura Ring personal access token |
| `OURA_START_DATE` | Ingestion start date (e.g. `2025-11-25`) |
| `STRAVA_CLIENT_ID` | Strava API application client ID |
| `STRAVA_CLIENT_SECRET` | Strava API application client secret |
| `STRAVA_ACCESS_TOKEN` | Current OAuth2 access token |
| `STRAVA_REFRESH_TOKEN` | Current OAuth2 refresh token |
| `STRAVA_TOKEN_EXPIRES_AT` | Token expiration timestamp (auto-refreshed on runs) |

### 5. Snowflake key pair authentication

This project uses RSA key pair authentication for all Snowflake connections
(Python scripts, dbt, and Metabase). Password auth is deprecated by Snowflake
with enforcement beginning August–October 2026.

Generate a key pair following
[Snowflake's key pair auth documentation](https://docs.snowflake.com/en/user-guide/key-pair-auth).
Set `SNOWFLAKE_PRIVATE_KEY_PATH` in `.env` to the absolute path of your
unencrypted `.p8` private key file.

### 6. Configure dbt

Create or update `~/.dbt/profiles.yml`:

```yaml
health_analytics:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      private_key_path: "{{ env_var('SNOWFLAKE_PRIVATE_KEY_PATH') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      schema: PUBLIC
      threads: 4
```

Verify the connection:

```bash
cd dbt/
dbt debug
cd ..
```

---

## Running the Pipeline

### Full pipeline (ingestion + transformation)

```bash
./run_pipeline.sh
```

This runs all four ingestion sources in sequence, then executes `dbt run` to
rebuild all staging views and mart tables. Apple Health ingestion requires a
manual XML export from iPhone; the script prompts to skip if no fresh export
is available.

### Individual ingestion scripts

```bash
source .venv/bin/activate
python ingestion/oura/ingest_sleep.py
python ingestion/strava/ingest_activities.py
python ingestion/apple_health/ingest_heart_rate.py
python ingestion/apple_health/ingest_body_composition.py
```

### dbt only

```bash
cd dbt/
dbt run                                    # all models
dbt run --select staging                   # staging views only
dbt run --select marts                     # mart tables only
dbt run --select daily_health_summary      # specific model
dbt run --select mart_regime_labels
dbt run --select mart_training_load_features
```

> **Note:** dbt commands must be run from the `dbt/` subdirectory, not the
> repository root.

---

## Running Analyses

### Project 1: Physiological Nonstationarity

```bash
uv run python analyses/physiological_nonstationarity/analysis.py
```

Outputs:
- `results/stationarity_tests.csv`
- `results/regime_means.csv`
- `results/detection_latency.csv`
- `results/nonstationarity_analysis.png`

### Project 3: Training Load Predictors

Requires `mart_training_load_features` to be built first:

```bash
cd dbt/
dbt run --select mart_training_load_features
cd ..
uv run python analyses/training_load_predictors/analysis.py
```

Outputs:
- `results/descriptive_summary.csv`
- `results/permutation_results.csv`
- `results/pre_transition_features.csv`
- `results/feature_distributions.png`

---

## Starting the Metabase Dashboard

```bash
cd infra/metabase/
docker compose up -d
```

First-time setup (admin account, Snowflake connection) is documented in
[infra/metabase/README.md](infra/metabase/README.md).
