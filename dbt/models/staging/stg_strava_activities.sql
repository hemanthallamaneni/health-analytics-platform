WITH raw AS (
    SELECT
        id,
        name,
        sport_type,
        start_date,
        elapsed_time,
        distance,
        raw_json,
        loaded_at
    FROM {{ source('raw_strava', 'raw_activities') }}
),

parsed AS (
    SELECT
        id,
        name,
        sport_type,
        start_date::TIMESTAMP                               AS start_date,
        start_date::DATE                                    AS activity_date,
        elapsed_time::INTEGER                               AS elapsed_time,
        PARSE_JSON(raw_json):moving_time::INTEGER           AS moving_time,
        distance::FLOAT                                     AS distance_meters,
        PARSE_JSON(raw_json):total_elevation_gain::FLOAT    AS elevation_gain,
        PARSE_JSON(raw_json):average_speed::FLOAT           AS average_speed,
        PARSE_JSON(raw_json):average_watts::FLOAT           AS average_watts,
        PARSE_JSON(raw_json):weighted_average_watts::FLOAT  AS weighted_avg_watts,
        PARSE_JSON(raw_json):kilojoules::FLOAT              AS kilojoules,
        PARSE_JSON(raw_json):elev_high::FLOAT               AS elev_high,
        PARSE_JSON(raw_json):elev_low::FLOAT                AS elev_low,
        PARSE_JSON(raw_json):has_heartrate::BOOLEAN         AS has_heartrate,
        PARSE_JSON(raw_json):device_name::STRING            AS device_name,
        PARSE_JSON(raw_json):start_date_local::TIMESTAMP    AS start_date_local,
        loaded_at
    FROM raw
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY loaded_at DESC) = 1
)
SELECT * FROM parsed