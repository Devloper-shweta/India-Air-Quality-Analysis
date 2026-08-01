"""
---------------------------------------------------------
add_state_to_locations.py

Purpose:
Add State column into locations_raw.csv

Input:
data/raw/locations_raw.csv

Output:
data/raw/locations_with_state.csv
---------------------------------------------------------
"""

import time
import requests
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "raw" / "locations_raw.csv"
OUTPUT_FILE = BASE_DIR / "data" / "raw" / "locations_with_state.csv"

print("Loading Locations...")

df = pd.read_csv(INPUT_FILE)

if "state" not in df.columns:
    df["state"] = None

headers = {
    "User-Agent": "India-Air-Quality-Analysis"
}

cache = {}

# ---------------------------------------------------------
# Manual Mapping
# ---------------------------------------------------------

mapping = {

    # Delhi
    "delhi":"Delhi",
    "new delhi":"Delhi",
    "dwarka":"Delhi",
    "rohini":"Delhi",
    "mandir marg":"Delhi",
    "r k puram":"Delhi",
    "rk puram":"Delhi",
    "punjabi bagh":"Delhi",
    "anand vihar":"Delhi",
    "lodhi road":"Delhi",
    "ito":"Delhi",
    "ashok vihar":"Delhi",
    "jahangirpuri":"Delhi",
    "okhla":"Delhi",
    "bawana":"Delhi",
    "najafgarh":"Delhi",
    "narela":"Delhi",
    "vasant kunj":"Delhi",
    "jnu":"Delhi",
    "iit delhi":"Delhi",
    "nsut":"Delhi",
    "dtu":"Delhi",
    "igi airport":"Delhi",

    # Maharashtra
    "mumbai":"Maharashtra",
    "navi mumbai":"Maharashtra",
    "thane":"Maharashtra",
    "pune":"Maharashtra",
    "nagpur":"Maharashtra",
    "nashik":"Maharashtra",

    # Telangana
    "hyderabad":"Telangana",

    # Karnataka
    "bangalore":"Karnataka",
    "bengaluru":"Karnataka",
    "mysuru":"Karnataka",

    # Tamil Nadu
    "chennai":"Tamil Nadu",
    "coimbatore":"Tamil Nadu",

    # West Bengal
    "kolkata":"West Bengal",

    # Rajasthan
    "jaipur":"Rajasthan",
    "jodhpur":"Rajasthan",
    "udaipur":"Rajasthan",

    # Uttar Pradesh
    "lucknow":"Uttar Pradesh",
    "kanpur":"Uttar Pradesh",
    "agra":"Uttar Pradesh",
    "varanasi":"Uttar Pradesh",
    "noida":"Uttar Pradesh",
    "ghaziabad":"Uttar Pradesh",

    # Bihar
    "patna":"Bihar",

    # Gujarat
    "ahmedabad":"Gujarat",
    "surat":"Gujarat",
    "vadodara":"Gujarat",

    # Madhya Pradesh
    "bhopal":"Madhya Pradesh",
    "indore":"Madhya Pradesh",

    # Odisha
    "bhubaneswar":"Odisha",

    # Andhra Pradesh
    "visakhapatnam":"Andhra Pradesh",
    "vijayawada":"Andhra Pradesh",

    # Kerala
    "kochi":"Kerala",
    "kochin":"Kerala",
    "thiruvananthapuram":"Kerala",

    # Assam
    "guwahati":"Assam",

    # Chandigarh
    "chandigarh":"Chandigarh",

    # Jammu & Kashmir
    "srinagar":"Jammu and Kashmir",
    "jammu":"Jammu and Kashmir",

    # Others
    "dehradun":"Uttarakhand",
    "ranchi":"Jharkhand",
    "shimla":"Himachal Pradesh",
    "itanagar":"Arunachal Pradesh",
    "imphal":"Manipur",
    "agartala":"Tripura",
    "aizawl":"Mizoram",
    "kohima":"Nagaland",
    "gangtok":"Sikkim",
    "port blair":"Andaman and Nicobar Islands",
    "leh":"Ladakh"
}

total = len(df)

for index, row in df.iterrows():

    current_state = str(row.get("state", "")).strip().lower()

    if current_state not in ["", "nan", "none", "unknown"]:
        continue

    location_name = str(row["location_name"]).lower()

    found = False

    for city, state in mapping.items():

        if city in location_name:
            df.at[index, "state"] = state
            found = True
            break

    if found:
        continue

    lat = row["latitude"]
    lon = row["longitude"]

    if pd.isna(lat) or pd.isna(lon):
        df.at[index, "state"] = "Unknown"
        continue

    key = (round(lat,5), round(lon,5))

    if key in cache:
        df.at[index, "state"] = cache[key]
        continue

    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?format=jsonv2"
        f"&lat={lat}"
        f"&lon={lon}"
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        if response.status_code == 200:

            address = response.json().get("address", {})

            state = (
                address.get("state")
                or address.get("union_territory")
                or address.get("state_district")
                or address.get("region")
                or "Unknown"
            )

        else:
            state = "Unknown"

    except Exception:
        state = "Unknown"

    cache[key] = state
    df.at[index, "state"] = state

    if (index + 1) % 20 == 0:
        print(f"{index+1}/{total} completed")

    time.sleep(1)

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8"
)

print("\nDone")
print("Saved:", OUTPUT_FILE)
print(df["state"].value_counts())