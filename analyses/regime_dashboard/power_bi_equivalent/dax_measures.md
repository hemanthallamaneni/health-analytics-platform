# Power BI Equivalent — DAX Measures

The Project 2 dashboard's analytical content is largely pre-computed in the
`mart_regime_labels` dbt model. This document specifies the minimal set of
DAX measures required to surface that content in Power BI visuals.

Most measures are simple wrappers around aggregated mart columns. The mart
stores per-regime statistics on every row, so a measure like
`AVERAGE(RegimeLabels[REGIME_HRV_MEAN])` returns the regime-specific mean
without requiring DAX to compute it.

## Time-series measures

```dax
HRV (daily) =
SUM(RegimeLabels[AVERAGE_HRV])

Resting HR (daily) =
SUM(RegimeLabels[LOWEST_HEART_RATE])

Sleep efficiency (daily) =
SUM(RegimeLabels[SLEEP_EFFICIENCY])

Readiness score (daily) =
SUM(RegimeLabels[READINESS_SCORE])
```

These are intentionally `SUM` rather than `AVG` because there is exactly one
row per `ACTIVITY_DATE` in the mart. `SUM` over a single value returns that
value; using `AVG` produces the same result with slightly more compute.

## Within-regime baseline measures

```dax
Regime HRV mean (current row) =
AVERAGE(RegimeLabels[REGIME_HRV_MEAN])

Regime HRV upper band =
AVERAGE(RegimeLabels[REGIME_HRV_UPPER])

Regime HRV lower band =
AVERAGE(RegimeLabels[REGIME_HRV_LOWER])

Regime resting HR mean =
AVERAGE(RegimeLabels[REGIME_RHR_MEAN])

Regime resting HR upper band =
AVERAGE(RegimeLabels[REGIME_RHR_UPPER])

Regime resting HR lower band =
AVERAGE(RegimeLabels[REGIME_RHR_LOWER])
```

When plotted with `ACTIVITY_DATE` on the x-axis and grouped by `REGIME_HRV`
(or `REGIME_RESTING_HR`), each measure renders as a flat step line per regime
because the underlying column values are constant within each regime.

## Regime delta measures

For the summary table panel, two measures quantify the absolute regime shift
in user-facing units:

```dax
HRV regime shift (ms) =
VAR baseline_mean =
    CALCULATE(
        AVERAGE(RegimeLabels[REGIME_HRV_MEAN]),
        RegimeLabels[REGIME_HRV] = "Regime 1"
    )
VAR post_travel_mean =
    CALCULATE(
        AVERAGE(RegimeLabels[REGIME_HRV_MEAN]),
        RegimeLabels[REGIME_HRV] = "Regime 2"
    )
RETURN
    baseline_mean - post_travel_mean

Resting HR regime shift (bpm) =
VAR pre_training_mean =
    CALCULATE(
        AVERAGE(RegimeLabels[REGIME_RHR_MEAN]),
        RegimeLabels[REGIME_RESTING_HR] = "Regime 1"
    )
VAR marathon_training_mean =
    CALCULATE(
        AVERAGE(RegimeLabels[REGIME_RHR_MEAN]),
        RegimeLabels[REGIME_RESTING_HR] = "Regime 2"
    )
RETURN
    pre_training_mean - marathon_training_mean
```

Expected results based on Project 1's analysis: HRV regime shift returns
approximately 13.53 ms; resting HR regime shift returns approximately
4.54 bpm.

## Detection latency callouts

The detection latency findings are conclusions from Project 1, not values
computed at dashboard runtime. Hardcode them as DAX text measures used in
KPI cards:

```dax
HRV detection latency =
"7 days late"

Resting HR detection outcome =
"Never detected"
```

For richer formatting, use Power BI's text card visuals with these as labels,
or compose into a single measure that returns a multi-line description.

## Why DAX is minimal here

The dbt mart pre-computes all aggregations that DAX would otherwise need to
calculate at query time. This is intentional design: keeping aggregation
logic in dbt means it is version-controlled, testable, and consistent across
any BI tool that reads from the mart. Power BI and Metabase both render the
same data because both consume the same materialized table.

Implementations that move aggregation logic into the BI tool layer
(per-regime means computed in DAX, regime boundaries defined in M-language
parameters, etc.) are technically possible but reduce portability across tools
and create a second source of truth for the regime statistics.
