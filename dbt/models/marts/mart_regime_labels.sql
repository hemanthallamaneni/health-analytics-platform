{{
    config(materialized='table')
}}

-- Regime boundaries hardcoded from PELT change-point detection (Project 1).
-- Do not modify without re-running analyses/physiological_nonstationarity/analysis.py.
--
-- HRV:        Regime 1 = 2025-11-25 → 2025-12-27 | Regime 2 = 2025-12-28 → present
-- Resting HR: Regime 1 = 2025-11-25 → 2026-02-27 | Regime 2 = 2026-02-28 → present
-- Sleep Efficiency / Readiness Score: single regime (no change-point detected)

WITH base AS (
    SELECT
        activity_date,
        average_hrv,
        lowest_heart_rate,
        sleep_efficiency,
        readiness_score,
        hrv_balance,
        total_sleep_duration,
        deep_sleep_duration,
        rem_sleep_duration,
        light_sleep_duration,
        bedtime_start,
        bedtime_end,
        workout_count,
        total_distance_meters,
        total_kilojoules,
        total_elapsed_time,
        sport_types
    FROM {{ ref('daily_health_summary') }}
),

labeled AS (
    SELECT
        *,
        CASE
            WHEN activity_date <= '2025-12-27' THEN 'Regime 1'
            ELSE                                     'Regime 2'
        END AS regime_hrv,
        CASE
            WHEN activity_date <= '2026-02-27' THEN 'Regime 1'
            ELSE                                     'Regime 2'
        END AS regime_resting_hr
    FROM base
),

regime_hrv_stats AS (
    SELECT
        regime_hrv,
        AVG(average_hrv)    AS regime_hrv_mean,
        STDDEV(average_hrv) AS regime_hrv_sd,
        MIN(average_hrv)    AS regime_hrv_min,
        MAX(average_hrv)    AS regime_hrv_max
    FROM labeled
    GROUP BY 1
),

regime_rhr_stats AS (
    SELECT
        regime_resting_hr,
        AVG(lowest_heart_rate)    AS regime_rhr_mean,
        STDDEV(lowest_heart_rate) AS regime_rhr_sd,
        MIN(lowest_heart_rate)    AS regime_rhr_min,
        MAX(lowest_heart_rate)    AS regime_rhr_max
    FROM labeled
    GROUP BY 1
),

-- Single-regime signals: compute global stats, label as Regime 1 for consistency
global_sleep_stats AS (
    SELECT
        AVG(sleep_efficiency)    AS regime_sleep_mean,
        STDDEV(sleep_efficiency) AS regime_sleep_sd,
        MIN(sleep_efficiency)    AS regime_sleep_min,
        MAX(sleep_efficiency)    AS regime_sleep_max
    FROM labeled
),

global_readiness_stats AS (
    SELECT
        AVG(readiness_score)    AS regime_readiness_mean,
        STDDEV(readiness_score) AS regime_readiness_sd,
        MIN(readiness_score)    AS regime_readiness_min,
        MAX(readiness_score)    AS regime_readiness_max
    FROM labeled
)

SELECT
    l.activity_date,
    l.average_hrv,
    l.lowest_heart_rate,
    l.sleep_efficiency,
    l.readiness_score,
    l.hrv_balance,
    l.total_sleep_duration,
    l.deep_sleep_duration,
    l.rem_sleep_duration,
    l.light_sleep_duration,
    l.bedtime_start,
    l.bedtime_end,
    l.workout_count,
    l.total_distance_meters,
    l.total_kilojoules,
    l.total_elapsed_time,
    l.sport_types,

    -- Regime labels
    l.regime_hrv,
    l.regime_resting_hr,

    -- HRV within-regime stats (for time-series bands)
    h.regime_hrv_mean,
    h.regime_hrv_sd,
    h.regime_hrv_mean + h.regime_hrv_sd AS regime_hrv_upper,
    h.regime_hrv_mean - h.regime_hrv_sd AS regime_hrv_lower,
    h.regime_hrv_min,
    h.regime_hrv_max,

    -- Resting HR within-regime stats
    r.regime_rhr_mean,
    r.regime_rhr_sd,
    r.regime_rhr_mean + r.regime_rhr_sd AS regime_rhr_upper,
    r.regime_rhr_mean - r.regime_rhr_sd AS regime_rhr_lower,
    r.regime_rhr_min,
    r.regime_rhr_max,

    -- Sleep efficiency global stats
    sl.regime_sleep_mean,
    sl.regime_sleep_sd,
    sl.regime_sleep_mean + sl.regime_sleep_sd AS regime_sleep_upper,
    sl.regime_sleep_mean - sl.regime_sleep_sd AS regime_sleep_lower,
    sl.regime_sleep_min,
    sl.regime_sleep_max,

    -- Readiness score global stats
    rd.regime_readiness_mean,
    rd.regime_readiness_sd,
    rd.regime_readiness_mean + rd.regime_readiness_sd AS regime_readiness_upper,
    rd.regime_readiness_mean - rd.regime_readiness_sd AS regime_readiness_lower,
    rd.regime_readiness_min,
    rd.regime_readiness_max

FROM labeled l
LEFT JOIN regime_hrv_stats    h  ON l.regime_hrv        = h.regime_hrv
LEFT JOIN regime_rhr_stats    r  ON l.regime_resting_hr = r.regime_resting_hr
CROSS JOIN global_sleep_stats sl
CROSS JOIN global_readiness_stats rd
ORDER BY l.activity_date
