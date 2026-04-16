# dbt: Health Analytics Transformation Layer

Transforms raw ingested data from Snowflake's raw schemas into a unified
daily health summary mart and a regime-labeled analysis table derived from
Project 1's PELT change-point results.

---

## Project

dbt project name: `health_analytics`  
Profile: `health_analytics` (configured in `~/.dbt/profiles.yml`)  
Target database: `HEALTH_ANALYTICS`

All models land in the `MART_HEALTH` schema. The `generate_schema_name`
macro overrides dbt's default behavior of concatenating the target schema
prefix; models resolve to `MART_HEALTH` directly rather than
`{target_schema}_MART_HEALTH`.

---

## Running dbt

Commands must be run from this directory (`dbt/`), not the repo root:

```bash
cd dbt/

dbt run                        # build all models
dbt run --select staging       # staging layer only
dbt run --select marts         # mart layer only
dbt run --select daily_health_summary
dbt run --select mart_regime_labels
```

---

## Model Reference

### Staging (views, `MART_HEALTH`)

| Model | Source table | Description |
|---|---|---|
| `stg_oura_sleep` | `RAW_OURA.RAW_SLEEP` | Parses JSON string with `PARSE_JSON()`, extracts sleep metrics, filters `long_sleep` type |
| `stg_apple_health_heart_rate` | `RAW_APPLE_HEALTH.RAW_HEART_RATE` | Casts timestamps, surfaces per-reading heart rate values |
| `stg_apple_health_body_composition` | `RAW_APPLE_HEALTH.RAW_BODY_COMPOSITION` | Pivots four body composition measurement types per row; corrects RENPHO body fat decimal encoding |
| `stg_strava_activities` | `RAW_STRAVA.RAW_ACTIVITIES` | Parses JSON activity records, surfaces distance, kilojoules, elapsed time, elevation, sport type |

Raw layer stores all JSON as `STRING`. `PARSE_JSON()` is called at the
staging layer (intentional; documented in repo root CLAUDE.md).

### Marts (tables, `MART_HEALTH`)

**`daily_health_summary`**  
Unified daily grain. Joins all four staging models on `activity_date`.
Sleep spine is the primary grain (one row per night of `long_sleep`,
selected by `ROW_NUMBER()` on `total_sleep_duration DESC` to exclude naps).
Body composition is forward-filled via `LAST_VALUE IGNORE NULLS` across the
sleep date spine to handle infrequent weigh-in cadence. Strava activities
aggregate to daily totals.

**`mart_regime_labels`**  
Regime-annotated extension of `daily_health_summary`. Adds per-row regime
labels (`REGIME_HRV`, `REGIME_RESTING_HR`) derived from PELT change-point
boundaries detected in Project 1, plus within-regime descriptive statistics
(mean, SD, min, max, ±1 SD bands) for all four signals. Used as the primary
data source for the Project 2 Metabase dashboard.

> Regime boundaries are hardcoded from PELT output. Do not modify without
> re-running `analyses/physiological_nonstationarity/analysis.py`.

---

## Macros

**`generate_schema_name`**  
Overrides dbt's default schema naming to prevent target-schema prefixing.
Without this macro, a model configured with `+schema: MART_HEALTH` would
land in `PUBLIC_MART_HEALTH` (or equivalent) rather than `MART_HEALTH`.

---

## Key Design Decisions

- Raw layer is `STRING`, not `VARIANT`; `PARSE_JSON()` at staging
- `long_sleep` filter via `ROW_NUMBER()` prevents nap contamination of the daily grain
- Body composition forward-fill handles sparse RENPHO measurement cadence
- RENPHO body fat stored as decimal (e.g. `0.113`), corrected with a `CASE` multiplier in staging
- Strava ingestion is incremental; dbt staging reads the full current state
