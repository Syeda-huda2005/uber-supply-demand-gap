-- ============================================================
--  UBER SUPPLY-DEMAND GAP  |  SQL INSIGHTS
--  Dataset : Uber Request Data (6,745 rows)
--  Tool    : SQLite / MySQL / PostgreSQL compatible
-- ============================================================

-- ─────────────────────────────────────────────────────────────
--  STEP 0 : Create & load the table
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS uber_requests (
    request_id        INTEGER,
    pickup_point      TEXT,
    driver_id         TEXT,
    status            TEXT,
    request_timestamp TEXT,
    drop_timestamp    TEXT,
    request_hour      INTEGER,
    request_weekday   TEXT,
    trip_duration_min REAL,
    time_slot         TEXT,
    is_fulfilled      INTEGER   -- 1 = Trip Completed, 0 = Not
);

-- After creating, import the cleaned CSV:
-- SQLite: .mode csv
--         .import Cleaned_Uber_Data.csv uber_requests


-- ============================================================
--  PROBLEM STATEMENT 1
--  What is the overall distribution of ride request statuses?
--  Business Goal: Understand how many rides are actually fulfilled
-- ============================================================

SELECT
    status,
    COUNT(*)                                              AS total_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2)    AS percentage
FROM uber_requests
GROUP BY status
ORDER BY total_count DESC;

-- INSIGHT: Only ~42% of rides are completed.
-- No Cars Available = ~39%, Cancelled = ~19%.
-- 58% of demand is UNFULFILLED.


-- ============================================================
--  PROBLEM STATEMENT 2
--  How does status vary between City and Airport pickups?
--  Business Goal: Identify which pickup point has the worst gap
-- ============================================================

SELECT
    pickup_point,
    status,
    COUNT(*)                                                              AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY pickup_point), 2)
        AS pct_within_pickup
FROM uber_requests
GROUP BY pickup_point, status
ORDER BY pickup_point, count DESC;

-- INSIGHT:
-- City    → ~39% Cancellations (drivers avoid airport trips)
-- Airport → ~60% No Cars Available (nobody positioned there)


-- ============================================================
--  PROBLEM STATEMENT 3
--  Which hours have the highest demand and lowest fulfillment?
--  Business Goal: Identify peak hours for driver allocation
-- ============================================================

SELECT
    request_hour,
    COUNT(*)                                               AS total_requests,
    SUM(is_fulfilled)                                      AS completed,
    COUNT(*) - SUM(is_fulfilled)                          AS unfulfilled,
    ROUND(SUM(is_fulfilled) * 100.0 / COUNT(*), 2)        AS fulfillment_rate_pct
FROM uber_requests
GROUP BY request_hour
ORDER BY request_hour;

-- INSIGHT: Two demand spikes - 5-10 AM and 5-10 PM.
-- Fulfillment drops below 30% in these windows.


-- ============================================================
--  PROBLEM STATEMENT 4
--  During which hours are cancellations highest from City?
--  Business Goal: Find the morning cancellation pattern
-- ============================================================

SELECT
    request_hour,
    COUNT(*)  AS total_city_requests,
    SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END)   AS cancellations,
    ROUND(
        SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
    2) AS cancellation_rate_pct
FROM uber_requests
WHERE pickup_point = 'City'
GROUP BY request_hour
ORDER BY cancellation_rate_pct DESC
LIMIT 10;

-- INSIGHT: Hours 5-9 AM from City have 50%+ cancellation rate.
-- Drivers refuse morning airport trips.


-- ============================================================
--  PROBLEM STATEMENT 5
--  During which hours is "No Cars" worst at Airport?
--  Business Goal: Pinpoint the evening Airport supply gap
-- ============================================================

