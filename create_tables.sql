-- =============================================================
-- create_tables.sql
-- India Air Quality Analysis — PostgreSQL Schema
-- =============================================================
-- Design: two tables in a simple star-style relationship.
--   locations    -> one row per monitoring station (dimension)
--   measurements -> one row per location/sensor/pollutant/day (fact)
--
-- A UNIQUE constraint on measurements makes re-running load.py
-- idempotent (safe to re-run without creating duplicate rows).
-- =============================================================

CREATE TABLE IF NOT EXISTS locations (
    location_id     BIGINT PRIMARY KEY,
    location_name   VARCHAR(255),
    city            VARCHAR(150),
    state           VARCHAR(100),
    country         VARCHAR(100),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS measurements (
    id                  BIGSERIAL PRIMARY KEY,
    location_id         BIGINT NOT NULL REFERENCES locations(location_id) ON DELETE CASCADE,
    sensor_id           BIGINT NOT NULL,
    pollutant           VARCHAR(50) NOT NULL,          -- normalized code, e.g. 'pm25'
    pollutant_display   VARCHAR(50),                    -- readable form, e.g. 'PM2.5'
    value               DOUBLE PRECISION NOT NULL,       -- daily average concentration
    units               VARCHAR(30),
    min_value           DOUBLE PRECISION,
    max_value            DOUBLE PRECISION,
    coverage_percent     DOUBLE PRECISION,                 -- % of expected readings that day
    measurement_date    DATE NOT NULL,
    year                INT,
    month               INT,
    month_name          VARCHAR(20),
    day                 INT,
    weekday             VARCHAR(20),
    CONSTRAINT uq_measurement UNIQUE (location_id, sensor_id, measurement_date, pollutant)
);

-- Indexes to speed up the analytical queries in analysis_queries.sql
-- and the Power BI dashboard's filters/slicers.
CREATE INDEX IF NOT EXISTS idx_measurements_date       ON measurements (measurement_date);
CREATE INDEX IF NOT EXISTS idx_measurements_pollutant  ON measurements (pollutant);
CREATE INDEX IF NOT EXISTS idx_measurements_location   ON measurements (location_id);
CREATE INDEX IF NOT EXISTS idx_measurements_year_month ON measurements (year, month);

CREATE INDEX IF NOT EXISTS idx_locations_state ON locations (state);
CREATE INDEX IF NOT EXISTS idx_locations_city  ON locations (city);
