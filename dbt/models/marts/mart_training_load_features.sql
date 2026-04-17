{{
    config(
        materialized='table',
        schema='mart_health'
    )
}}

-- Daily training-load features with rolling windows for ACWR computation.
-- Built on mart_regime_labels which already contains daily-aggregated Strava data
-- joined to regime annotations.
--
-- Feature windows:
--   7-day acute window  (sports-science standard for short-term load)
--   14-day pre-transition window (analytical window for Project 3)
--   28-day chronic window (sports-science standard for chronic baseline)

WITH base AS (
    SELECT
        activity_date,
        regime_hrv,
        regime_resting_hr,
        average_hrv,
        lowest_heart_rate,
        readiness_score,
        COALESCE(workout_count, 0) AS workout_count,
        COALESCE(total_distance_meters, 0) AS distance_m,
        COALESCE(total_elapsed_time, 0) AS elapsed_sec,
        COALESCE(total_kilojoules, 0) AS kilojoules,
        CASE WHEN COALESCE(workout_count, 0) > 0 THEN 1 ELSE 0 END AS is_workout_day
    FROM {{ ref('mart_regime_labels') }}
),

rolling_features AS (
    SELECT
        activity_date,
        regime_hrv,
        regime_resting_hr,
        average_hrv,
        lowest_heart_rate,
        readiness_score,
        workout_count,
        distance_m,
        elapsed_sec,
        kilojoules,
        is_workout_day,

        -- 7-day acute window (trailing, inclusive of current day)
        SUM(distance_m) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS distance_7d,
        SUM(elapsed_sec) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS elapsed_7d,
        SUM(kilojoules) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS kj_7d,
        SUM(is_workout_day) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS workout_days_7d,

        -- 14-day acute window (analytical window of interest)
        SUM(distance_m) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS distance_14d,
        SUM(elapsed_sec) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS elapsed_14d,
        SUM(kilojoules) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS kj_14d,
        SUM(is_workout_day) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS workout_days_14d,

        -- 28-day chronic window
        SUM(distance_m) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 27 PRECEDING AND CURRENT ROW
        ) AS distance_28d,
        SUM(elapsed_sec) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 27 PRECEDING AND CURRENT ROW
        ) AS elapsed_28d,
        SUM(is_workout_day) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 27 PRECEDING AND CURRENT ROW
        ) AS workout_days_28d,

        -- Row count for window completeness check
        COUNT(*) OVER (
            ORDER BY activity_date 
            ROWS BETWEEN 27 PRECEDING AND CURRENT ROW
        ) AS rows_in_28d_window
    FROM base
),

with_acwr AS (
    SELECT
        *,
        -- ACWR: 7-day mean / 28-day mean. Null when chronic window incomplete.
        CASE 
            WHEN rows_in_28d_window = 28 AND distance_28d > 0
            THEN (distance_7d / 7.0) / (distance_28d / 28.0)
        END AS acwr_distance,
        CASE 
            WHEN rows_in_28d_window = 28 AND elapsed_28d > 0
            THEN (elapsed_7d / 7.0) / (elapsed_28d / 28.0)
        END AS acwr_elapsed
    FROM rolling_features
)

SELECT * FROM with_acwr
ORDER BY activity_date