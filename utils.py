"""
utils.py
---------------------------------------------------------------------
Shared utility module for the India Air Quality Analysis ETL pipeline.

Centralizes logic that would otherwise be duplicated across
extract_locations.py, extract_sensors.py, extract_measurements.py,
transform.py, and load.py:

    - Project-relative path configuration
    - .env-based configuration (never hardcode credentials)
    - Structured logging (console + per-module log file)
    - A resilient requests.Session with retry/backoff
    - Explicit OpenAQ rate-limit (HTTP 429) handling
    - JSON/CSV file I/O helpers

Import this module from any script:
    from utils import get_logger, get_session, api_get, ...
---------------------------------------------------------------------
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configurable paths (resolved relative to project root, not the CWD, so
# scripts work correctly no matter where they're launched from)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOG_DIR = PROJECT_ROOT / "logs"

for _dir in (DATA_RAW_DIR, DATA_PROCESSED_DIR, LOG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Environment / configuration — credentials are ALWAYS read from .env,
# never hardcoded in source.
# ---------------------------------------------------------------------------
load_dotenv(PROJECT_ROOT / ".env")

OPENAQ_API_KEY: str = os.getenv("OPENAQ_API_KEY", "")
OPENAQ_BASE_URL: str = os.getenv("OPENAQ_BASE_URL", "https://api.openaq.org/v3")

DB_CONFIG: Dict[str, str] = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "air_quality_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# OpenAQ / pipeline constants
INDIA_ISO_CODE = "IN"        # ISO 3166-1 alpha-2 code used to filter locations to India
DEFAULT_PAGE_LIMIT = 1000     # Max results per page allowed by OpenAQ API v3
MAX_RETRIES = 5
BACKOFF_FACTOR = 2           # exponential backoff base, in seconds
REQUEST_TIMEOUT = 60          # seconds per request


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger that writes to both stdout and a
    dedicated log file (logs/<name>.log). Safe to call multiple
    times for the same name without creating duplicate handlers.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def validate_api_key(logger: Optional[logging.Logger] = None) -> None:
    """Fail fast with a clear error if OPENAQ_API_KEY is missing from .env."""
    log = logger or get_logger("config")
    if not OPENAQ_API_KEY:
        log.error(
            "OPENAQ_API_KEY is missing. Add it to your .env file before "
            "running the pipeline (see README.md for setup instructions)."
        )
        raise EnvironmentError("Missing OPENAQ_API_KEY in .env")


def get_session() -> requests.Session:
    """
    Build a requests.Session pre-configured with:
      - the OpenAQ API key header (X-API-Key)
      - automatic retries with exponential backoff for transient
        network failures and common 5xx server errors

    HTTP 429 (rate limit) is handled explicitly in `api_get` below,
    since it requires reading OpenAQ's custom rate-limit headers
    rather than a blind retry.
    """
    session = requests.Session()
    session.headers.update({
        "X-API-Key": OPENAQ_API_KEY,
        "Accept": "application/json",
    })

    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def api_get(
    session: requests.Session,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
    max_retries: int = MAX_RETRIES,
) -> Optional[Dict[str, Any]]:
    """
    Perform a GET request against the OpenAQ API with explicit handling for:
      - HTTP 429 (rate limit)   -> sleep using the X-RateLimit-Reset header
      - Network/connection errors -> exponential backoff retry
      - Other non-200 responses   -> logged, then retried

    Returns the parsed JSON response body, or None once retries are exhausted.
    """
    log = logger or get_logger("api_client")
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)

            # --- Rate limit hit: back off using the server's own reset time ---
            if response.status_code == 429:
                reset_seconds = int(response.headers.get("x-ratelimit-reset", 5))
                log.warning(
                    "Rate limit hit (429). Sleeping %ss before retry (%s/%s)...",
                    reset_seconds, attempt, max_retries,
                )
                time.sleep(max(reset_seconds, 1))
                continue

            if response.status_code == 200:
                return response.json()

            log.error(
                "Request failed [%s] for %s (attempt %s/%s): %s",
                response.status_code, url, attempt, max_retries, response.text[:300],
            )
            # Skip timeout sensors
            if response.status_code == 408:
                log.warning(
                    "408 Timeout for %s. Skipping this request.",
                    url,
                )
                return None
                

        except requests.exceptions.RequestException as exc:
                log.warning(
                "Network error on attempt %s/%s for %s: %s",
                attempt, 
                max_retries, 
                url,
                exc,
            )

        sleep_time = BACKOFF_FACTOR ** attempt
        log.info("Retrying in %ss...", sleep_time)
        time.sleep(sleep_time)

    log.error("Exhausted all %s retries for URL: %s", max_retries, url)
    return None


def save_json(data: Any, filepath: Path, logger: Optional[logging.Logger] = None) -> None:
    """Persist any JSON-serializable object to disk (UTF-8, pretty-printed)."""
    log = logger or get_logger("file_io")
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info("Saved raw JSON -> %s", filepath)
    except OSError as exc:
        log.error("Failed to save JSON to %s: %s", filepath, exc)
        raise
