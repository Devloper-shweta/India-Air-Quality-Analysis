-- =============================================================
-- analysis_queries.sql
-- India Air Quality Analysis — Analytical SQL Queries
-- =============================================================
-- Run these against the `air_quality_db` database after load.py
-- has populated the `locations` and `measurements` tables.
--
-- Sections:
--   1. Top polluted cities
--   2. Average PM2.5 by state
--   3. Pollutant trends over time
--   4. Daily averages
--   5. Monthly averages
--   6. Highest pollution locations (station-level)
--   7. KPI summary queries (for Power BI cards)
--   8. Reusable views for Power BI to connect to directly
-- =============================================================


-- =============================================================
-- 1. TOP POLLUTED CITIES (by average PM2.5, all-time)
-- =============================================================
SELECT
    l.city,
    l.state,
    ROUND(AVG(m.value)::numeric, 2) AS avg_pm25,
    COUNT(DISTINCT l.location_id)   AS station_count,
    COUNT(*)                        AS reading_count
FROM measurements m
JOIN locations l ON l.location_id = m.location_id
WHERE m.pollutant = 'pm25'
GROUP BY l.city, l.state
HAVING COUNT(*) >= 5                 -- exclude cities with too few readings to be reliable
ORDER BY avg_pm25 DESC
LIMIT 20;


-- =============================================================
-- 2. AVERAGE PM2.5 BY STATE
-- =============================================================
SELECT
    l.state,
    ROUND(AVG(m.value)::numeric, 2) AS avg_pm25,
    ROUND(MIN(m.value)::numeric, 2) AS min_pm25,
    ROUND(MAX(m.value)::numeric, 2) AS max_pm25,
    COUNT(DISTINCT l.location_id)   AS station_count
FROM measurements m
JOIN locations l ON l.location_id = m.location_id
WHERE m.pollutant = 'pm25'
  AND l.state <> 'Unknown'
GROUP BY l.state
ORDER BY avg_pm25 DESC;


-- =============================================================
-- 3. POLLUTANT TRENDS OVER TIME (monthly average, per pollutant)
-- =============================================================
SELECT
    m.pollutant_display,
    m.year,
    m.month,
    m.month_name,
    ROUND(AVG(m.value)::numeric, 2) AS avg_value,
    COUNT(*)                        AS reading_count
FROM measurements m
GROUP BY m.pollutant_display, m.year, m.month, m.month_name
ORDER BY m.pollutant_display, m.year, m.month;


-- =============================================================
-- 4. DAILY AVERAGES (across all of India, per pollutant)
-- =============================================================
SELECT
    m.measurement_date,
    m.pollutant_display,
    ROUND(AVG(m.value)::numeric, 2) AS daily_avg_value,
    COUNT(DISTINCT m.location_id)   AS reporting_stations
FROM measurements m
GROUP BY m.measurement_date, m.pollutant_display
ORDER BY m.measurement_date DESC, m.pollutant_display;


-- =============================================================
-- 5. MONTHLY AVERAGES (across all of India, per pollutant)
-- =============================================================
SELECT
    m.year,
    m.month,
    m.month_name,
    m.pollutant_display,
    ROUND(AVG(m.value)::numeric, 2) AS monthly_avg_value,
    COUNT(DISTINCT m.location_id)   AS reporting_stations
FROM measurements m
GROUP BY m.year, m.month, m.month_name, m.pollutant_display
ORDER BY m.year, m.month, m.pollutant_display;


-- =============================================================
-- 6. HIGHEST POLLUTION LOCATIONS (station-level, any pollutant)
-- =============================================================
SELECT
    l.location_name,
    l.city,
    l.state,
    m.pollutant_display,
    ROUND(AVG(m.value)::numeric, 2) AS avg_value,
    ROUND(MAX(m.value)::numeric, 2) AS peak_value,
    COUNT(*)                        AS reading_count
FROM measurements m
JOIN locations l ON l.location_id = m.location_id
GROUP BY l.location_name, l.city, l.state, m.pollutant_display
HAVING COUNT(*) >= 5
ORDER BY avg_value DESC
LIMIT 25;


-- =============================================================
-- 7. KPI SUMMARY QUERIES (for Power BI KPI cards)
-- =============================================================

-- 7a. National average PM2.5 (headline KPI)
SELECT ROUND(AVG(value)::numeric, 2) AS national_avg_pm25
FROM measurements
WHERE pollutant = 'pm25';

-- 7b. National average PM10
SELECT ROUND(AVG(value)::numeric, 2) AS national_avg_pm10
FROM measurements
WHERE pollutant = 'pm10';

-- 7c. Total active monitoring stations
SELECT COUNT(DISTINCT location_id) AS total_stations
FROM locations;

-- 7d. Most polluted city overall (by average PM2.5)
SELECT l.city, l.state, ROUND(AVG(m.value)::numeric, 2) AS avg_pm25
FROM measurements m
JOIN locations l ON l.location_id = m.location_id
WHERE m.pollutant = 'pm25'
GROUP BY l.city, l.state
HAVING COUNT(*) >= 5
ORDER BY avg_pm25 DESC
LIMIT 1;

-- 7e. Date range covered by the dataset
SELECT MIN(measurement_date) AS earliest_date, MAX(measurement_date) AS latest_date
FROM measurements;


-- =============================================================
-- 8. REUSABLE VIEWS — connect Power BI directly to these
-- =============================================================

-- 8a. Flat, denormalized view for Power BI's data model (one row per reading)
CREATE OR REPLACE VIEW vw_air_quality_flat AS
SELECT
    m.id,
    l.location_id,
    l.location_name,
    l.city,
    l.state,
    l.country,
    l.latitude,
    l.longitude,
    m.sensor_id,
    m.pollutant,
    m.pollutant_display,
    m.value,
    m.units,
    m.min_value,
    m.max_value,
    m.coverage_percent,
    m.measurement_date,
    m.year,
    m.month,
    m.month_name,
    m.day,
    m.weekday
FROM measurements m
JOIN locations l ON l.location_id = m.location_id;

-- 8b. Pre-aggregated city-level monthly summary (lighter-weight for dashboard drill-through)
CREATE OR REPLACE VIEW vw_city_monthly_summary AS
SELECT
    l.city,
    l.state,
    m.pollutant_display,
    m.year,
    m.month,
    m.month_name,
    ROUND(AVG(m.value)::numeric, 2) AS avg_value,
    ROUND(MAX(m.value)::numeric, 2) AS max_value,
    COUNT(*)                        AS reading_count
FROM measurements m
JOIN locations l ON l.location_id = m.location_id
GROUP BY l.city, l.state, m.pollutant_display, m.year, m.month, m.month_name;

-- 8c. State-level ranking view (feeds the "Top polluted states" visual)
CREATE OR REPLACE VIEW vw_state_ranking AS
SELECT
    l.state,
    m.pollutant_display,
    ROUND(AVG(m.value)::numeric, 2) AS avg_value,
    RANK() OVER (PARTITION BY m.pollutant_display ORDER BY AVG(m.value) DESC) AS pollution_rank
FROM measurements m
JOIN locations l ON l.location_id = m.location_id
WHERE l.state <> 'Unknown'
GROUP BY l.state, m.pollutant_display;
