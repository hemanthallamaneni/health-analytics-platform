-- Per-sample telemetry for analyzable runs only.
--
-- Filters:
--   * Run-type sport (Run, TrailRun, VirtualRun)
--   * Has GPS at activity level (latitude/longitude present in some sample)
--   * Has HR at activity level (from Strava or Apple Watch backfill)
--   * Activity duration > 5 minutes (exclude false starts)
--   * is_moving = TRUE (drop pre-start and post-stop stationary samples)
--
-- Each row also carries the activity-level metadata needed for downstream
-- weather joins and per-run summarization.

WITH streams AS (
    SELECT * FROM {{ ref('stg_strava_streams_with_hr') }}
),

activities AS (
    SELECT
        id           AS activity_id,
        name         AS activity_name,
        sport_type,
        start_date,
        elapsed_time,
        distance_meters,
        device_name,
        start_date_local
    FROM {{ ref('stg_strava_activities') }}
    WHERE sport_type IN ('Run', 'TrailRun', 'VirtualRun')
      AND elapsed_time >= 300
      AND distance_meters > 0
),

-- Activity-level coverage check: at least one HR sample and at least one
-- GPS sample over the full activity (before is_moving filter).
coverage AS (
    SELECT
        activity_id,
        COUNT_IF(heartrate IS NOT NULL)            AS n_hr_samples,
        COUNT_IF(latitude IS NOT NULL)             AS n_gps_samples,
        MIN(CASE WHEN latitude IS NOT NULL THEN latitude END)   AS first_lat,
        MIN(CASE WHEN longitude IS NOT NULL THEN longitude END) AS first_lon,
        MAX(hr_source)                             AS hr_source
    FROM streams
    GROUP BY activity_id
),

eligible_activities AS (
    SELECT
        a.activity_id,
        a.activity_name,
        a.sport_type,
        a.start_date,
        a.start_date_local,
        a.start_date_local::DATE AS local_date,
        a.elapsed_time,
        a.distance_meters,
        a.device_name,
        c.first_lat,
        c.first_lon,
        c.hr_source,
        c.n_hr_samples,
        c.n_gps_samples
    FROM activities a
    INNER JOIN coverage c ON a.activity_id = c.activity_id
    WHERE c.n_hr_samples  > 0
      AND c.n_gps_samples > 0
)

SELECT
    e.activity_id,
    e.activity_name,
    e.sport_type,
    e.start_date,
    e.start_date_local,
    e.local_date,
    e.elapsed_time,
    e.distance_meters,
    e.device_name,
    e.first_lat,
    e.first_lon,
    e.hr_source,
    e.n_hr_samples,
    e.n_gps_samples,
    s.sample_index,
    s.time_offset_sec,
    DATEADD('second', s.time_offset_sec, e.start_date) AS sample_ts_utc,
    s.heartrate,
    s.cadence_spm,
    s.velocity_mps,
    s.altitude_m,
    s.grade_pct,
    s.distance_m,
    s.latitude,
    s.longitude,
    s.backfill_gap_sec
FROM eligible_activities e
INNER JOIN streams s ON s.activity_id = e.activity_id
WHERE s.is_moving = TRUE
