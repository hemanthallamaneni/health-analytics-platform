WITH raw AS (
    SELECT
        id,
        day,
        raw_json,
        loaded_at
    FROM {{ source('raw_oura', 'raw_readiness') }}
),

parsed AS (
    SELECT
        id,
        day::DATE                                                              AS readiness_date,
        PARSE_JSON(raw_json):score::INTEGER                                    AS readiness_score,
        PARSE_JSON(raw_json):temperature_deviation::FLOAT                      AS temperature_deviation,
        PARSE_JSON(raw_json):temperature_trend_deviation::FLOAT                AS temperature_trend_deviation,
        PARSE_JSON(raw_json):contributors:activity_balance::INTEGER            AS contrib_activity_balance,
        PARSE_JSON(raw_json):contributors:body_temperature::INTEGER            AS contrib_body_temperature,
        PARSE_JSON(raw_json):contributors:hrv_balance::INTEGER                 AS contrib_hrv_balance,
        PARSE_JSON(raw_json):contributors:previous_day_activity::INTEGER       AS contrib_previous_day_activity,
        PARSE_JSON(raw_json):contributors:previous_night::INTEGER              AS contrib_previous_night,
        PARSE_JSON(raw_json):contributors:recovery_index::INTEGER              AS contrib_recovery_index,
        PARSE_JSON(raw_json):contributors:resting_heart_rate::INTEGER          AS contrib_resting_heart_rate,
        PARSE_JSON(raw_json):contributors:sleep_balance::INTEGER               AS contrib_sleep_balance,
        PARSE_JSON(raw_json):timestamp::TIMESTAMP                              AS readiness_timestamp,
        loaded_at
    FROM raw
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY loaded_at DESC) = 1
)
SELECT * FROM parsed
