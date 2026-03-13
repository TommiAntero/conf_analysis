# Peace Situational Awareness Dashboard

A conflict monitoring and early-warning dashboard combining statistical fatality forecasts with real-time news signals.

**Live app:** [conflictanalysisdemo.streamlit.app](https://conflictanalysisdemo.streamlit.app)

---

## What it does

The dashboard tracks 14 conflict-affected countries relevant to peace mediation work. It integrates two independent data sources to give both a forward-looking forecast and a current real-time signal.

### Tab 1 — VIEWS Forecast
Statistical conflict forecasts from the [VIEWS project](https://viewsforecasting.org) (Uppsala University & PRIO). Shows predicted battle-related deaths and the probability of exceeding the 25 BRD conflict threshold, per country per month, over a ~12-month horizon.

### Tab 2 — News Signal (GDELT)
Real-time conflict news signal from the [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/). Tracks news volume (article intensity) and tone (negative = more hostile coverage) for each country over the past 30–180 days.

### Tab 3 — Combined View
Scatter plot combining VIEWS fatality forecasts with GDELT conflict scores. Countries in the upper right have the highest combined risk signal.

---

## Data sources

| Source | What it measures | Update frequency |
|---|---|---|
| VIEWS fatalities003 | Predicted battle-related deaths (country-month) | Released monthly |
| GDELT DOC 2.0 | Conflict news volume and tone | Refreshed daily via GitHub Actions |

---

## Countries monitored

Sudan, Somalia, Ethiopia, Mali, Niger, Myanmar, Colombia, Yemen, Nigeria, Congo DRC, Mozambique, South Sudan, Afghanistan, Burkina Faso

---

## How to interpret

- **`main_mean`** — predicted fatalities per month (e.g. 500 = ~500 battle deaths expected)
- **`main_dich`** — probability of ≥25 battle-related deaths; values near 1.0 indicate near-certain active conflict
- **GDELT conflict score [0–1]** — composite of news volume (60%) and inverse tone (40%), normalised across countries; higher = stronger conflict signal in media
- **Combined view** — cross-referencing both sources helps identify countries where forecasts and current news signal align (higher confidence) vs. diverge (worth investigating)

### Caveats
- VIEWS forecasts continuity well but does not predict new conflict outbreaks
- GDELT reflects media attention, not events directly — well-covered conflicts score higher regardless of actual severity
- Neither source replaces ground-level situational awareness

---

## Technical setup

```
app.py                 Streamlit UI (3 tabs)
data_processor.py      VIEWS CSV loading and shaping
gdelt_fetcher.py       GDELT API calls + local JSON cache
refresh_gdelt.py       CI script for GitHub Actions
.github/workflows/     Daily cache refresh at 05:00 UTC
gdelt_cache.json       Cache file (auto-updated by Actions)
requirements.txt       Python dependencies
```

### Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Automated data refresh

GitHub Actions runs `refresh_gdelt.py` every morning at 05:00 UTC, fetches fresh GDELT data for all countries, and commits the updated `gdelt_cache.json` back to the repository. Streamlit Cloud picks up the new cache on the next app load.
