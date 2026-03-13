"""
CI script: fetch GDELT signals for all CMI countries and save to cache.
Run by GitHub Actions every morning. No Streamlit dependency.
"""

from gdelt_fetcher import fetch_all_signals, CACHE_FILE
from data_processor import CMI_COUNTRIES

print(f"Refreshing GDELT cache for {len(CMI_COUNTRIES)} countries …\n")

# Force fresh fetch by clearing cache first
if CACHE_FILE.exists():
    CACHE_FILE.unlink()
    print("Cleared old cache.\n")

raw = fetch_all_signals(CMI_COUNTRIES, days_back=90)

print(f"\nDone. {len(raw)} rows fetched for {raw['country'].nunique()} countries.")
print(f"Cache saved to: {CACHE_FILE}")
