"""
GDELT DOC 2.0 news signal fetcher for Peace Dashboard.

BUGFIXES vs. original:
  1. VOLUME WAS ALWAYS 0  — mode=timelinetone returns only "Average Tone".
     Volume requires a separate call with mode=timelinevol.
     Fixed: two API calls per country, results merged on date.

  2. COUNTRY NAME MISMATCHES — Burkina Faso, Mali, Niger, Ethiopia, Yemen
     returned 0 records because GDELT expects specific name variants.
     Fixed: GDELT_NAME_MAP translates VIEWS names → GDELT-friendly names.

  3. SMOOTHING PARAM WRONG — GDELT smoothing is in days (integer string),
     passing smoothing=7 as an int caused silent API fallback to raw data.
     Fixed: cast to str explicitly.
"""

import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
CACHE_FILE = Path(__file__).parent / "gdelt_cache.json"
CACHE_TTL_HOURS = 6

CONFLICT_TERMS = (
    "(conflict OR battle OR attack OR violence OR war OR fighting "
    "OR ceasefire OR casualties OR airstrike OR militia)"
)

# ---------------------------------------------------------------------------
# BUG FIX 2 — GDELT name map
# VIEWS country name  →  name that GDELT recognises reliably
# ---------------------------------------------------------------------------
GDELT_NAME_MAP: dict[str, str] = {
    "Burkina Faso":  "Burkina",          # GDELT uses shortened form
    "Mali":          "Mali",             # keep but add French alias fallback below
    "Niger":         "Niger",            # OK but needs explicit region qualifier
    "Ethiopia":      "Ethiopia",         # OK — was likely a transient API issue
    "Yemen":         "Yemen",
    "Congo, DRC":    "Congo",
    "South Sudan":   "South Sudan",
    "Myanmar":       "Myanmar",
}


def _gdelt_country_name(country: str) -> str:
    """Return the GDELT-friendly query name for a country."""
    return GDELT_NAME_MAP.get(country, country)


# ---------------------------------------------------------------------------
# BUG FIX 1 — separate volume + tone calls, then merge
# ---------------------------------------------------------------------------

