"""
transform.py
---------------------------------------------------------
Stage 4 : Transform Data
India Air Quality Analysis
---------------------------------------------------------
"""

from pathlib import Path
import pandas as pd
from tqdm import tqdm
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from utils import (
    DATA_RAW_DIR,
    DATA_PROCESSED_DIR,
    get_logger,
)
CITY_STATE = {

    # Delhi
    "Delhi": "Delhi",
    "New Delhi": "Delhi",
    "R K Puram": "Delhi",
    "Anand Vihar": "Delhi",

    # Maharashtra
    "Mumbai": "Maharashtra",
    "Pune": "Maharashtra",
    "Nagpur": "Maharashtra",
    "Nashik": "Maharashtra",
    "Aurangabad": "Maharashtra",
    "Kolhapur": "Maharashtra",
    "Thane": "Maharashtra",
    "Navi Mumbai": "Maharashtra",
    "Solapur": "Maharashtra",

    # Karnataka
    "Bengaluru": "Karnataka",
    "Bangalore": "Karnataka",
    "Mysuru": "Karnataka",
    "Hubli": "Karnataka",
    "Belgaum": "Karnataka",

    # Tamil Nadu
    "Chennai": "Tamil Nadu",
    "Coimbatore": "Tamil Nadu",
    "Madurai": "Tamil Nadu",
    "Salem": "Tamil Nadu",

    # Telangana
    "Hyderabad": "Telangana",
    "Warangal": "Telangana",

    # Gujarat
    "Ahmedabad": "Gujarat",
    "Surat": "Gujarat",
    "Vadodara": "Gujarat",
    "Rajkot": "Gujarat",

    # Rajasthan
    "Jaipur": "Rajasthan",
    "Jodhpur": "Rajasthan",
    "Udaipur": "Rajasthan",
    "Kota": "Rajasthan",

    # Uttar Pradesh
    "Kanpur": "Uttar Pradesh",
    "Lucknow": "Uttar Pradesh",
    "Agra": "Uttar Pradesh",
    "Noida": "Uttar Pradesh",
    "Varanasi": "Uttar Pradesh",
    "Ghaziabad": "Uttar Pradesh",

    # West Bengal
    "Kolkata": "West Bengal",
    "Howrah": "West Bengal",
    "Durgapur": "West Bengal",

    # Madhya Pradesh
    "Bhopal": "Madhya Pradesh",
    "Indore": "Madhya Pradesh",
    "Gwalior": "Madhya Pradesh",

    # Punjab
    "Amritsar": "Punjab",
    "Ludhiana": "Punjab",
    "Jalandhar": "Punjab",

    # Haryana
    "Gurugram": "Haryana",
    "Gurgaon": "Haryana",
    "Faridabad": "Haryana",
    "Panipat": "Haryana",

    # Bihar
    "Patna": "Bihar",

    # Odisha
    "Bhubaneswar": "Odisha",
    "Cuttack": "Odisha",

    # Assam
    "Guwahati": "Assam",

    # Kerala
    "Kochi": "Kerala",
    "Thiruvananthapuram": "Kerala",
    "Kozhikode": "Kerala",

    # Chhattisgarh
    "Raipur": "Chhattisgarh",

    # Jharkhand
    "Ranchi": "Jharkhand",

    # Goa
    "Panaji": "Goa"
}
logger = get_logger("transform")

# ---------------------------------------------------------
# File Paths
# ---------------------------------------------------------

LOCATIONS_CSV = DATA_RAW_DIR / "locations_with_state.csv"

MEASUREMENTS_CSV = DATA_RAW_DIR / "measurements_raw.csv"

OUTPUT_CSV = DATA_PROCESSED_DIR / "air_quality_cleaned.csv"

# ---------------------------------------------------------
# Load CSV Files
# ---------------------------------------------------------

def load_data():

    logger.info("Loading CSV files...")

    locations = pd.read_csv(LOCATIONS_CSV)

    measurements = pd.read_csv(MEASUREMENTS_CSV)

    logger.info(
        f"Locations : {len(locations)} | Measurements : {len(measurements)}"
    )

    return locations, measurements


# ---------------------------------------------------------
# Build Sensor -> Location Mapping
# ---------------------------------------------------------

def build_sensor_mapping(locations):

    logger.info("Building Sensor Mapping...")

    mapping = []

    for _, row in tqdm(
        locations.iterrows(),
        total=len(locations),
        desc="Mapping Sensors"
    ):

        location_id = row["location_id"]

        sensor_ids = str(row["sensor_ids"])

        if sensor_ids == "nan":
            continue

        sensors = sensor_ids.split(";")

        for sensor in sensors:

            sensor = sensor.strip()

            if sensor.isdigit():

                mapping.append({

                    "sensor_id": int(sensor),

                    "location_id": location_id

                })

    sensor_map = pd.DataFrame(mapping)

    logger.info(
        f"Sensor Mapping Created : {len(sensor_map)} rows"
    )
    print(sensor_map.head(20))
    print("Unique location_id:", sensor_map["location_id"].nunique())
    print("Unique sensor_id:", sensor_map["sensor_id"].nunique())
    return sensor_map


# ---------------------------------------------------------
# Attach Location ID into Measurements
# ---------------------------------------------------------

def attach_location_id(measurements, sensor_map):

    logger.info("Attaching Location IDs...")

    measurements = measurements.merge(

        sensor_map,

        on="sensor_id",

        how="left"

    )

    logger.info(

        f"Measurements after mapping : {len(measurements)}"

    )

    return measurements

# ---------------------------------------------------------
# Clean Locations
# ---------------------------------------------------------

