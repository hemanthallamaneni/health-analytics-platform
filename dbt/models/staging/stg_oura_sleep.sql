WITH raw AS (
    SELECT
        id,
        day,
        raw_json,
        loaded_at
    FROM HEALTH_ANALYTICS.RAW_OURA.RAW_SLEEP
),

parsed AS (
    SELECT
        id,
        day::DATE                                                   AS sleep_date,
        raw_json:type::STRING                                       AS sleep_type,
        raw_json:readiness:score::INTEGER                           AS readiness_score,
        raw_json:readiness:contributors:activity_balance::INTEGER   AS activity_balance,
        raw_json:readiness:contributors:hrv_balance::INTEGER        AS hrv_balance,
        raw_json:readiness:contributors:resting_heart_rate::INTEGER AS resting_heart_rate_score,
        raw_json:readiness:contributors:sleep_balance::INTEGER      AS sleep_balance,
        raw_json:readiness:contributors:body_temperature::INTEGER   AS body_temperature_score,
        raw_json:readiness:temperature_deviation::FLOAT             AS temperature_deviation,
        raw_json:efficiency::INTEGER                                AS efficiency,
        raw_json:average_hrv::INTEGER                               AS average_hrv,
        raw_json:average_heart_rate::FLOAT                          AS average_heart_rate,
        raw_json:lowest_heart_rate::INTEGER                         AS lowest_heart_rate,
        raw_json:average_breath::FLOAT                              AS average_breath,
        raw_json:total_sleep_duration::INTEGER                      AS total_sleep_duration,
        raw_json:deep_sleep_duration::INTEGER                       AS deep_sleep_duration,
        raw_json:rem_sleep_duration::INTEGER                        AS rem_sleep_duration,
        raw_json:light_sleep_duration::INTEGER                      AS light_sleep_duration,
        raw_json:awake_time::INTEGER                                AS awake_time,
        raw_json:latency::INTEGER                                   AS sleep_latency,
        raw_json:bedtime_start::TIMESTAMP                           AS bedtime_start,
        raw_json:bedtime_end::TIMESTAMP                             AS bedtime_end,
        raw_json:sleep_phase_5_min::STRING                          AS sleep_phases,
        loaded_at
    FROM raw
)

SELECT * FROM parsed