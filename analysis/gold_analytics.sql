"-- BTS Gold Layer Analytical Queries" 
-- =============================================================
-- BTS Aviation Delay Intelligence System
-- Gold Layer Analytical Queries
-- Author: Narsing Shiva Kumar
-- Date: September 2026
-- Data: 20,928,599 US domestic flights | Jan 2023-Dec 2025
-- =============================================================
-- All queries follow certified measure definitions
-- from Semantic Layer v1.0 (docs/semantic/)
-- Evidence states: OBSERVED / DERIVED / MODELED / INFERRED
-- =============================================================


-- =============================================================
-- QUERY 1: Fleet-Level Operations Summary
-- Evidence: OBSERVED
-- Purpose: Top-level KPIs across full dataset
-- =============================================================

SELECT
    COUNT(*)                                          AS total_flights,
    SUM(CASE WHEN is_cancelled = 0 THEN 1 ELSE 0 END) AS operated_flights,
    SUM(is_cancelled)                                 AS cancelled_flights,
    SUM(arr_delayed_flag)                             AS delayed_flights,
    ROUND(
        100.0 * SUM(is_cancelled) / COUNT(*), 2
    )                                                 AS cancellation_rate_pct,
    ROUND(
        100.0 * SUM(arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                 AS delay_rate_pct,
    -- Delay rate denominator = operated flights only
    -- Cancelled flights excluded per semantic layer definition
    ROUND(SUM(CASE WHEN arr_delay_mins > 0
              THEN arr_delay_mins ELSE 0 END), 0)     AS total_arrival_delay_mins,
    ROUND(AVG(CASE WHEN arr_delayed_flag = 1
              THEN arr_delay_mins END), 2)            AS avg_delay_delayed_only_mins,
    ROUND(STDDEV(CASE WHEN arr_delayed_flag = 1
                 THEN arr_delay_mins END), 2)         AS stddev_delay_mins
FROM fact_delays;


-- =============================================================
-- QUERY 2: Carrier Performance — Three Dimensions
-- Evidence: OBSERVED
-- Purpose: Compare carriers across delay rate, cancellation
--          rate, and average delay (delayed flights only)
-- Semantic note: "worst carrier" requires metric definition
--               Three metrics = three different answers
-- =============================================================

SELECT
    c.carrier_name,
    COUNT(*)                                           AS total_flights,
    SUM(CASE WHEN f.is_cancelled = 0
             THEN 1 ELSE 0 END)                        AS operated_flights,
    SUM(f.is_cancelled)                                AS cancelled_flights,
    SUM(f.arr_delayed_flag)                            AS delayed_flights,
    ROUND(
        100.0 * SUM(f.is_cancelled) / COUNT(*), 2
    )                                                  AS cancellation_rate_pct,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN f.is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    ROUND(
        AVG(CASE WHEN f.arr_delayed_flag = 1
            THEN f.arr_delay_mins END), 2
    )                                                  AS avg_delay_delayed_only_mins,
    ROUND(
        SUM(CASE WHEN f.arr_delay_mins > 0
            THEN f.arr_delay_mins ELSE 0 END), 0
    )                                                  AS total_delay_mins
FROM fact_delays f
JOIN dim_carrier c ON f.carrier_key = c.carrier_key
WHERE c.record_type = 'SNAPSHOT_V1'
GROUP BY c.carrier_name
ORDER BY delay_rate_pct DESC;


-- =============================================================
-- QUERY 3: Delay Cause Distribution
-- Evidence: OBSERVED (via bridge table)
-- Purpose: Which BTS-reported categories drive delay minutes
-- CRITICAL: Filter by ONE delay_code per aggregation
--           Summing across all codes double-counts per flight
-- =============================================================

SELECT
    b.delay_code,
    d.delay_category,
    d.ioc_pillar,
    d.operational_influence_class,
    COUNT(DISTINCT b.flight_id)        AS affected_flights,
    ROUND(SUM(b.attributed_mins), 0)   AS total_attributed_mins,
    ROUND(AVG(b.attributed_mins), 2)   AS avg_attributed_mins,
    ROUND(AVG(b.attribution_pct), 2)   AS avg_attribution_pct
FROM bridge_flight_delay_reason b
JOIN dim_delay_reason d
    ON b.delay_reason_key = d.delay_reason_key
WHERE d.record_type = 'TYPE1_LOOKUP'
GROUP BY
    b.delay_code,
    d.delay_category,
    d.ioc_pillar,
    d.operational_influence_class
ORDER BY total_attributed_mins DESC;


-- =============================================================
-- QUERY 4: IOC Pillar Summary
-- Evidence: DERIVED (project-defined IOC mapping)
-- Purpose: Aggregate delay exposure by IOC pillar
-- Note: Pillar mapping is project-defined — not BTS or FAA
-- =============================================================

SELECT
    dominant_delay_pillar,
    COUNT(*)                                           AS total_flights,
    SUM(arr_delayed_flag)                              AS delayed_flights,
    ROUND(
        100.0 * SUM(arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    ROUND(SUM(CASE WHEN arr_delay_mins > 0
              THEN arr_delay_mins ELSE 0 END), 0)      AS total_delay_mins,
    ROUND(AVG(CASE WHEN arr_delayed_flag = 1
              THEN arr_delay_mins END), 2)             AS avg_delay_mins
FROM fact_delays
WHERE is_cancelled = 0
GROUP BY dominant_delay_pillar
ORDER BY total_delay_mins DESC;


-- =============================================================
-- QUERY 5: Monthly Seasonal Pattern
-- Evidence: OBSERVED
-- Purpose: Flight volume and delay rate by month
--          across all 3 years combined
-- =============================================================

SELECT
    d.month,
    d.month_name,
    d.season,
    COUNT(*)                                           AS total_flights,
    SUM(CASE WHEN f.is_cancelled = 0
             THEN 1 ELSE 0 END)                        AS operated_flights,
    SUM(f.arr_delayed_flag)                            AS delayed_flights,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN f.is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    ROUND(SUM(CASE WHEN f.arr_delay_mins > 0
              THEN f.arr_delay_mins ELSE 0 END), 0)    AS total_delay_mins
FROM fact_delays f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.record_type = 'STATIC'
GROUP BY d.month, d.month_name, d.season
ORDER BY d.month;


-- =============================================================
-- QUERY 6: Year-over-Year Trend
-- Evidence: OBSERVED
-- Purpose: Compare delay performance across 2023, 2024, 2025
-- =============================================================

SELECT
    d.year,
    COUNT(*)                                           AS total_flights,
    SUM(f.is_cancelled)                                AS cancelled_flights,
    SUM(f.arr_delayed_flag)                            AS delayed_flights,
    ROUND(
        100.0 * SUM(f.is_cancelled) / COUNT(*), 2
    )                                                  AS cancellation_rate_pct,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN f.is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    ROUND(SUM(CASE WHEN f.arr_delay_mins > 0
              THEN f.arr_delay_mins ELSE 0 END), 0)    AS total_delay_mins,
    ROUND(AVG(CASE WHEN f.arr_delayed_flag = 1
              THEN f.arr_delay_mins END), 2)           AS avg_delay_mins
FROM fact_delays f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.record_type = 'STATIC'
GROUP BY d.year
ORDER BY d.year;


-- =============================================================
-- QUERY 7: Top 15 Airports by Delay Exposure
-- Evidence: OBSERVED
-- Purpose: Which origin airports accumulate most delay minutes
-- Note: Uses active relationship (origin role)
-- =============================================================

SELECT
    a.airport_code,
    a.city,
    a.state,
    COUNT(*)                                           AS total_flights,
    SUM(f.arr_delayed_flag)                            AS delayed_flights,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN f.is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    ROUND(SUM(CASE WHEN f.arr_delay_mins > 0
              THEN f.arr_delay_mins ELSE 0 END), 0)    AS total_delay_mins,
    SUM(f.is_cancelled)                                AS cancelled_flights
FROM fact_delays f
JOIN dim_airport a ON f.origin_airport_key = a.airport_key
WHERE a.record_type = 'SNAPSHOT_V1'
GROUP BY a.airport_code, a.city, a.state
ORDER BY total_delay_mins DESC
LIMIT 15;


-- =============================================================
-- QUERY 8: Late Aircraft Propagation Signal
-- Evidence: OBSERVED (reporting) / INFERRED (propagation)
-- Purpose: Identify flights with late aircraft delay
--          as possible propagation indicator
-- Note: Sequence observed — causation NOT proven
-- =============================================================

SELECT
    c.carrier_name,
    COUNT(*)                                           AS total_flights,
    SUM(CASE WHEN f.late_aircraft_delay_mins > 0
             THEN 1 ELSE 0 END)                        AS late_aircraft_flights,
    ROUND(
        100.0 * SUM(CASE WHEN f.late_aircraft_delay_mins > 0
                    THEN 1 ELSE 0 END) / COUNT(*), 2
    )                                                  AS late_aircraft_rate_pct,
    ROUND(
        AVG(CASE WHEN f.late_aircraft_delay_mins > 0
            THEN f.late_aircraft_delay_mins END), 2
    )                                                  AS avg_late_aircraft_mins,
    ROUND(
        SUM(CASE WHEN f.late_aircraft_delay_mins > 0
            THEN f.late_aircraft_delay_mins ELSE 0 END), 0
    )                                                  AS total_late_aircraft_mins
    -- INFERRED: late_aircraft_delay_mins is a possible
    -- propagation indicator. BTS does not prove causation.
FROM fact_delays f
JOIN dim_carrier c ON f.carrier_key = c.carrier_key
WHERE c.record_type = 'SNAPSHOT_V1'
GROUP BY c.carrier_name
ORDER BY late_aircraft_rate_pct DESC;


-- =============================================================
-- QUERY 9: Modeled Cost Exposure by Carrier
-- Evidence: MODELED
-- Source: Ferguson et al. FAA/NEXTOR 2010 — $45/min
-- MANDATORY: Label as modeled estimate in all outputs
--            Not actual airline financial loss
-- =============================================================

SELECT
    c.carrier_name,
    COUNT(*)                                           AS total_flights,
    ROUND(SUM(CASE WHEN f.arr_delay_mins > 0
              THEN f.arr_delay_mins ELSE 0 END), 0)    AS total_delay_mins,
    ROUND(SUM(mc.estimated_delay_cost), 2)             AS modeled_cost_exposure_usd
    -- MODELED: arr_delay_mins * $45/min
    -- Not actual airline cost
FROM fact_delays f
JOIN dim_carrier c ON f.carrier_key = c.carrier_key
JOIN model_delay_cost mc ON f.flight_id = mc.flight_id
WHERE c.record_type = 'SNAPSHOT_V1'
GROUP BY c.carrier_name
ORDER BY modeled_cost_exposure_usd DESC;


-- =============================================================
-- QUERY 10: Holiday Travel Window Analysis
-- Evidence: OBSERVED (flights) / DERIVED (window definition)
-- Purpose: Compare delay rates during holiday windows
--          vs non-holiday periods
-- Note: holiday_travel_window is approximate — not exact
--       US federal holidays
-- =============================================================

SELECT
    COALESCE(d.holiday_travel_window, 'Non-Holiday')  AS period,
    COUNT(*)                                           AS total_flights,
    SUM(f.arr_delayed_flag)                            AS delayed_flights,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN f.is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    SUM(f.is_cancelled)                                AS cancelled_flights,
    ROUND(
        100.0 * SUM(f.is_cancelled) / COUNT(*), 2
    )                                                  AS cancellation_rate_pct
FROM fact_delays f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.record_type = 'STATIC'
GROUP BY COALESCE(d.holiday_travel_window, 'Non-Holiday')
ORDER BY delay_rate_pct DESC;


-- =============================================================
-- QUERY 11: Weekend vs Weekday Performance
-- Evidence: OBSERVED (flights) / DERIVED (is_weekend)
-- Purpose: Compare operational patterns on weekends vs weekdays
-- Note: day_of_week encoding — 1=Sunday, 7=Saturday
--       is_weekend = day_of_week IN (1,7)
-- =============================================================

SELECT
    CASE WHEN d.is_weekend THEN 'Weekend'
         ELSE 'Weekday' END                            AS day_type,
    COUNT(*)                                           AS total_flights,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN f.is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    ROUND(
        100.0 * SUM(f.is_cancelled) / COUNT(*), 2
    )                                                  AS cancellation_rate_pct,
    ROUND(AVG(CASE WHEN f.arr_delayed_flag = 1
              THEN f.arr_delay_mins END), 2)           AS avg_delay_mins
FROM fact_delays f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.record_type = 'STATIC'
GROUP BY CASE WHEN d.is_weekend THEN 'Weekend'
              ELSE 'Weekday' END
ORDER BY delay_rate_pct DESC;


-- =============================================================
-- QUERY 12: Route-Level Delay Exposure (Top 20)
-- Evidence: OBSERVED
-- Purpose: Identify highest-delay routes
-- Note: Route = origin + destination pair
--       Not a standalone dimension in v1
-- =============================================================

SELECT
    o.airport_code                                     AS origin,
    d.airport_code                                     AS destination,
    COUNT(*)                                           AS total_flights,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag)
        / NULLIF(SUM(CASE WHEN f.is_cancelled = 0
                     THEN 1 ELSE 0 END), 0), 2
    )                                                  AS delay_rate_pct,
    ROUND(SUM(CASE WHEN f.arr_delay_mins > 0
              THEN f.arr_delay_mins ELSE 0 END), 0)    AS total_delay_mins,
    ROUND(AVG(CASE WHEN f.arr_delayed_flag = 1
              THEN f.arr_delay_mins END), 2)           AS avg_delay_mins
FROM fact_delays f
JOIN dim_airport o ON f.origin_airport_key = o.airport_key
JOIN dim_airport d ON f.dest_airport_key = d.airport_key
WHERE o.record_type = 'SNAPSHOT_V1'
  AND d.record_type = 'SNAPSHOT_V1'
  AND f.is_cancelled = 0
GROUP BY o.airport_code, d.airport_code
HAVING COUNT(*) >= 1000  -- minimum volume threshold
ORDER BY total_delay_mins DESC
LIMIT 20;