def clean_locations(locations):

    logger.info("Cleaning Locations...")

    locations = locations.copy()

    # Remove duplicate locations
    locations.drop_duplicates(
        subset=["location_id"],
        inplace=True
    )

    # Clean text columns
    text_columns = [
        "location_name",
        "locality",
        "country_name",
        "provider_name",
        "timezone"
    ]

    for col in text_columns:

        if col in locations.columns:

            locations[col] = (
                locations[col]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
            )

    # Latitude & Longitude
    locations["latitude"] = pd.to_numeric(
        locations["latitude"],
        errors="coerce"
    )

    locations["longitude"] = pd.to_numeric(
        locations["longitude"],
        errors="coerce"
    )

    logger.info(
        f"Locations after cleaning : {len(locations)}"
    )

    return locations


# ---------------------------------------------------------
# Clean Measurements
# ---------------------------------------------------------

def clean_measurements(measurements):

    logger.info("Cleaning Measurements...")

    measurements = measurements.copy()

    measurements.drop_duplicates(inplace=True)

    measurements["value"] = pd.to_numeric(
        measurements["value"],
        errors="coerce"
    )

    measurements["coverage"] = pd.to_numeric(
        measurements["coverage"],
        errors="coerce"
    )

    measurements = measurements[
        measurements["value"].notna()
    ]

    measurements["datetime_utc"] = pd.to_datetime(
        measurements["datetime_utc"],
        errors="coerce"
    )

    measurements["datetime_local"] = pd.to_datetime(
        measurements["datetime_local"],
        errors="coerce"
    )

    logger.info(
        f"Measurements after cleaning : {len(measurements)}"
    )

    return measurements

# ---------------------------------------------------------
# Add State Column
# ---------------------------------------------------------
def add_state_column(locations):

    logger.info("Creating State Column using Reverse Geocoding...")

    locations = locations.copy()

    geolocator = Nominatim(user_agent="india_air_quality")
    reverse = RateLimiter(
        geolocator.reverse,
        min_delay_seconds=1
    )

    states = []

    for _, row in tqdm(
        locations.iterrows(),
        total=len(locations),
        desc="Finding States"
    ):

        lat = row["latitude"]
        lon = row["longitude"]

        try:

            if pd.isna(lat) or pd.isna(lon):
                states.append("Unknown")
                continue

            location = reverse(
                (lat, lon),
                language="en"
            )

            if location is None:
                states.append("Unknown")
                continue

            address = location.raw.get("address", {})

            state = address.get("state")

            if state is None:
                state = address.get("union_territory")

            if state is None:
                state = "Unknown"

            states.append(state)

        except Exception:

            states.append("Unknown")

    locations["state"] = states

    logger.info("State Column Created.")

    return locations
# ---------------------------------------------------------
# Merge Locations + Measurements
# ---------------------------------------------------------

def merge_data(locations, measurements):

    logger.info("Merging datasets...")

    df = measurements.merge(
        locations,
        on="location_id",
        how="left"
    )

    logger.info(f"Merged Records : {len(df)}")

    return df


# ---------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------

def create_features(df):

    logger.info("Creating Features...")

    df = df.copy()

    # Date Features
    df["year"] = df["datetime_local"].dt.year
    df["month"] = df["datetime_local"].dt.month
    df["day"] = df["datetime_local"].dt.day
    df["hour"] = df["datetime_local"].dt.hour

    # Month Name
    df["month_name"] = df["datetime_local"].dt.month_name()

    # Day Name
    df["day_name"] = df["datetime_local"].dt.day_name()

    # Weekend Flag
    df["is_weekend"] = (
        df["day_name"]
        .isin(["Saturday", "Sunday"])
        .astype(int)
    )

    logger.info("Feature Engineering Completed.")

    return df


# ---------------------------------------------------------
# Final Dataset
# ---------------------------------------------------------

def prepare_final_dataset(df):

    logger.info("Preparing Final Dataset...")

    required_columns = [

        "location_id",
        "location_name",
        "locality",
        "state",
        "country_name",

        "latitude",
        "longitude",

        "sensor_id",
        "parameter",
        "units",

        "value",
        "coverage",

        "datetime_utc",
        "datetime_local",

        "year",
        "month",
        "month_name",
        "day",
        "day_name",
        "hour",
        "is_weekend"

    ]

    # Keep only existing columns
    required_columns = [
        col for col in required_columns
        if col in df.columns
    ]

    df = df[required_columns]

    logger.info(
        f"Final Dataset Shape : {df.shape}"
    )

    return df
# ---------------------------------------------------------
# Save Dataset
# ---------------------------------------------------------

def save_dataset(df):

    logger.info("Saving Processed Dataset...")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8"
    )

    logger.info(f"Saved : {OUTPUT_CSV}")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    logger.info("=" * 60)
    logger.info("Starting Transform Stage")
    logger.info("=" * 60)

    try:

        # Load
        locations, measurements = load_data()

        # Clean
        locations = clean_locations(locations)
        measurements = clean_measurements(measurements)

        # Build Sensor Mapping
        sensor_map = build_sensor_mapping(locations)

        # Attach location_id into measurements
        measurements = attach_location_id(
            measurements,
            sensor_map
        )

        # Merge
        merged = merge_data(
            locations,
            measurements
        )

        # Features
        merged = create_features(merged)

        # Final Dataset
        final_df = prepare_final_dataset(merged)

        # Save
        save_dataset(final_df)

        logger.info("=" * 60)
        logger.info("Transform Completed Successfully")
        logger.info("=" * 60)

    except Exception as e:

        logger.exception(e)

        raise


if __name__ == "__main__":
    main()