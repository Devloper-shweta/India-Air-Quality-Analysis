from typing import Any, Dict, List
import time

import pandas as pd
from tqdm import tqdm

from utils import (
    DATA_RAW_DIR,
    DEFAULT_PAGE_LIMIT,
    OPENAQ_BASE_URL,
    api_get,
    get_logger,
    get_session,
    save_json,
    validate_api_key,
)

logger = get_logger("extract_sensors")

LOCATIONS_CSV_PATH = DATA_RAW_DIR / "locations_raw.csv"
RAW_JSON_PATH = DATA_RAW_DIR / "sensors_raw.json"
RAW_CSV_PATH = DATA_RAW_DIR / "sensors_raw.csv"
FAILED_LOCATIONS_PATH = DATA_RAW_DIR / "failed_locations.csv"


def load_location_ids() -> List[int]:

    if not LOCATIONS_CSV_PATH.exists():
        raise FileNotFoundError(
            f"{LOCATIONS_CSV_PATH} not found. Run extract_locations.py first."
        )

    df = pd.read_csv(LOCATIONS_CSV_PATH)

    location_ids = (
        df["location_id"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    logger.info(
        "Loaded %s unique location IDs",
        len(location_ids)
    )

    return location_ids


def fetch_sensors_for_location(session, location_id: int):

    endpoint = f"{OPENAQ_BASE_URL}/locations/{location_id}/sensors"
    logger.info(f"Requesting sensors for Location {location_id}")

    all_sensors = []

    page = 1

    while True:

        params = {
            "limit": DEFAULT_PAGE_LIMIT,
            "page": page
        }

        try:

            payload = api_get(
                session=session,
                url=endpoint,
                params=params,
                logger=logger
            )

            if payload is None:
                logger.warning(
                    f"Skipping Location {location_id}"
                )
                break

            results = payload.get("results", [])

            if len(results) == 0:
                break

            all_sensors.extend(results)

            if len(results) < DEFAULT_PAGE_LIMIT:
                break

            page += 1

            time.sleep(1)

        except Exception as e:

            logger.error(
                f"Location {location_id} failed : {e}"
            )

            break

    return all_sensors


def flatten_sensors(location_id, raw_sensors):

    rows = []

    for sensor in raw_sensors:

        parameter = sensor.get("parameter") or {}

        rows.append({

            "location_id": location_id,

            "sensor_id": sensor.get("id"),

            "sensor_name": sensor.get("name"),

            "parameter_id": parameter.get("id"),

            "parameter_name": parameter.get("name"),

            "parameter_display_name": parameter.get("displayName"),

            "units": parameter.get("units"),

            "datetime_first": (
                sensor.get("datetimeFirst") or {}
            ).get("utc"),

            "datetime_last": (
                sensor.get("datetimeLast") or {}
            ).get("utc"),

        })

    return rows
# Skip problematic location
if location_id == 3409327:
        logger.warning(f"Skipping problematic location: {location_id}")
        failed_locations.append(location_id)
        continue

def main() -> None:

    logger.info("=== Starting extract_sensors.py ===")

    try:

        validate_api_key(logger)

        session = get_session()

        location_ids = load_location_ids()

        if not location_ids:
            logger.warning("No location IDs found.")
            return

        all_raw_by_location = {}

        flattened_rows = []

        failed_locations = []

        total_locations = len(location_ids)

        for index, location_id in enumerate(
            tqdm(location_ids,
                 desc="Fetching sensors",
                 unit="location"),
            start=1,
        ):

            logger.info(
                f"Processing {index}/{total_locations} | Location ID = {location_id}"
            )

            sensors = fetch_sensors_for_location(
                session,
                location_id
            )

            if not sensors:

                failed_locations.append(location_id)

                continue

            all_raw_by_location[str(location_id)] = sensors

            flattened_rows.extend(
                flatten_sensors(
                    location_id,
                    sensors
                )
            )

        if not flattened_rows:

            logger.error(
                "No sensor data downloaded."
            )

            return

# -------------------------
 # Save JSON
 # -------------------------

save_json(
all_raw_by_location,
RAW_JSON_PATH,
logger=logger
)

 # -------------------------
 # Save CSV
# -------------------------

df = (
pd.DataFrame(flattened_rows)
            .drop_duplicates(subset=["sensor_id"])
        )

        df.to_csv(
            RAW_CSV_PATH,
            index=False,
            encoding="utf-8"
        )

        logger.info(
            "Saved %s sensors.",
            len(df)
        )

        # -------------------------
        # Save Failed Locations
        # -------------------------

        if failed_locations:

            failed_df = pd.DataFrame({

                "location_id": failed_locations

            })

            failed_df.to_csv(
                FAILED_LOCATIONS_PATH,
                index=False
            )

            logger.warning(
                "%s failed locations saved.",
                len(failed_locations)
            )

        logger.info(
            "=== extract_sensors.py completed successfully ==="
        )
    except EnvironmentError as env_err:
        logger.error("Configuration error: %s", env_err)

    except FileNotFoundError as fnf_err:
        logger.error(str(fnf_err))

    except Exception as exc:
        logger.exception(
            "Unexpected error during sensor extraction: %s",
            exc
        )
        raise


if __name__ == "__main__":
    main()