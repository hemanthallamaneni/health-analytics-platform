WITH sleep AS (
    SELECT
        sleep_date AS activity_date,
        sleep_type,
        readiness_score,
        hrv_balance,
        average_hrv,
        average_heart_rate,
        lowest_heart_rate,
        total_sleep_duration,
        deep_sleep_duration,
        rem_sleep_duration,
        light_sleep_duration,
        efficiency,
        bedtime_start,
        bedtime_end,
        ROW_NUMBER() OVER (
            PARTITION BY sleep_date
            ORDER BY total_sleep_duration DESC
        ) AS rn
    FROM {{ ref('stg_oura_sleep') }}
    WHERE sleep_type = 'long_sleep'
),

heart_rate AS (
    SELECT
        start_time::DATE AS activity_date,
        AVG(heart_rate)  AS avg_heart_rate,
        MAX(heart_rate)  AS max_heart_rate,
        MIN(heart_rate)  AS min_heart_rate,
        COUNT(*)         AS hr_reading_count
    FROM {{ ref('stg_apple_health_heart_rate') }}
    GROUP BY 1
),

body_comp_raw AS (
    SELECT DISTINCT
        start_time::DATE AS activity_date,
        LAST_VALUE(CASE WHEN measurement_type = 'HKQuantityTypeIdentifierBodyMass'
            THEN value END) IGNORE NULLS OVER (
            PARTITION BY start_time::DATE
            ORDER BY start_time)             AS weight_kg,
        LAST_VALUE(CASE WHEN measurement_type = 'HKQuantityTypeIdentifierBodyFatPercentage'
            THEN value END) IGNORE NULLS OVER (
            PARTITION BY start_time::DATE
            ORDER BY start_time)             AS body_fat_pct,
        LAST_VALUE(CASE WHEN measurement_type = 'HKQuantityTypeIdentifierLeanBodyMass'
            THEN value END) IGNORE NULLS OVER (
            PARTITION BY start_time::DATE
            ORDER BY start_time)             AS lean_body_mass_kg,
        LAST_VALUE(CASE WHEN measurement_type = 'HKQuantityTypeIdentifierBodyMassIndex'
            THEN value END) IGNORE NULLS OVER (
            PARTITION BY start_time::DATE
            ORDER BY start_time)             AS bmi
    FROM {{ ref('stg_apple_health_body_composition') }}
),

sleep_spine AS (
    SELECT activity_date FROM sleep WHERE rn = 1
),

body_comp AS (
    SELECT
        sp.activity_date,
        LAST_VALUE(bc.weight_kg IGNORE NULLS) OVER (
            ORDER BY sp.activity_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS weight_kg,
        LAST_VALUE(bc.body_fat_pct IGNORE NULLS) OVER (
            ORDER BY sp.activity_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS body_fat_pct,
        LAST_VALUE(bc.lean_body_mass_kg IGNORE NULLS) OVER (
            ORDER BY sp.activity_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS lean_body_mass_kg,
        LAST_VALUE(bc.bmi IGNORE NULLS) OVER (
            ORDER BY sp.activity_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS bmi
    FROM sleep_spine sp
    LEFT JOIN body_comp_raw bc ON sp.activity_date = bc.activity_date
),

activities AS (
    SELECT
        activity_date,
        COUNT(*)              AS workout_count,
        SUM(distance_meters)  AS total_distance_meters,
        SUM(kilojoules)       AS total_kilojoules,
        SUM(elapsed_time)     AS total_elapsed_time,
        SUM(elevation_gain)   AS total_elevation_gain,
        LISTAGG(sport_type, ', ') WITHIN GROUP (ORDER BY start_date) AS sport_types
    FROM {{ ref('stg_strava_activities') }}
    GROUP BY 1
)

SELECT
    s.activity_date,
    s.sleep_type,
    s.readiness_score,
    s.hrv_balance,
    s.average_hrv,
    s.average_heart_rate  AS oura_avg_heart_rate,
    s.lowest_heart_rate,
    s.total_sleep_duration,
    s.deep_sleep_duration,
    s.rem_sleep_duration,
    s.light_sleep_duration,
    s.efficiency           AS sleep_efficiency,
    s.bedtime_start,
    s.bedtime_end,
    hr.avg_heart_rate      AS apple_avg_heart_rate,
    hr.max_heart_rate,
    hr.min_heart_rate,
    hr.hr_reading_count,
    bc.weight_kg,
    bc.body_fat_pct,
    bc.lean_body_mass_kg,
    bc.bmi,
    a.workout_count,
    a.total_distance_meters,
    a.total_kilojoules,
    a.total_elapsed_time,
    a.total_elevation_gain,
    a.sport_types
FROM sleep s
LEFT JOIN heart_rate hr ON s.activity_date = hr.activity_date
LEFT JOIN body_comp bc  ON s.activity_date = bc.activity_date
LEFT JOIN activities a  ON s.activity_date = a.activity_date
WHERE s.rn = 1
