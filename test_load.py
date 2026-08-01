import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.load import load_csv, prepare_dataframe_for_insert


def test_load_csv_converts_weekend_flag_to_boolean(monkeypatch):
    sample_csv = """location_id,location_name,locality,state,country_name,latitude,longitude,sensor_id,parameter,units,value,coverage,datetime_utc,datetime_local,is_weekend
1,Test,Local,TestState,TestCountry,12.34,56.78,10,pm25,ug/m3,4.5,1.0,2024-01-01T00:00:00Z,2024-01-01T05:30:00+05:30,1
"""

    tmp_path = Path("/tmp/test_air_quality.csv")
    tmp_path.write_text(sample_csv, encoding="utf-8")

    monkeypatch.setattr("scripts.load.PROCESSED_CSV", tmp_path)

    df = load_csv()
    prepared = prepare_dataframe_for_insert(df)

    assert prepared["datetime_utc"].dtype.kind in {"M", "m"}
    assert prepared["datetime_local"].dtype.kind in {"M", "m"}
    assert prepared["is_weekend"].tolist() == [True]
