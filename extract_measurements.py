"""
extract_measurements.py
---------------------------------------------------------
Stage 3 : Download Measurements from OpenAQ
---------------------------------------------------------
"""

import json
import os
import time

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from utils import (
    DATA_RAW_DIR,
    DEFAULT_PAGE_LIMIT,
    OPENAQ_BASE_URL,
    api_get,
    get_logger,
    get_session,
)

# ---------------------------------------------------------
# Logger
# ---------------------------------------------------------

logger = get_logger("extract_measurements")

# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

load_dotenv()

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY not found.")

# ---------------------------------------------------------
# File Paths
# ---------------------------------------------------------

LOCATIONS_FILE = DATA_RAW_DIR / "locations_raw.csv"

RAW_CSV = DATA_RAW_DIR / "measurements_raw.csv"

RAW_JSON = DATA_RAW_DIR / "measurements_raw.json"

# ---------------------------------------------------------
# Download Settings
# ---------------------------------------------------------

DATE_FROM = "2024-01-01T00:00:00Z"

DATE_TO = "2024-12-31T23:59:59Z"

# Testing
MAX_SENSORS = 100

MAX_PAGES = 10

# ---------------------------------------------------------
# Load Sensor IDs
# ---------------------------------------------------------

def load_sensor_ids():

    logger.info("Loading Sensor IDs...")

    if not LOCATIONS_FILE.exists():
        raise FileNotFoundError(
            f"{LOCATIONS_FILE} not found."
        )

    locations = pd.read_csv(LOCATIONS_FILE)

    sensor_ids = []

    for value in locations["sensor_ids"].dropna():

        sensors = str(value).split(";")

        for sensor in sensors:

            sensor = sensor.strip()

            if sensor.isdigit():

                sensor_ids.append(int(sensor))

    sensor_ids = sorted(list(set(sensor_ids)))

    logger.info(
        f"Total Unique Sensors : {len(sensor_ids)}"
    )

    return sensor_ids
# ---------------------------------------------------------
# Download Measurements for One Sensor
# ---------------------------------------------------------

def download_sensor_measurements(session, sensor_id):

    endpoint = f"{OPENAQ_BASE_URL}/sensors/{sensor_id}/measurements"

    all_rows = []

    page = 1

    while True:

        params = {

            "limit": DEFAULT_PAGE_LIMIT,
            "page": page,
            "date_from": DATE_FROM,
            "date_to": DATE_TO

        }

        payload = api_get(

            session=session,
            url=endpoint,
            params=params,
            logger=logger

        )

        # API Error
        if payload is None:

            logger.warning(
                f"Sensor {sensor_id} : API returned None"
            )

            break

        results = payload.get("results", [])

        # No More Records
        if len(results) == 0:

            break

        # Flatten JSON
        for row in results:

            period = row.get("period", {})
            parameter = row.get("parameter", {})
            coverage = row.get("coverage", {})

            all_rows.append({

                "sensor_id": sensor_id,

                "parameter": parameter.get("name"),

                "units": parameter.get("units"),

                "value": row.get("value"),

                "datetime_utc":
                    period.get("datetimeFrom", {}).get("utc"),

                "datetime_local":
                    period.get("datetimeFrom", {}).get("local"),

                "coverage":
                    coverage.get("percentCoverage")

            })

        logger.info(

            f"Sensor {sensor_id} | "
            f"Page {page} | "
            f"Records {len(results)}"

        )

        # Last Page
        if len(results) < DEFAULT_PAGE_LIMIT:

            break

        page += 1

        # Safety Limit
        if MAX_PAGES is not None:

            if page > MAX_PAGES:

                logger.warning(

                    f"Sensor {sensor_id} reached "
                    f"{MAX_PAGES} pages."

                )

                break

        # Avoid Rate Limit
        time.sleep(0.3)

    return all_rows
# ---------------------------------------------------------
# Main Download Loop
# ---------------------------------------------------------

def main():

    logger.info("=" * 60)
    logger.info("Starting Measurement Extraction")
    logger.info("=" * 60)

    # Create ONE session only
    session = get_session()

    # Load Sensor IDs
    sensor_ids = load_sensor_ids()

    if len(sensor_ids) == 0:

        logger.error("No Sensor IDs found.")

        return

    logger.info(
        f"Downloading measurements for first "
        f"{min(MAX_SENSORS, len(sensor_ids))} sensors..."
    )

    all_measurements = []

    for index, sensor_id in enumerate(

        tqdm(
            sensor_ids[:MAX_SENSORS],
            desc="Downloading Measurements"
        ),

        start=1

    ):

        logger.info(
            f"Sensor {index}/{min(MAX_SENSORS, len(sensor_ids))}"
            f" | ID = {sensor_id}"
        )

        try:

            sensor_rows = download_sensor_measurements(
                session,
                sensor_id
            )

            if sensor_rows:

                all_measurements.extend(sensor_rows)

        except Exception as e:

            logger.exception(
                f"Sensor {sensor_id} failed : {e}"
            )

            continue

    logger.info(
        f"Downloaded {len(all_measurements)} measurements."
    )

    if len(all_measurements) == 0:

        logger.warning("No measurements downloaded.")

        return

    save_measurements(all_measurements)

    logger.info("=" * 60)
    logger.info("Measurement Extraction Completed")
    logger.info("=" * 60)

# ---------------------------------------------------------
# Save Measurements
# ---------------------------------------------------------

def save_measurements(all_measurements):

    logger.info("Saving measurements...")

    df = pd.DataFrame(all_measurements)

    # Remove duplicate rows
    df.drop_duplicates(inplace=True)

    # Sort records
    if "datetime_utc" in df.columns:
        df.sort_values(
            by="datetime_utc",
            inplace=True
        )

    # Save CSV
    df.to_csv(
        RAW_CSV,
        index=False,
        encoding="utf-8"
    )

    # Save JSON
    with open(
        RAW_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_measurements,
            f,
            indent=2,
            ensure_ascii=False
        )

    logger.info(f"CSV Saved : {RAW_CSV}")
    logger.info(f"JSON Saved : {RAW_JSON}")
    logger.info(f"Total Records : {len(df)}")


# ---------------------------------------------------------
# Run Script
# ---------------------------------------------------------

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        logger.warning("Process Interrupted by User.")

    except Exception as e:

        logger.exception(e)

        raise