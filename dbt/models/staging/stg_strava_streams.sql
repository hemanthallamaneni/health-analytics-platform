-- Long-format Strava activity streams.
-- One row per (activity_id, sample_index).
-- Wide-to-long: each stream type becomes a column, joined on sample_index.
-- Time stream is the authoritative time axis (Strava's series_type=time
-- request was silently ignored by the API; we use the time array directly).

WITH raw AS (
    SELECT
        activity_id,
        stream_type,
        stream_json,
        original_size,
        loaded_at
    FROM {{ source('raw_strava', 'raw_streams') }}
    QUALIFY ROW_NUMBER() OVER (PARTITION BY activity_id, stream_type ORDER BY loaded_at DESC) = 1
),

flattened AS (
    SELECT
        r.activity_id,
        r.stream_type,
        f.index           AS sample_index,
        f.value           AS sample_value
    FROM raw r,
    LATERAL FLATTEN(input => PARSE_JSON(r.stream_json)) f
),

pivoted AS (
    SELECT
        activity_id,
        sample_index,
        MAX(CASE WHEN stream_type = 'time'            THEN sample_value::INTEGER END) AS time_offset_sec,
        MAX(CASE WHEN stream_type = 'heartrate'       THEN sample_value::INTEGER END) AS heartrate,
        MAX(CASE WHEN stream_type = 'cadence'         THEN sample_value::INTEGER END) AS cadence_spm,
        MAX(CASE WHEN stream_type = 'velocity_smooth' THEN sample_value::FLOAT   END) AS velocity_mps,
        MAX(CASE WHEN stream_type = 'altitude'        THEN sample_value::FLOAT   END) AS altitude_m,
        MAX(CASE WHEN stream_type = 'grade_smooth'    THEN sample_value::FLOAT   END) AS grade_pct,
        MAX(CASE WHEN stream_type = 'distance'        THEN sample_value::FLOAT   END) AS distance_m,
        MAX(CASE WHEN stream_type = 'moving'          THEN sample_value::BOOLEAN END) AS is_moving,
        MAX(CASE WHEN stream_type = 'latlng'          THEN sample_value[0]::FLOAT END) AS latitude,
        MAX(CASE WHEN stream_type = 'latlng'          THEN sample_value[1]::FLOAT END) AS longitude
    FROM flattened
    GROUP BY activity_id, sample_index
)

SELECT * FROM pivoted
