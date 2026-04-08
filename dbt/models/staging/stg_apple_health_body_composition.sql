with raw AS (
    SELECT
        id,
        source,
        start_date,
        end_date,
        type as measurement_type,
        unit,
        value,
        raw_json,
        creation
    FROM HEALTH_ANALYTICS.RAW_APPLE_HEALTH.RAW_BODY_COMPOSITION
),

parsed AS (
    SELECT
        id,
        source,
        start_date::TIMESTAMP AS start_time,
        end_date::TIMESTAMP AS end_time,
        value::FLOAT,
        measurement_type,
        unit,
        raw_json,
        creation::TIMESTAMP AS created_at
    FROM raw
)
SELECT * FROM parsed