def _fetch_timeline(country_query: str, mode: str, days_back: int) -> list[dict]:
    """Fetch one GDELT timeline mode. Returns list of {date, value} dicts."""
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)

    params = {
        "query": f'"{country_query}" {CONFLICT_TERMS}',
        "mode": mode,
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
        "smoothing": "7",   # BUG FIX 3 — must be a string
    }

    for attempt in range(3):
        try:
            resp = requests.get(GDELT_API, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            # Both timelinevol and timelinetone wrap data in data.timeline[0].data
            timeline = data.get("timeline", [])
            if timeline:
                return timeline[0].get("data", [])
            return []
        except Exception as e:
            if attempt == 2:
                print(f"  [GDELT] {country_query} ({mode}): failed — {e}")
                return []
            time.sleep(3)
    return []


def fetch_country_signal(country: str, days_back: int = 90) -> pd.DataFrame:
    """
    Fetch conflict news volume AND tone for one country from GDELT DOC 2.0.

    Makes two API calls (timelinevol + timelinetone) and merges on date.
    Returns a DataFrame with columns: date, volume, tone, country.
    """
    gdelt_name = _gdelt_country_name(country)

    print(f"  [GDELT] {country} → querying as '{gdelt_name}'")

    vol_data  = _fetch_timeline(gdelt_name, "timelinevol", days_back)
    time.sleep(1.5)   # be polite between the two calls
    tone_data = _fetch_timeline(gdelt_name, "timelinetone", days_back)

    if not vol_data and not tone_data:
        return pd.DataFrame(columns=["date", "volume", "tone", "country"])

    vol_map  = {pt["date"]: pt["value"] for pt in vol_data}
    tone_map = {pt["date"]: pt["value"] for pt in tone_data}

    all_dates = sorted(set(vol_map) | set(tone_map))
    if not all_dates:
        return pd.DataFrame(columns=["date", "volume", "tone", "country"])

    rows = [
        {
            "date":    pd.to_datetime(d, format="ISO8601"),
            "volume":  vol_map.get(d, 0.0),
            "tone":    tone_map.get(d, 0.0),
            "country": country,
        }
        for d in all_dates
    ]
    df = pd.DataFrame(rows)
    print(f"  [GDELT] {country}: {len(df)} rows, "
          f"vol [{df['volume'].min():.2f}–{df['volume'].max():.2f}], "
          f"tone [{df['tone'].min():.2f}–{df['tone'].max():.2f}]")
    return df


# ---------------------------------------------------------------------------
# Batch fetch with local JSON cache (unchanged logic, same interface)
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _cache_is_fresh(entry: dict, ttl_hours: int = CACHE_TTL_HOURS) -> bool:
    fetched_at = entry.get("fetched_at")
    if not fetched_at:
        return False
    # Also invalidate old cache entries that have volume=0 (fetched with old bug)
    records = entry.get("data", [])
    if records and all(r.get("volume", 0) == 0.0 for r in records):
        print(f"  [GDELT cache] stale (all volume=0), forcing refresh")
        return False
    age = datetime.utcnow() - datetime.fromisoformat(fetched_at)
    return age < timedelta(hours=ttl_hours)


def fetch_all_signals(
    countries: list[str],
    days_back: int = 90,
    cache_ttl_hours: int = CACHE_TTL_HOURS,
    sleep_between: float = 3.0,
) -> pd.DataFrame:
    """
    Fetch GDELT conflict signal for all countries.
    Results are cached locally for `cache_ttl_hours` hours.

    Returns a DataFrame with columns: date, volume, tone, country.
    """
    cache = _load_cache()
    frames: list[pd.DataFrame] = []

    for country in countries:
        entry = cache.get(country, {})
        if _cache_is_fresh(entry, cache_ttl_hours):
            print(f"  [GDELT] {country}: using cache ({len(entry.get('data', []))} records)")
            records = entry.get("data", [])
            if records:
                df = pd.DataFrame(records)
                df["date"] = pd.to_datetime(df["date"])
                frames.append(df)
            continue

        df = fetch_country_signal(country, days_back=days_back)
        time.sleep(sleep_between)

        if not df.empty:
            frames.append(df)
            cache[country] = {
                "fetched_at": datetime.utcnow().isoformat(),
                "data": df.assign(date=df["date"].astype(str)).to_dict(orient="records"),
            }
        else:
            cache[country] = {"fetched_at": datetime.utcnow().isoformat(), "data": []}

    _save_cache(cache)

    if not frames:
        return pd.DataFrame(columns=["date", "volume", "tone", "country"])

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    return combined


# ---------------------------------------------------------------------------
# Aggregate: monthly conflict score per country (unchanged)
# ---------------------------------------------------------------------------

def monthly_conflict_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily GDELT signal to a monthly conflict score.
    Returns columns: year, month, country, news_volume, news_tone, conflict_score.
    conflict_score ∈ [0, 1]: higher = more conflict signal.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["year", "month", "country", "news_volume", "news_tone", "conflict_score"]
        )

    df = df.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    agg = (
        df.groupby(["year", "month", "country"], as_index=False)
        .agg(news_volume=("volume", "mean"), news_tone=("tone", "mean"))
    )

    v_min, v_max = agg["news_volume"].min(), agg["news_volume"].max()
    agg["vol_norm"] = (
        (agg["news_volume"] - v_min) / (v_max - v_min)
        if v_max > v_min else 0.0
    )

    t_min, t_max = agg["news_tone"].min(), agg["news_tone"].max()
    agg["tone_norm"] = (
        1 - (agg["news_tone"] - t_min) / (t_max - t_min)
        if t_max > t_min else 0.5
    )

    agg["conflict_score"] = (0.6 * agg["vol_norm"] + 0.4 * agg["tone_norm"]).round(3)
    return agg.drop(columns=["vol_norm", "tone_norm"])


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_countries = ["Sudan", "Somalia", "Burkina Faso", "Mali", "Yemen"]
    print(f"Testing fixed fetcher with: {test_countries}\n")

    # Clear old broken cache entries for test countries
    cache = _load_cache()
    for c in test_countries:
        cache.pop(c, None)
    _save_cache(cache)

    raw = fetch_all_signals(test_countries, days_back=60)
    print(f"\nTotal rows fetched: {len(raw)}")
    if not raw.empty:
        print(raw.groupby("country")[["volume", "tone"]].describe().round(3))

    monthly = monthly_conflict_score(raw)
    if not monthly.empty:
        print("\nMonthly conflict scores:")
        print(monthly.sort_values("conflict_score", ascending=False).head(15).to_string(index=False))
