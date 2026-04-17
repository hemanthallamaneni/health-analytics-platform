-- Strava streams enriched with backfilled heart rate from Apple Watch
-- via Apple Health, for activities where Strava-provided HR is missing.
--
-- Backfill strategy: nearest-neighbor join within ±5 seconds.
-- Apple Health timestamps are in Central time (CDT during study window);
-- adding INTERVAL 5 HOUR converts to UTC to align with Strava timestamps.
--
-- Activities with HR present in Strava use Strava values unchanged
-- (hr_source = 'strava'). Activities missing HR get nearest-neighbor
-- Apple Watch values (hr_source = 'apple_watch_backfill').
-- Single source per activity; no mixing within a run.

WITH streams AS (
    SELECT * FROM {{ ref('stg_strava_streams') }}
),

activities AS (
    SELECT id, start_date, has_heartrate
    FROM {{ ref('stg_strava_activities') }}
),

-- Per-activity HR coverage from Strava (count of non-null HR samples)
strava_hr_coverage AS (
    SELECT
        activity_id,
        COUNT(heartrate) AS n_hr_samples
    FROM streams
    GROUP BY activity_id
),

-- Activities that need backfill: zero HR samples in the Strava streams
needs_backfill AS (
    SELECT activity_id
    FROM strava_hr_coverage
    WHERE n_hr_samples = 0
),

-- Apple Watch HR samples in UTC, source-filtered to the watch only.
-- The non-breaking space and curly apostrophe in the source string are
-- the actual exported characters from Apple Health.
apple_watch_hr_utc AS (
    SELECT
        DATEADD('hour', 5, START_DATE) AS sample_ts_utc,
        HEART_RATE                     AS heartrate_aw
    FROM {{ source('raw_apple_health', 'raw_heart_rate') }}
    WHERE SOURCE = 'Hemanth\u2019s Apple\u00a0Watch'
),

-- For each Strava sample in a backfill activity, compute the absolute
-- UTC timestamp from (activity start + time_offset).
backfill_targets AS (
    SELECT
        s.activity_id,
        s.sample_index,
        s.time_offset_sec,
        DATEADD('second', s.time_offset_sec, a.start_date) AS sample_ts_utc
    FROM streams s
    INNER JOIN needs_backfill nb ON s.activity_id = nb.activity_id
    INNER JOIN activities a       ON s.activity_id = a.id
),

-- Nearest-neighbor join: for each backfill target, the Apple Watch HR
-- sample with the smallest absolute time gap, capped at ±5 seconds.
backfilled_hr AS (
    SELECT
        bt.activity_id,
        bt.sample_index,
        aw.heartrate_aw,
        ABS(DATEDIFF('second', bt.sample_ts_utc, aw.sample_ts_utc)) AS gap_sec,
        ROW_NUMBER() OVER (
            PARTITION BY bt.activity_id, bt.sample_index
            ORDER BY ABS(DATEDIFF('second', bt.sample_ts_utc, aw.sample_ts_utc))
        ) AS rn
    FROM backfill_targets bt
    INNER JOIN apple_watch_hr_utc aw
        ON aw.sample_ts_utc BETWEEN DATEADD('second', -5, bt.sample_ts_utc)
                                 AND DATEADD('second',  5, bt.sample_ts_utc)
),

best_backfill AS (
    SELECT activity_id, sample_index, heartrate_aw, gap_sec
    FROM backfilled_hr
    WHERE rn = 1
),

enriched AS (
    SELECT
        s.activity_id,
        s.sample_index,
        s.time_offset_sec,
        COALESCE(s.heartrate, bb.heartrate_aw) AS heartrate,
        CASE
            WHEN s.heartrate IS NOT NULL                   THEN 'strava'
            WHEN bb.heartrate_aw IS NOT NULL               THEN 'apple_watch_backfill'
            ELSE NULL
        END                                    AS hr_source,
        bb.gap_sec                             AS backfill_gap_sec,
        s.cadence_spm,
        s.velocity_mps,
        s.altitude_m,
        s.grade_pct,
        s.distance_m,
        s.is_moving,
        s.latitude,
        s.longitude
    FROM streams s
    LEFT JOIN best_backfill bb
        ON s.activity_id = bb.activity_id
       AND s.sample_index = bb.sample_index
)

SELECT * FROM enriched
