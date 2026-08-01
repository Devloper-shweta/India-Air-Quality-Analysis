import pandas as pd
import psycopg2

from psycopg2.extras import execute_values

from utils import (
    DATA_PROCESSED_DIR,
    DB_CONFIG,
    get_logger,
)
CSV_FILE = DATA_PROCESSED_DIR / "air_quality_cleaned.csv"

TABLE_NAME = "air_quality_openaq"

logger = get_logger("load")

PROCESSED_CSV = DATA_PROCESSED_DIR / "air_quality_cleaned.csv"


def connect_db():

    logger.info("Connecting PostgreSQL...")

    conn = psycopg2.connect(

        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]

    )

    logger.info("Connected Successfully.")

    return conn
def create_table(conn):

    logger.info("Creating table if not exists...")

    cursor = conn.cursor()

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS air_quality_openaq (

        id SERIAL PRIMARY KEY,

        location_id BIGINT,

        location_name TEXT,

        locality TEXT,

        state TEXT,

        country_name TEXT,

        latitude DOUBLE PRECISION,

        longitude DOUBLE PRECISION,

        sensor_id BIGINT,

        parameter VARCHAR(50),

        units VARCHAR(50),

        value DOUBLE PRECISION,

        coverage DOUBLE PRECISION,

        datetime_utc TIMESTAMP,

        datetime_local TIMESTAMP,

        year INTEGER,

        month INTEGER,

        month_name VARCHAR(20),

        day INTEGER,

        day_name VARCHAR(20),

        hour INTEGER,

        is_weekend BOOLEAN

    );

    """)

    cursor.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'air_quality_openaq'
              AND column_name = 'is_weekend'
        ) THEN
            ALTER TABLE air_quality_openaq ADD COLUMN is_weekend BOOLEAN;
        END IF;
    END $$;
    """)

    conn.commit()

    cursor.close()

    logger.info("Table Ready.")
# ---------------------------------------------------------
# Load CSV
# ---------------------------------------------------------

def load_csv():

    logger.info("Loading Processed CSV...")

    df = pd.read_csv(PROCESSED_CSV)

    logger.info(f"Records Found : {len(df)}")

    # -----------------------------
    # Convert datetime columns
    # -----------------------------

    df["datetime_utc"] = pd.to_datetime(
        df["datetime_utc"],
        errors="coerce"
    )

    df["datetime_local"] = pd.to_datetime(
        df["datetime_local"],
        errors="coerce"
    )

    # -----------------------------
    # Replace NaN with None
    # -----------------------------

    df = df.where(pd.notnull(df), None)

    logger.info("CSV Loaded Successfully.")

    return df
# ---------------------------------------------------------
# Prepare Records
# ---------------------------------------------------------

def prepare_dataframe_for_insert(df):

    prepared_df = df.copy()

    prepared_df = prepared_df.where(pd.notnull(prepared_df), None)

    if "is_weekend" in prepared_df.columns:

        prepared_df["is_weekend"] = (
        prepared_df["is_weekend"]
        .fillna(False)
        .apply(lambda x: bool(x))
    )

    return prepared_df


# ---------------------------------------------------------
# Insert Records
# ---------------------------------------------------------

def insert_data(conn, df):

    logger.info("Preparing Records...")

    df = prepare_dataframe_for_insert(df)

    records = []

    for row in df.itertuples(index=False, name=None):

        row = tuple(
            bool(v) if type(v).__name__ == "bool_" else v
            for v in row
        )

        records.append(row)

    cursor = conn.cursor()

    query = """
    INSERT INTO air_quality_openaq (

        location_id,
        location_name,
        locality,
        state,
        country_name,
        latitude,
        longitude,
        sensor_id,
        parameter,
        units,
        value,
        coverage,
        datetime_utc,
        datetime_local,
        year,
        month,
        month_name,
        day,
        day_name,
        hour,
        is_weekend

    )
    VALUES %s
    """

    logger.info(f"Inserting {len(records)} records...")

    execute_values(
        cursor,
        query,
        records,
        page_size=5000
    )

    conn.commit()
    cursor.close()

    logger.info("Data Inserted Successfully.")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    logger.info("=" * 60)
    logger.info("Starting Load Stage")
    logger.info("=" * 60)

    conn = None

    try:

        # Connect Database
        conn = connect_db()

        # Create Table
        create_table(conn)

        # Load CSV
        df = load_csv()

        # Insert Data
        insert_data(conn, df)

        logger.info("=" * 60)
        logger.info("Load Stage Completed Successfully")
        logger.info("=" * 60)

    except Exception as e:

        logger.exception(e)

        if conn:
            conn.rollback()

        raise

    finally:

        if conn:

            conn.close()

            logger.info("Database Connection Closed.")


# ---------------------------------------------------------

if __name__ == "__main__":

    main()