SELECT
    request_hour,
    COUNT(*) AS total_airport_requests,
    SUM(CASE WHEN status = 'No Cars Available' THEN 1 ELSE 0 END) AS no_cars_count,
    ROUND(
        SUM(CASE WHEN status = 'No Cars Available' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
    2) AS no_cars_rate_pct
FROM uber_requests
WHERE pickup_point = 'Airport'
GROUP BY request_hour
ORDER BY no_cars_rate_pct DESC
LIMIT 10;

-- INSIGHT: Hours 17-21 at Airport have 70%+ No Cars rate.
-- Severe evening supply vacuum at the airport.


-- ============================================================
--  PROBLEM STATEMENT 6
--  What is the supply vs demand gap per time slot?
--  Business Goal: Quantify unfulfilled demand by time window
-- ============================================================

SELECT
    time_slot,
    COUNT(*)                        AS total_demand,
    SUM(is_fulfilled)               AS supply_fulfilled,
    COUNT(*) - SUM(is_fulfilled)    AS gap,
    ROUND(SUM(is_fulfilled) * 100.0 / COUNT(*), 2) AS fulfillment_pct,
    ROUND((COUNT(*) - SUM(is_fulfilled)) * 100.0 / COUNT(*), 2) AS gap_pct
FROM uber_requests
GROUP BY time_slot
ORDER BY gap DESC;

-- INSIGHT: Evening Rush has the largest absolute gap.
-- Morning Rush has the highest cancellation-driven gap.


-- ============================================================
--  PROBLEM STATEMENT 7
--  How many drivers are active and what is avg trips/driver?
--  Business Goal: Assess driver supply capacity
-- ============================================================

SELECT
    COUNT(DISTINCT driver_id)   AS total_active_drivers,
    COUNT(CASE WHEN status = 'Trip Completed' THEN 1 END)   AS total_completed_trips,
    ROUND(
        COUNT(CASE WHEN status = 'Trip Completed' THEN 1 END) * 1.0
        / COUNT(DISTINCT driver_id),
    2) AS avg_trips_per_driver
FROM uber_requests
WHERE driver_id IS NOT NULL
  AND driver_id != '';

-- INSIGHT: Shows driver capacity vs completed trips ratio.


-- ============================================================
--  PROBLEM STATEMENT 8
--  What is average trip duration by pickup point?
--  Business Goal: Does trip length discourage drivers?
-- ============================================================

SELECT
    pickup_point,
    COUNT(*)                                   AS completed_trips,
    ROUND(AVG(trip_duration_min), 2)           AS avg_duration_min,
    ROUND(MIN(trip_duration_min), 2)           AS min_duration_min,
    ROUND(MAX(trip_duration_min), 2)           AS max_duration_min
FROM uber_requests
WHERE status = 'Trip Completed'
  AND trip_duration_min IS NOT NULL
GROUP BY pickup_point;

-- INSIGHT: Airport trips ~52 min avg vs City ~47 min.
-- Longer trips = slower driver turnaround = supply gap.


-- ============================================================
--  PROBLEM STATEMENT 9
--  Which day of week has highest unfulfilled requests?
--  Business Goal: Check if any day worsens the gap
-- ============================================================

SELECT
    request_weekday,
    COUNT(*)                        AS total_requests,
    SUM(is_fulfilled)               AS completed,
    COUNT(*) - SUM(is_fulfilled)    AS unfulfilled,
    ROUND(SUM(is_fulfilled) * 100.0 / COUNT(*), 2) AS fulfillment_pct
FROM uber_requests
GROUP BY request_weekday
ORDER BY unfulfilled DESC;

-- INSIGHT: Demand is consistent across weekdays.
-- The problem is time-of-day based, not day-of-week based.


-- ============================================================
--  PROBLEM STATEMENT 10
--  Full cross-tab: Pickup Point x Time Slot x Status
--  Business Goal: Confirm the two critical problem cells
-- ============================================================

SELECT
    pickup_point,
    time_slot,
    status,
    COUNT(*) AS request_count
FROM uber_requests
GROUP BY pickup_point, time_slot, status
ORDER BY request_count DESC;

-- INSIGHT (top 2 rows will be):
-- Airport + Evening Rush + No Cars Available → ~1,048 requests  (PROBLEM 1)
-- City    + Morning Rush + Cancelled          →  ~786 requests  (PROBLEM 2)
-- These two rows ARE the core of the supply-demand gap.


-- ============================================================
--  PROBLEM STATEMENT 11
--  What % of total demand do the two critical windows cover?
--  Business Goal: Quantify the impact of fixing just these two
-- ============================================================

SELECT
    'City Morning Rush Cancellations'   AS problem_window,
    COUNT(*)                            AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM uber_requests), 2) AS pct_of_total
FROM uber_requests
WHERE pickup_point = 'City'
  AND time_slot    = 'Morning Rush (5-10)'
  AND status       = 'Cancelled'

UNION ALL

SELECT
    'Airport Evening Rush No Cars'      AS problem_window,
    COUNT(*)                            AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM uber_requests), 2) AS pct_of_total
FROM uber_requests
WHERE pickup_point = 'Airport'
  AND time_slot    = 'Evening Rush (17-22)'
  AND status       = 'No Cars Available';

-- INSIGHT: These two windows = ~27% of ALL requests unfulfilled.
-- Fixing them alone could push fulfillment from 42% → ~69%.


-- ============================================================
--  PROBLEM STATEMENT 12
--  Rank hours by supply-demand gap (largest first)
--  Business Goal: Prioritize hours needing most intervention
-- ============================================================

SELECT
    request_hour,
    COUNT(*)                       AS total_demand,
    SUM(is_fulfilled)              AS supply,
    COUNT(*) - SUM(is_fulfilled)   AS gap,
    RANK() OVER (ORDER BY (COUNT(*) - SUM(is_fulfilled)) DESC) AS gap_rank
FROM uber_requests
GROUP BY request_hour
ORDER BY gap_rank;

-- INSIGHT: Top-ranked hours (biggest gap) get first priority
-- for driver incentives and surge pricing.

-- ============================================================
--  END OF SQL INSIGHTS SCRIPT
-- ============================================================
