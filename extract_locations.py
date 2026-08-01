"""
extract_locations.py
---------------------------------------------------------------------
Stage 1 of the ETL pipeline: EXTRACT — Locations

Fetches all air quality monitoring station "locations" in India from
the OpenAQ API v3 (`GET /v3/locations`, filtered by `iso=IN`), handling:

    - Pagination (OpenAQ returns results page by page)
    - Rate limiting (HTTP 429) via utils.api_get
    - Retries with exponential backoff on transient failures
    - A progress bar (tqdm) so long pulls show live progress

Outputs
-------
    data/raw/locations_raw.json   -> full raw API response (all pages)
    data/raw/locations_raw.csv    -> flattened location records

Run:
    python scripts/extract_locations.py
---------------------------------------------------------------------
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from tqdm import tqdm

from utils import (
    DATA_RAW_DIR,
    DEFAULT_PAGE_LIMIT,
    INDIA_ISO_CODE,
    OPENAQ_BASE_URL,
    api_get,
    get_logger,
    get_session,
    save_json,
    validate_api_key,
)

logger = get_logger("extract_locations")

LOCATIONS_ENDPOINT = f"{OPENAQ_BASE_URL}/locations"
RAW_JSON_PATH = DATA_RAW_DIR / "locations_raw.json"
RAW_CSV_PATH = DATA_RAW_DIR / "locations_raw.csv"


def fetch_all_india_locations(session) -> List[Dict[str, Any]]:
    """
    Page through GET /v3/locations?iso=IN until every India location
    has been retrieved. Returns the combined list of raw location
    records (as returned by the API, pre-flattening).
    """
    all_results: List[Dict[str, Any]] = []
    page = 1

    with tqdm(desc="Fetching India locations", unit="page") as progress_bar:
        while True:
            params = {
                "iso": INDIA_ISO_CODE,
                "limit": DEFAULT_PAGE_LIMIT,
                "page": page,
            }

            payload = api_get(session, LOCATIONS_ENDPOINT, params=params, logger=logger)

            if payload is None:
                logger.error("Aborting extraction: page %s failed after all retries.", page)
                break

            results = payload.get("results", [])
            found = payload.get("meta", {}).get("found", 0)

            if not results:
                logger.info("No more results at page %s. Extraction complete.", page)
                break

            all_results.extend(results)
            progress_bar.update(1)
            progress_bar.set_postfix(records=len(all_results), api_reports=found)

            # Stop once we've retrieved fewer records than the page limit —
            # this means we've reached the last page.
            if len(results) < DEFAULT_PAGE_LIMIT:
                logger.info("Reached final page (%s). Total records: %s", page, len(all_results))
                break

            page += 1

    return all_results


def flatten_locations(raw_locations: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Flatten the nested OpenAQ location JSON into a tabular structure
    suitable for CSV export and downstream transform/load stages.
    """
    records = []

    for loc in raw_locations:
        coordinates = loc.get("coordinates") or {}
        country = loc.get("country") or {}
        provider = loc.get("provider") or {}
        sensors = loc.get("sensors") or []

        sensor_ids = [str(s.get("id")) for s in sensors if s.get("id") is not None]
        parameters = [
            (s.get("parameter") or {}).get("name", "")
            for s in sensors
            if s.get("parameter")
        ]

        records.append({
            "location_id": loc.get("id"),
            "location_name": loc.get("name"),
            "locality": loc.get("locality"),
            "timezone": loc.get("timezone"),
            "country_code": country.get("code"),
            "country_name": country.get("name"),
            "latitude": coordinates.get("latitude"),
            "longitude": coordinates.get("longitude"),
            "provider_id": provider.get("id"),
            "provider_name": provider.get("name"),
            "is_mobile": loc.get("isMobile"),
            "is_monitor": loc.get("isMonitor"),
            "datetime_first": (loc.get("datetimeFirst") or {}).get("utc"),
            "datetime_last": (loc.get("datetimeLast") or {}).get("utc"),
            "sensor_ids": ";".join(sensor_ids),
            "parameters": ";".join(sorted(set(parameters))),
        })

    return pd.DataFrame.from_records(records)


def main() -> None:
    """Orchestrate the locations extraction stage end to end."""
    logger.info("=== Starting extract_locations.py ===")

    try:
        validate_api_key(logger)
        session = get_session()

        raw_locations = fetch_all_india_locations(session)

        if not raw_locations:
            logger.warning("No location data retrieved. Exiting without writing files.")
            return

        # Save the untouched raw API payload for traceability / re-processing
        save_json(raw_locations, RAW_JSON_PATH, logger=logger)

        # Save a flattened CSV version for quick inspection and downstream use
        df = flatten_locations(raw_locations)
        RAW_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(RAW_CSV_PATH, index=False, encoding="utf-8")
        logger.info("Saved raw CSV -> %s (%s rows)", RAW_CSV_PATH, len(df))

        logger.info("=== extract_locations.py completed successfully ===")

    except EnvironmentError as env_err:
        logger.error("Configuration error: %s", env_err)
    except Exception as exc:  # noqa: BLE001 — top-level script guard
        logger.exception("Unexpected error during location extraction: %s", exc)
        raise


if __name__ == "__main__":
    main()
