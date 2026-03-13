"""
VIEWS fatalities003 — data processing module
Handles loading, filtering and shaping CM (country-month) data for the dashboard.
"""

import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
CM_FILE = DATA_DIR / "fatalities003_2026_01_t01_cm.csv"
PGM_FILE = DATA_DIR / "fatalities003_2026_01_t01_pgm.csv"

# CMI-relevant focus countries (edit freely)
CMI_COUNTRIES = [
    "Sudan", "Somalia", "Ethiopia", "Mali", "Niger",
    "Myanmar", "Colombia", "Yemen", "Nigeria", "Congo, DRC",
    "Mozambique", "South Sudan", "Afghanistan", "Burkina Faso",
]


def load_cm(path: Path = CM_FILE) -> pd.DataFrame:
    """Load country-month CSV and return a clean DataFrame."""
    df = pd.read_csv(path)
    # Add a human-readable label column  e.g. "2026-02"
    df["label"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    return df


def load_pgm(path: Path = PGM_FILE) -> pd.DataFrame:
    """Load PRIO-GRID-month CSV (sub-national level)."""
    return pd.read_csv(path)


def filter_countries(df: pd.DataFrame, countries: list[str] = CMI_COUNTRIES) -> pd.DataFrame:
    """Return rows for the selected countries only."""
    return df[df["country"].isin(countries)].copy()


def top_n_countries(df: pd.DataFrame, n: int = 20, month_id: int | None = None) -> pd.DataFrame:
    """Return the N countries with the highest fatality forecast.
    
    If month_id is None, uses the first available month.
    """
    if month_id is None:
        month_id = int(df["month_id"].min())
    subset = df[df["month_id"] == month_id].copy()
    return subset.nlargest(n, "main_mean")


def pivot_timeseries(df: pd.DataFrame, value_col: str = "main_mean") -> pd.DataFrame:
    """Pivot to wide format: index=label, columns=country, values=value_col."""
    return df.pivot(index="label", columns="country", values=value_col)


def to_dashboard_json(
    df: pd.DataFrame,
    countries: list[str] = CMI_COUNTRIES,
    output_path: Path | None = None,
) -> dict:
    """Build a JSON-serialisable dict ready for the dashboard.

    Structure:
        {
          "CountryName": [
            {"label": "2026-02", "fatalities": 355.1, "prob": 1.0},
            ...
          ],
          ...
        }
    """
    filtered = filter_countries(df, countries)
    months = sorted(filtered["month_id"].unique())
    result = {}

    for country in countries:
        country_df = filtered[filtered["country"] == country].copy()
        country_df = country_df.set_index("month_id")
        series = []
        for m in months:
            if m in country_df.index:
                row = country_df.loc[m]
                series.append({
                    "label": str(row["label"]),
                    "fatalities": round(float(row["main_mean"]), 1),
                    "prob": round(float(row["main_dich"]), 3),
                })
        if series:
            result[country] = series

    if output_path:
        output_path.write_text(json.dumps(result, indent=2))
        print(f"Saved → {output_path}")

    return result


def summary_table(df: pd.DataFrame, month_id: int | None = None) -> pd.DataFrame:
    """Quick summary: country, fatalities, prob for a given month."""
    if month_id is None:
        month_id = int(df["month_id"].min())
    subset = df[df["month_id"] == month_id][["country", "isoab", "main_mean", "main_dich"]].copy()
    subset = subset.rename(columns={"main_mean": "fatalities_forecast", "main_dich": "prob_25brd"})
    return subset.sort_values("fatalities_forecast", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    df = load_cm()
    print(f"Loaded {len(df)} rows, {df['country'].nunique()} countries, "
          f"months {df['month_id'].min()}–{df['month_id'].max()}")

    print("\nTop 10 countries (first forecast month):")
    print(top_n_countries(df, n=10).to_string(index=False, columns=["country","isoab","year","month","main_mean","main_dich"]))

    print("\nExporting dashboard JSON …")
    out = Path(__file__).parent.parent / "data" / "dashboard_data.json"
    to_dashboard_json(df, output_path=out)
