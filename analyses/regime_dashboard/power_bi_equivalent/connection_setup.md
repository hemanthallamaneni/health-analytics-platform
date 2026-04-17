# Power BI Equivalent — Connection Setup

This document specifies how to reproduce the Project 2 dashboard in Power BI
Desktop, given access to the same Snowflake backend. The implementation here
is a portability reference rather than the primary deliverable; the live
dashboard runs on self-hosted Metabase (see `infra/metabase/`).

## Prerequisites

- Power BI Desktop (Windows or macOS)
- Snowflake account credentials with `USAGE` on `HEALTH_ANALYTICS.MART_HEALTH`
  and `SELECT` on `MART_REGIME_LABELS`
- Snowflake account identifier in the form `<account>.<region>` (e.g.
  `vtxiyyq-we09601`)

## Snowflake connector configuration

In Power BI Desktop:

1. Home → Get Data → More → Database → Snowflake
2. Server: `<account>.snowflakecomputing.com` (Power BI requires the FQDN form,
   unlike Metabase or dbt)
3. Warehouse: `COMPUTE_WH`
4. Data Connectivity mode: Import (recommended for a single-user portfolio
   dashboard; switch to DirectQuery only if working with very large fact tables)
5. Click OK
6. Authentication: select Snowflake account, enter username and password
   (or configure key pair via Power BI's connector settings if available
   in your version)

## Source query

Rather than importing the entire mart and shaping in Power Query, point
Power BI directly at the regime mart with a native query:

```sql
SELECT
    ACTIVITY_DATE,
    AVERAGE_HRV,
    LOWEST_HEART_RATE,
    SLEEP_EFFICIENCY,
    READINESS_SCORE,
    REGIME_HRV,
    REGIME_RESTING_HR,
    REGIME_HRV_MEAN,
    REGIME_HRV_SD,
    REGIME_HRV_UPPER,
    REGIME_HRV_LOWER,
    REGIME_RHR_MEAN,
    REGIME_RHR_SD,
    REGIME_RHR_UPPER,
    REGIME_RHR_LOWER,
    REGIME_SLEEP_MEAN,
    REGIME_READINESS_MEAN
FROM MART_HEALTH.MART_REGIME_LABELS
ORDER BY ACTIVITY_DATE
```

Save the query as a single table named `RegimeLabels`. Refresh schedule
should match the dbt run cadence (typically daily).

## Authentication note

The Snowflake password deprecation (enforcement Aug–Oct 2026) affects this
connection. For production deployments, use Snowflake key pair authentication
instead of password. Power BI Desktop's Snowflake connector supports key pair
auth in recent versions; the private key file lives outside the repository at
`~/.config/snowflake/keys/snowflake_key.p8` per the project's auth conventions.

## Schema notes

The mart was designed for BI consumption: per-regime statistics are
pre-computed in dbt, so all aggregation logic lives in the data layer rather
than in DAX. This minimizes DAX complexity in the report and means both the
Metabase and Power BI implementations consume the same materialized view of
the data.

If the mart schema changes, both implementations need to be updated. The
authoritative source is `dbt/models/marts/mart_regime_labels.sql`.
