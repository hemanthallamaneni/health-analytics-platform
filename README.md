# Health Analytics Platform

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9)
![Snowflake](https://img.shields.io/badge/Snowflake-warehouse-29B5E8?logo=snowflake&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-transformation-FF694B?logo=dbt&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

A longitudinal personal health data platform and methods portfolio investigating
physiological nonstationarity in wearable sensor data.

---

## Abstract

Commercial wearable algorithms assume that each user's physiological signals are
stationary within a rolling window, computing readiness and recovery scores
against a slowly adapting baseline. This research program tests that assumption
empirically on continuous data from an Oura Ring, Apple Watch, and Strava,
finding that heart rate variability and resting heart rate are trend-stationary
rather than stationary — they drift directionally across physiological regimes
in ways a rolling mean either detects late or misses entirely. Two discrete
regime transitions are identified via PELT change-point detection, each
physiologically annotated: one consistent with environmental disruption, one
consistent with cardiovascular adaptation under sustained aerobic training. A
regime-aware baseline framework and a training-load characterization of
transition heterogeneity complete the three-project arc. The full analytical
stack — from raw API ingestion to materialized data mart to statistical analysis
— is documented, reproducible, and publicly available.

---

## Thesis

Commercial wearable algorithms compute recovery and readiness scores against a
rolling baseline that assumes the underlying physiological signal is stationary
within a window. This portfolio investigates what happens when that assumption
fails: empirically, operationally, and predictively, across three connected
projects.

---

## Portfolio Structure

| Project | Status | Description |
|---|---|---|
| [Project 1: Physiological Nonstationarity Investigation](#project-1-physiological-nonstationarity-investigation) | ✅ Complete | Stationarity tests, change-point detection, detection latency analysis |
| [Project 2: Regime-Aware Operations Dashboard](#project-2-regime-aware-operations-dashboard) | 🔄 Data layer complete; dashboard panels in construction | Self-hosted Metabase dashboard with within-regime baseline computation |
| [Project 3: Training Load as a Predictor of Regime Transitions](#project-3-training-load-as-a-predictor-of-regime-transitions) | ✅ Complete | Training-load characterization of regime transition heterogeneity |

---

## Project 1: Physiological Nonstationarity Investigation

**[→ Full analysis and findings](analyses/physiological_nonstationarity/README.md)**

Applied ADF and KPSS stationarity tests to daily Oura Ring data spanning
November 2025 through April 2026 across four signals: HRV, resting heart rate,
sleep efficiency, and Oura's composite readiness score. HRV and resting HR are
trend-stationary, exhibiting directional drift inconsistent with a fixed-mean
baseline. Sleep efficiency and readiness score are stationary in this window.

PELT change-point detection (RBF kernel) identified two discrete regime
transitions, both physiologically annotated:

| Date | Signal | Direction | Event |
|---|---|---|---|
| 2025-12-27 | Average HRV | ↓ 16.7% | Travel disruption (3-week interstate stay) |
| 2026-02-27 | Resting HR | ↓ 9.3% | Marathon training block initiated |

A 30-day rolling mean lagged PELT by 7 days on the HRV transition and failed to
detect the resting HR transition entirely. This detection latency result is the
quantitative justification for the regime-aware baseline approach in Project 2.

![Nonstationarity Analysis](analyses/physiological_nonstationarity/results/nonstationarity_analysis.png)

*Four signals on a shared time axis. Faint traces: daily values. Bold lines: 30-day rolling mean. Dashed vertical lines: PELT-detected change-points. Shaded regions: detected physiological regimes. Event annotations mark the life and training context of each transition.*

**Methods:** ADF · KPSS · PELT (ruptures, RBF kernel) · Detection latency
analysis  
**Stack:** Python · Snowflake · dbt · statsmodels · ruptures · matplotlib

---

## Project 2: Regime-Aware Operations Dashboard

**[→ Full design and status](analyses/regime_dashboard/README.md)**

Self-hosted Metabase dashboard operationalizing the Project 1 findings. Rather
than computing signal baselines against a rolling global mean, baselines are
computed within PELT-detected regimes, partitioning each signal's history at
detected change-point boundaries before calculating reference statistics.

The dbt model `mart_regime_labels` is complete and production-ready: it extends
`DAILY_HEALTH_SUMMARY` with per-row regime labels and within-regime descriptive
statistics (mean, SD, min, max, ±1 SD bands). Power BI equivalent DAX measures
are documented in `analyses/regime_dashboard/power_bi_equivalent/` as a stack
portability reference. Dashboard panels in Metabase are in final construction.

The detection latency result from Project 1 (a naive rolling mean missing a
real 4.54 bpm resting HR regime shift entirely) motivates this design decision
quantitatively.

**Methods:** Regime-aware baseline computation · Metabase · Snowflake  
**Stack:** Metabase (Docker) · Snowflake · dbt · Python

---

## Project 3: Training Load as a Predictor of Regime Transitions

**[→ Full analysis and findings](analyses/training_load_predictors/README.md)**

Takes the annotated change-points from Project 1 as outcome variables and asks
whether training load metrics in the preceding 14-day window share a common
signature. They do not. The HRV transition followed 28 days of zero training
(travel-related interruption), while the resting HR transition followed an acute
training-load spike with an acute-to-chronic workload ratio (ACWR) at the 100th
percentile of all 14-day windows in the dataset. The two regime shifts reflect
distinct underlying mechanisms — one consistent with detraining, one consistent
with overload — rather than a single training-load process.

![Feature Distributions](analyses/training_load_predictors/results/feature_distributions.png)

*Per-feature comparison of 14-day pre-transition training-load values (dashed vertical lines) against the full distribution of rolling 14-day windows. The pre-RHR transition window shows ACWR distance at the dataset maximum; the pre-HRV transition window shows zero load across all cumulative measures.*

**Methods:** Percentile rank characterization · Permutation testing (10,000
iterations) · ACWR (Gabbett 2016)  
**Stack:** Python · Snowflake · dbt · scipy · numpy · matplotlib

---

## Data Infrastructure

Four ingestion sources, all production-grade and running on a scheduled pipeline:

| Source | Method | Schema |
|---|---|---|
| Oura Ring | REST API (paginated, full-history) | `RAW_OURA` |
| Apple Health | HealthKit XML export (heart rate) | `RAW_APPLE_HEALTH` |
| Apple Health / RENPHO | HealthKit XML export (body composition) | `RAW_APPLE_HEALTH` |
| Strava | OAuth2 with auto-refresh (incremental) | `RAW_STRAVA` |

All sources land in Snowflake, transform through dbt staging models, surface
in a unified daily summary mart (`MART_HEALTH.DAILY_HEALTH_SUMMARY`), and are
visualized in Metabase. The `ingestion/healthfit/` directory is a retired stub
from an earlier pipeline iteration, superseded by the direct Apple Health XML
parsing pipeline.

**Stack:** Python 3.12 · pyenv · uv · Snowflake · dbt · Metabase · Ubuntu 22.04

---

## Repository Structure

```
health-analytics-platform/
├── ingestion/                              # Python ingestion scripts
│   ├── oura/                               # Oura REST API → Snowflake
│   ├── apple_health/                       # Apple Health XML → Snowflake
│   ├── strava/                             # Strava OAuth2 → Snowflake
│   ├── healthfit/                          # Retired stub (superseded by apple_health)
│   └── common/                             # Shared auth (Snowflake key pair)
├── dbt/                                    # dbt transformation layer
│   ├── models/
│   │   ├── staging/                        # Source-specific views
│   │   │   ├── stg_oura_sleep.sql
│   │   │   ├── stg_apple_health_heart_rate.sql
│   │   │   ├── stg_apple_health_body_composition.sql
│   │   │   ├── stg_strava_activities.sql
│   │   │   └── sources.yml
│   │   └── marts/                          # Materialized analytical tables
│   │       ├── daily_health_summary.sql
│   │       ├── mart_regime_labels.sql
│   │       └── mart_training_load_features.sql
│   └── macros/                             # generate_schema_name override
├── analyses/
│   ├── physiological_nonstationarity/      # Project 1
│   │   ├── analysis.py
│   │   ├── README.md
│   │   └── results/
│   ├── regime_dashboard/                   # Project 2
│   │   ├── README.md
│   │   ├── screenshots/
│   │   └── power_bi_equivalent/
│   └── training_load_predictors/           # Project 3
│       ├── analysis.py
│       ├── README.md
│       └── results/
├── infra/
│   └── metabase/                           # Docker Compose stack + setup guide
├── run_pipeline.sh                         # End-to-end ingestion + dbt orchestration
├── SETUP.md                                # Reproduction instructions
└── README.md
```

For full reproduction instructions, see [SETUP.md](SETUP.md).

---

## Background

Built to support a research program in applied physiological monitoring. Personal
data as a methodological testbed for techniques relevant to healthcare workforce
monitoring, clinical remote patient monitoring, and sports science. The n=1
constraint is real and documented honestly in each analysis; the methods
generalize to multi-subject cohorts and are framed as such in the research
directions sections.

**Author:** Hemanth Allamaneni  
MS Applied Cognition and Neuroscience (HCI and Intelligent Systems), UT Dallas, 2025  
[github.com/hemanthallamaneni](https://github.com/hemanthallamaneni)