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
        day::DATE                                                            AS sleep_date,
        PARSE_JSON(raw_json):type::STRING                                    AS sleep_type,
        PARSE_JSON(raw_json):readiness:score::INTEGER                        AS readiness_score,
        PARSE_JSON(raw_json):readiness:contributors:activity_balance::INTEGER AS activity_balance,
        PARSE_JSON(raw_json):readiness:contributors:hrv_balance::INTEGER     AS hrv_balance,
        PARSE_JSON(raw_json):readiness:contributors:resting_heart_rate::INTEGER AS resting_heart_rate_score,
        PARSE_JSON(raw_json):readiness:contributors:sleep_balance::INTEGER   AS sleep_balance,
        PARSE_JSON(raw_json):readiness:contributors:body_temperature::INTEGER AS body_temperature_score,
        PARSE_JSON(raw_json):readiness:temperature_deviation::FLOAT          AS temperature_deviation,
        PARSE_JSON(raw_json):efficiency::INTEGER                             AS efficiency,
        PARSE_JSON(raw_json):average_hrv::INTEGER                            AS average_hrv,
        PARSE_JSON(raw_json):average_heart_rate::FLOAT                       AS average_heart_rate,
        PARSE_JSON(raw_json):lowest_heart_rate::INTEGER                      AS lowest_heart_rate,
        PARSE_JSON(raw_json):average_breath::FLOAT                           AS average_breath,
        PARSE_JSON(raw_json):total_sleep_duration::INTEGER                   AS total_sleep_duration,
        PARSE_JSON(raw_json):deep_sleep_duration::INTEGER                    AS deep_sleep_duration,
        PARSE_JSON(raw_json):rem_sleep_duration::INTEGER                     AS rem_sleep_duration,
        PARSE_JSON(raw_json):light_sleep_duration::INTEGER                   AS light_sleep_duration,
        PARSE_JSON(raw_json):awake_time::INTEGER                             AS awake_time,
        PARSE_JSON(raw_json):latency::INTEGER                                AS sleep_latency,
        PARSE_JSON(raw_json):bedtime_start::TIMESTAMP                        AS bedtime_start,
        PARSE_JSON(raw_json):bedtime_end::TIMESTAMP                          AS bedtime_end,
        PARSE_JSON(raw_json):sleep_phase_5_min::STRING                       AS sleep_phases,
        loaded_at
    FROM raw
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY loaded_at DESC) = 1
)

SELECT * FROM parsed