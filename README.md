# Health Analytics Platform

A personal health data pipeline that ingests, transforms, and analyzes data from
Oura Ring, Apple Health, and HealthFit using a modern ELT stack: Python for
ingestion, Snowflake as the warehouse, and dbt for transformation.

## Why this exists

Personal health data lives in siloed apps. Oura tracks sleep and recovery,
Apple Health collects activity and biometrics, HealthFit captures workouts.
Each app has its own dashboard, but none of them talk to each other, and none
of them let me ask cross-source questions like "how does sleep quality two
nights before a long run correlate with run performance?"

This project consolidates all three sources into a single warehouse, builds a
unified daily metrics model on top, and creates the foundation for analytical
work that none of the source apps support natively.

## Architecture
┌─────────────────────────────────────┐
                │           Source Systems            │
                │                                     │
                │  Oura API  •  Apple Health Export   │
                │           HealthFit CSV             │
                └──────────────────┬──────────────────┘
                                   │
                                   │  Python ingestion
                                   │  (scheduled & on-demand)
                                   ▼
                ┌─────────────────────────────────────┐
                │         Snowflake Warehouse         │
                │                                     │
                │  raw_oura  •  raw_apple_health      │
                │          raw_healthfit              │
                └──────────────────┬──────────────────┘
                                   │
                                   │  dbt transformation
                                   │  (staging → marts)
                                   ▼
                ┌─────────────────────────────────────┐
                │            mart_health              │
                │                                     │
                │   Unified daily metrics model       │
                │   ready for analysis & dashboards   │
                └─────────────────────────────────────┘
## Tech stack

- **Python 3.12** managed via pyenv, with uv for dependency and environment management
- **Snowflake** as the analytical warehouse (free tier)
- **dbt** for SQL-based transformation, testing, and documentation
- **Oura API v2** for ring data (sleep, readiness, activity, HRV)
- **Apple Health export** parsed from the iOS Health app's XML export
- **HealthFit CSV exports** for workout-level data

## Repository structure
health-analytics-platform/
├── pyproject.toml          # Project metadata and dependencies (managed by uv)
├── uv.lock                 # Exact dependency versions for reproducibility
├── .python-version         # Python version pin (3.12.13)
├── README.md               # This file
├── ingestion/              # Python ingestion scripts
│   ├── oura/               # Oura API client and data fetcher
│   ├── apple_health/       # Apple Health XML parser
│   └── healthfit/          # HealthFit CSV ingestion
├── dbt/                    # dbt project (staging models and marts)
├── data/                   # Local data files (gitignored)
│   ├── raw/                # Raw exports from sources
│   └── processed/          # Intermediate processed files
├── docs/                   # Architecture and design documentation
└── tests/                  # Python tests for ingestion code
## Current status

This project is under active development. Current state:

- [x] Project scaffolded with uv and Python 3.12.13
- [x] Repository structure established
- [ ] Snowflake account and warehouse configured
- [ ] Oura API ingestion implemented
- [ ] Apple Health XML parser implemented
- [ ] HealthFit CSV ingestion implemented
- [ ] dbt project initialized with source definitions
- [ ] Staging models for each source
- [ ] Unified daily metrics mart
- [ ] dbt tests and documentation

## Data privacy

This is a personal health analytics project. The repository contains code only.
No actual health data, credentials, API tokens, or personally identifiable
information is committed to git. All data files in `data/` are gitignored, and
secrets live in a local `.env` file that is excluded from version control.

## Setup (work in progress)

Setup instructions will be documented here as the project matures. The current
prerequisites are:

- Linux or macOS with a modern shell
- pyenv with Python 3.12.13 installed
- uv for dependency management
- A Snowflake account (free tier is sufficient)
- An Oura Ring with Premium subscription and a personal access token

## Author

Hemanth Allamaneni

