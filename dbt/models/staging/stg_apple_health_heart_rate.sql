with raw AS (
    SELECT
        id,
        source,
        start_date,
        end_date,
        heart_rate,
        unit,
        raw_json,
        creation,
        loaded_at
    FROM HEALTH_ANALYTICS.RAW_APPLE_HEALTH.RAW_HEART_RATE
),

parsed AS (
    SELECT
        id,
        source,
        start_date::TIMESTAMP AS start_time,
        end_date::TIMESTAMP AS end_time,
        heart_rate::FLOAT AS heart_rate,
        unit,
        raw_json,
        creation::TIMESTAMP AS created_at
    FROM raw
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY loaded_at DESC) = 1
)
SELECT * FROM parsed