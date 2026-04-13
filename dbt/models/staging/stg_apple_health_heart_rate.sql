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
    FROM {{ source('raw_apple_health', 'raw_heart_rate') }}
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
)
SELECT * FROM parsed