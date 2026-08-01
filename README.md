# 🇮🇳 India Air Quality Analysis — End-to-End Data Engineering & Analytics Project

An end-to-end **Data Engineering + Data Analytics** pipeline that extracts real-time and historical
air quality data for India from the **OpenAQ API v3**, transforms and cleans it with **Python/Pandas**,
loads it into a **PostgreSQL** data warehouse, and visualizes insights through an interactive
**Power BI** dashboard.

This project demonstrates a production-style ETL workflow: API extraction with pagination, rate-limit
handling and retries, data cleaning and normalization, relational schema design, SQL analytics, and
BI dashboarding — the full lifecycle a Data Engineer / Analyst is expected to own.

---

## 📌 Project Architecture

```
                ┌─────────────────┐
                │   OpenAQ API v3   │
                │  (India stations) │
                └────────┬─────────┘
                         │  Extract (requests + retry + pagination)
                         ▼
                ┌─────────────────┐
                │   data/raw/       │  ← raw JSON + raw CSV (immutable landing zone)
                └────────┬─────────┘
                         │  Transform (pandas: clean, dedupe, normalize)
                         ▼
                ┌─────────────────┐
                │ data/processed/   │  ← cleaned, analysis-ready CSV
                └────────┬─────────┘
                         │  Load (psycopg2 / SQLAlchemy, bulk insert)
                         ▼
                ┌─────────────────┐
                │   PostgreSQL 17   │  ← star-schema style relational tables
                └────────┬─────────┘
                         │  SQL Analysis (views, aggregations)
                         ▼
                ┌─────────────────┐
                │     Power BI       │  ← KPI cards, trends, maps, drill-through
                └─────────────────┘
```

---

## 🧰 Tech Stack

| Layer            | Technology                          |
|-------------------|--------------------------------------|
| Language           | Python 3.13                          |
| API Source         | OpenAQ API v3                        |
| HTTP / Retry       | `requests`, `urllib3`                |
| Data Processing    | `pandas`, `numpy`                    |
| Database           | PostgreSQL 17                        |
| DB Driver / ORM    | `psycopg2`, `SQLAlchemy`             |
| Secrets Management | `python-dotenv` (`.env`)             |
| Visualization      | Power BI Desktop                     |
| IDE / VCS          | VS Code, Git                         |

---

## 📁 Project Structure

```
India-Air-Quality-Analysis/
│
├── data/
│   ├── raw/                     # Raw JSON & CSV pulled directly from OpenAQ API
│   ├── processed/                # Cleaned, transformed, analysis-ready CSV
│
├── scripts/
│   ├── extract_locations.py       # Fetch India monitoring station locations
│   ├── extract_sensors.py         # Fetch sensor metadata per location
│   ├── extract_measurements.py    # Fetch pollutant measurements per sensor
│   ├── transform.py               # Clean, normalize, and merge raw data
│   ├── load.py                    # Load processed data into PostgreSQL
│
├── sql/
│   ├── create_tables.sql          # DDL — schema & table definitions
│   ├── analysis_queries.sql       # Analytical SQL queries for insights
│
├── dashboard/                    # Power BI (.pbix) dashboard file
│
├── notebooks/                    # Exploratory Data Analysis (EDA) notebooks
│
├── .env                          # DB credentials & API config (NOT committed to Git)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🌐 Data Source: OpenAQ API v3

[OpenAQ](https://openaq.org) aggregates real-time and historical air quality measurements from
government and research-grade monitoring stations worldwide. This project uses API v3 endpoints to
pull **India-only** data:

- `GET /v3/locations` — monitoring station locations (filtered by `countries_id` = India)
- `GET /v3/locations/{id}/sensors` — sensors attached to each location (PM2.5, PM10, NO₂, SO₂, CO, O₃, etc.)
- `GET /v3/sensors/{id}/measurements` — time-series pollutant measurement values

> An OpenAQ API key is required. Register free at https://explore.openaq.org/register and generate
> a key from your account dashboard.

---

## ⚙️ Setup Instructions

### 1. Clone & create a virtual environment
```bash
git clone <your-repo-url>
cd India-Air-Quality-Analysis
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the project root (never commit this file):
```ini
# OpenAQ API
OPENAQ_API_KEY=your_openaq_api_key_here
OPENAQ_BASE_URL=https://api.openaq.org/v3

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=air_quality_db
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 4. Create the PostgreSQL database
```sql
CREATE DATABASE air_quality_db;
```

---

## ▶️ Running the Pipeline

Run each stage in order from the project root:

```bash
# 1. Extract India monitoring locations
python scripts/extract_locations.py

# 2. Extract sensors for each location
python scripts/extract_sensors.py

# 3. Extract pollutant measurements for each sensor
python scripts/extract_measurements.py

# 4. Transform & clean the raw data
python scripts/transform.py

# 5. Create tables & load processed data into PostgreSQL
python scripts/load.py
```

Then open `sql/analysis_queries.sql` in your SQL client (pgAdmin / DBeaver / psql) to explore
the analytical queries, and open `dashboard/India_Air_Quality.pbix` in Power BI, pointing its
PostgreSQL connector at your local `air_quality_db`.

*(Full step-by-step run instructions with troubleshooting are provided again at the end of this
build, once all scripts are generated.)*

---

## 📊 Power BI Dashboard Features

- KPI Cards — Avg PM2.5, Avg PM10, Total Monitoring Stations, Most Polluted City
- AQI Trend over time (daily/monthly)
- PM2.5 & PM10 deep-dive analysis
- Pollutant distribution by type
- State-wise India map (choropleth)
- City-wise pollution ranking
- Date range filters & slicers (state, city, pollutant)
- Drill-through from state → city → station-level detail

---

## 📈 Key Analytical Questions Answered

- Which Indian cities have the worst air quality?
- What is the average PM2.5 concentration by state?
- How do pollutant levels trend over time (daily/monthly/seasonal)?
- Which monitoring locations report the highest pollution levels?
- How does pollution vary by pollutant type across regions?

---

## 🔒 Data Engineering Best Practices Applied

- ✅ Secrets managed via `.env` — never hardcoded
- ✅ Modular, single-responsibility scripts
- ✅ Retry logic with exponential backoff for API resilience
- ✅ Rate-limit handling for OpenAQ API
- ✅ Raw vs. processed data separation (bronze/silver pattern)
- ✅ Idempotent, re-runnable load logic (upsert-safe)
- ✅ Structured logging across every script
- ✅ PEP8-compliant, documented, exception-safe code

---

## 👤 Author

Built as a portfolio project to demonstrate end-to-end Data Engineering and Analytics skills:
API integration, ETL pipeline design, SQL data modeling, and BI storytelling.

---

## 📄 License

This project uses publicly available data from [OpenAQ](https://openaq.org) under its open data
license. Code in this repository is provided for educational/portfolio purposes.
