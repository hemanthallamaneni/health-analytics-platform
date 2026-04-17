# Power BI Equivalent — Design Notes

This document covers visual design decisions specific to Power BI Desktop
that differ from the Metabase implementation, and notes which features are
supported in each tool.

## Dashboard structure

Both implementations use the same six-panel structure:

1. Detection latency callout (text/KPI card)
2. Regime summary table
3. HRV daily time series with regime baselines
4. Resting heart rate daily time series with regime baselines
5. Sleep efficiency daily trend (single regime)
6. Readiness score daily trend (single regime)

Layout suggestion for Power BI: top row spans the page width with the callout
and summary table side-by-side. The four time-series panels arrange in a 2x2
grid below. The order intentionally puts the "why this matters" callout first
and the negative-control signals (sleep, readiness) last, mirroring the
Metabase layout.

## Visual features supported in Power BI but not Metabase

The following enhancements are straightforward in Power BI Desktop but were
not feasible in Metabase's chart engine:

**Shaded SD bands.** Power BI's line chart supports an "Error bars" feature
that renders a shaded region between upper and lower bounds. Configure error
bars on the daily HRV line using `Regime HRV upper band` and
`Regime HRV lower band` measures. Repeat for resting HR. The visual result is
a shaded region around the regime mean line that visually communicates the
range of normal within-regime variation.

**Vertical reference lines at change-points.** Power BI line charts support
constant-line annotations on the x-axis. Add a vertical line at
`2025-12-27` on the HRV chart labeled "PELT-detected regime shift" and
another at `2026-02-27` on the resting HR chart. Metabase does not support
this; we relied on the color split at the regime boundary to communicate the
change-point location.

**Per-regime background shading.** Power BI's line chart supports
background regions defined by date ranges. Optionally shade the "baseline
period" portion of the HRV chart in one tint and the "post-travel period"
portion in another, providing additional visual reinforcement of the regime
structure.

**Cross-filter interactivity.** Power BI dashboards support click-through
filtering by default — clicking a row in the regime summary table filters
the time-series visuals to show only that regime. Metabase requires explicit
dashboard filter widgets for the same behavior.

## Visual features supported in Metabase but limited in Power BI

**Native SQL passthrough at the chart level.** Metabase questions are
backed by SQL queries that are part of the question definition. In Power BI,
SQL is configured at the data source level and applies to the whole report.
For a dashboard with six visuals reading variations of the same query,
Metabase's per-visual SQL is more flexible; Power BI typically requires either
loading the full mart and shaping in Power Query, or using multiple data
source queries.

**Public sharing without licensing concerns.** Metabase Open Source can
expose dashboards via public URLs (with the "Public Sharing" admin feature
enabled). Power BI's equivalent (Publish to Web) requires a Power BI Pro
license and is restricted in many enterprise environments.

## Color and theming

Use a consistent color scheme across panels:

- Regime 1 (baseline period for HRV, pre-training period for resting HR):
  cool tone, e.g. `#5B8DEF` (blue)
- Regime 2 (post-travel period for HRV, marathon training period for
  resting HR): warm tone, e.g. `#E8804B` (orange)
- Single-regime signals (sleep, readiness): neutral accent color
- Mean lines: same color as the corresponding raw line, dashed style,
  thicker stroke

Power BI's theme editor lets you save these as a named theme JSON for reuse
across reports.

## Refresh and deployment

For a portfolio artifact, the Power BI report can be:

1. Saved as a `.pbix` file and committed to the repository
2. Published to Power BI Service for a hosted version (requires a Pro license
   for sharing; free tier supports personal workspace only)
3. Exported to PDF via File → Export → Export to PDF for a static artifact
   equivalent to the Metabase PDF export at
   `analyses/regime_dashboard/screenshots/regime_dashboard.pdf`

The Metabase implementation is the live deliverable for this portfolio. The
Power BI specification in this directory exists for reviewers who want to see
how the same analytical content would be implemented in the more
enterprise-prevalent BI tool, and for the user's own future implementation
when Windows access is available.

## Implementation status

This Power BI specification is documentation only. No `.pbix` file is
committed to the repository at this time. Implementation requires Power BI
Desktop, which is not available on the user's current Linux development
machine. The specification is designed to be sufficient for a Power BI
practitioner to reproduce the dashboard in approximately 1–2 hours given
Snowflake access.
