with raw AS (
    SELECT
        id,
        source,
        start_date,
        end_date,
        heart_rate,
        unit,
        raw_json,
        creation
    FROM HEALTH_ANALYTICS.RAW_APPLE_HEALTH.RAW_HEART_RATE
),

parsed AS (
    SELECT
        id,
        source,
        start_date::TIMESTAMP AS start_time,
        end_date::TIMESTAMP AS end_time,
        heart_rate::FLOAT,
        unit,
        raw_json,
        creation::TIMESTAMP AS created_at
    FROM raw
)
SELECT * FROM parsed