# Project 2: Regime-Aware Dashboard

## Executive Summary

Project 2 operationalizes the findings from Project 1 in a self-hosted Metabase
dashboard. Rather than displaying signal baselines computed against a rolling
global mean, baselines are partitioned at the PELT-detected regime boundaries
from Project 1, so each signal's reference statistics (mean, SD, min, max)
reflect only observations within the same physiological regime. The dashboard
is the applied output; Project 1 provides its statistical justification.

## Motivation

Rolling-window baselines assume the underlying signal is stationary within the
window. Project 1 showed that HRV and resting HR are trend-stationary in this
dataset: they exhibit directional drift across physiological regimes, and the
30-day rolling mean either lagged the transition by 7 days (HRV) or missed it
entirely (resting HR). A regime-aware dashboard addresses this directly: each
panel computes its reference band only from observations in the same regime,
so a genuine adaptation (cardiac remodeling under marathon training) does not
inflate the baseline for the following regime.

## Method

A dbt model, `mart_regime_labels`, extends `DAILY_HEALTH_SUMMARY` with per-row
regime labels (`REGIME_HRV`, `REGIME_RESTING_HR`) and within-regime descriptive
statistics. Regime boundaries are hardcoded from Project 1's PELT output:

| Signal | Regime 1 | Regime 2 |
|---|---|---|
| Average HRV | 2025-11-25 to 2025-12-27 | 2025-12-28 to present |
| Lowest Heart Rate | 2025-11-25 to 2026-02-27 | 2026-02-28 to present |
| Sleep Efficiency | Single regime | |
| Readiness Score | Single regime | |

Do not modify these boundaries without re-running
`analyses/physiological_nonstationarity/analysis.py`.

The Metabase dashboard queries `MART_HEALTH.MART_REGIME_LABELS` directly.
Three panels are planned: time-series plots with regime shading and within-regime
mean +/- 1 SD bands, a regime summary table (per-regime descriptive stats per
signal), and a detection latency callout card.

## Data

Source: `MART_HEALTH.MART_REGIME_LABELS` in Snowflake. This is the authoritative
source of truth. The file `data/regime_labels.csv` is a local export artifact
excluded from version control (health data policy); regenerate it by querying
`MART_HEALTH.MART_REGIME_LABELS` and exporting to CSV.

<!-- data/regime_labels.csv is excluded from version control (health data policy).
     Regenerate by querying MART_HEALTH.MART_REGIME_LABELS in Snowflake and exporting to CSV. -->

## Results

Dashboard in progress. Metabase stack is running at `localhost:3000` via
`infra/metabase/`. The `mart_regime_labels` dbt model is complete and queryable.
Dashboard panels are under construction.

## Limitations

**Fixed regime boundaries.** Regime boundaries are hardcoded from a single
Project 1 run. They are not re-detected dynamically as new data arrives. Any
new physiological regime transition will not be reflected until Project 1 is
re-run and the dbt model is updated manually.

**n=1.** All baselines are personal. Reference statistics have no population
comparison and cannot be validated against clinical norms.

**Short window.** At 130+ days, the dataset contains only two detected
transitions. Regime statistics computed from a single short regime (e.g., Regime
1 HRV: 33 days) carry wide uncertainty that the dashboard does not currently
quantify.

**Metabase OSS limitations.** No native alerting, no row-level security, no
scheduled exports without the paid tier. Suitable for a personal analytics
portfolio; not production-grade for multi-user or clinical contexts.

## What Next

- Complete the three Metabase dashboard panels (time-series, regime summary
  table, detection latency callout)
- Power BI equivalent DAX measures and connector documentation in
  `power_bi_equivalent/` as a stack portability reference
- Automate Snowflake connection provisioning via Metabase REST API to make
  the stack fully declarative on first boot
