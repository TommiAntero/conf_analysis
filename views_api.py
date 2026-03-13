"""
VIEWS REST API client
Fetches live forecasts directly from viewsforecasting.org
Docs: https://viewsforecasting.org/data/

Usage:
    client = ViewsAPIClient()
    df = client.get_cm_forecast(release="fatalities003", steps=[1, 6, 12])
"""

import requests
import pandas as pd
from io import StringIO
from typing import Optional


BASE_URL = "https://api.viewsforecasting.org"

# Known model / release names
MODELS = {
    "fatalities003": "fatalities003",   # current production model (Dec 2025 →)
    "fatalities002": "fatalities002",   # retired Dec 2025
}

# Available variables
VARIABLES = {
    "main_mean":    "Predicted fatalities (natural scale)",
    "main_mean_ln": "Predicted fatalities (log scale)",
    "main_dich":    "Probability of ≥25 BRDs (cm) / ≥1 BRD (pgm)",
}


class ViewsAPIClient:
    """Thin wrapper around the VIEWS REST API."""

    def __init__(self, base_url: str = BASE_URL, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_cm_forecast(
        self,
        release: str = "fatalities003",
        step: int = 1,
        variables: list[str] = ("main_mean", "main_dich"),
    ) -> pd.DataFrame:
        """Fetch country-month forecast for a single step-ahead.

        Args:
            release:   Model release name, e.g. "fatalities003"
            step:      Steps ahead (1 = next month, 36 = 3 years out)
            variables: List of output variable names to retrieve

        Returns:
            DataFrame with columns: country_id, month_id, isoab, + requested variables
        """
        endpoint = f"{self.base_url}/{release}/cm/predictions/step{step:03d}/"
        params = {"vars": ",".join(variables), "format": "csv"}
        return self._fetch_csv(endpoint, params)

    def get_pgm_forecast(
        self,
        release: str = "fatalities003",
        step: int = 1,
        variables: list[str] = ("main_mean", "main_dich"),
    ) -> pd.DataFrame:
        """Fetch PRIO-GRID-month (sub-national) forecast for a single step."""
        endpoint = f"{self.base_url}/{release}/pgm/predictions/step{step:03d}/"
        params = {"vars": ",".join(variables), "format": "csv"}
        return self._fetch_csv(endpoint, params)

    def get_latest_release_info(self) -> dict:
        """Return metadata about available releases."""
        resp = self.session.get(f"{self.base_url}/", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Multi-step helper
    # ------------------------------------------------------------------

    def get_cm_multistep(
        self,
        release: str = "fatalities003",
        steps: list[int] = list(range(1, 37)),
        variables: list[str] = ("main_mean", "main_dich"),
    ) -> pd.DataFrame:
        """Fetch and concatenate forecasts for multiple steps ahead.

        Returns a long-format DataFrame with an extra 'step' column.
        """
        frames = []
        for step in steps:
            try:
                df = self.get_cm_forecast(release=release, step=step, variables=variables)
                df["step"] = step
                frames.append(df)
                print(f"  step {step:02d} ✓  ({len(df)} rows)")
            except Exception as exc:
                print(f"  step {step:02d} ✗  {exc}")
        if not frames:
            raise RuntimeError("No data retrieved from API")
        return pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_csv(self, url: str, params: dict) -> pd.DataFrame:
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return pd.read_csv(StringIO(resp.text))


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    client = ViewsAPIClient()

    print("Fetching fatalities003 step-1 country-month forecast …")
    try:
        df = client.get_cm_forecast(step=1)
        print(df.head())
        print(f"\nShape: {df.shape}")
    except Exception as e:
        print(f"API request failed: {e}")
        print("(Run this when connected to the internet)")
