WITH raw AS (
    SELECT
        id,
        source,
        start_date,
        end_date,
        type AS measurement_type,
        unit,
        value,
        raw_json,
        creation,
        loaded_at
    FROM HEALTH_ANALYTICS.RAW_APPLE_HEALTH.RAW_BODY_COMPOSITION
),
 
parsed AS (
    SELECT
        id,
        source,
        start_date::TIMESTAMP AS start_time,
        end_date::TIMESTAMP AS end_time,
        CASE
            WHEN measurement_type = 'HKQuantityTypeIdentifierBodyFatPercentage'
            THEN value::FLOAT * 100
            ELSE value::FLOAT
        END AS value,
        measurement_type,
        unit,
        raw_json,
        creation::TIMESTAMP AS created_at
    FROM raw
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY loaded_at DESC) = 1
)
 
SELECT * FROM parsed