"""
Peace Situational Awareness Dashboard
Powered by VIEWS fatalities003 data + GDELT news signal

Run with:
    streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data_processor import (
    load_cm,
    filter_countries,
    top_n_countries,
    summary_table,
    to_dashboard_json,
    CMI_COUNTRIES,
    CM_FILE,
)
from gdelt_fetcher import fetch_all_signals, monthly_conflict_score

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Peace Situational Awareness",
    page_icon="🕊️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load VIEWS data (cached)
# ---------------------------------------------------------------------------
@st.cache_data
def get_views_data():
    return load_cm(CM_FILE)


# ---------------------------------------------------------------------------
# Load GDELT news signal (cached, TTL 6h)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=6 * 3600, show_spinner="Fetching GDELT news signal …")
def get_gdelt_data(countries: tuple, days_back: int = 90):
    raw = fetch_all_signals(list(countries), days_back=days_back)
    return raw, monthly_conflict_score(raw)


df_all = get_views_data()
months = sorted(df_all["month_id"].unique())
first_month = months[0]
last_month = months[-1]

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------
st.sidebar.title("Filters")

selected_countries = st.sidebar.multiselect(
    "Countries",
    options=sorted(df_all["country"].unique()),
    default=CMI_COUNTRIES,
)

month_range = st.sidebar.slider(
    "Forecast horizon (month_id)",
    min_value=int(first_month),
    max_value=int(last_month),
    value=(int(first_month), int(last_month)),
)

variable = st.sidebar.radio(
    "Variable",
    options=["main_mean", "main_dich"],
    format_func=lambda v: {
        "main_mean": "Predicted fatalities",
        "main_dich": "Probability ≥25 BRD",
    }[v],
)

st.sidebar.markdown("---")
st.sidebar.caption("Source: VIEWS fatalities003, Uppsala University & PRIO")

# ---------------------------------------------------------------------------
# Filter VIEWS data
# ---------------------------------------------------------------------------
df = df_all[
    df_all["country"].isin(selected_countries)
    & df_all["month_id"].between(month_range[0], month_range[1])
].copy()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_forecast, tab_news, tab_combined = st.tabs([
    "📊 VIEWS Forecast",
    "📰 News Signal (GDELT)",
    "🔀 Combined View",
])

# ===========================================================================
# TAB 1: VIEWS Forecast (original dashboard)
# ===========================================================================
with tab_forecast:
    st.title("🕊️ Peace Situational Awareness")
    st.caption(
        f"VIEWS fatalities003 · Country-month forecast · "
        f"Data as of January 2026 · Horizon: {df['label'].min()} → {df['label'].max()}"
    )

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    snapshot = df_all[df_all["month_id"] == first_month]
    top_country = snapshot.loc[snapshot["main_mean"].idxmax(), "country"]
    top_val = snapshot["main_mean"].max()
    high_risk = (snapshot["main_dich"] >= 0.95).sum()

    col1.metric("Countries monitored", len(selected_countries))
    col2.metric("Highest risk (Feb 2026)", top_country, f"{top_val:.0f} fatalities/month")
    col3.metric("Prob ≥95% (first month)", f"{high_risk} countries")
    col4.metric("Forecast horizon", f"{len(months)} months")

    st.divider()

    # Time-series chart
    st.subheader("Conflict fatality forecast — time series")
    pivot = df.pivot_table(index="label", columns="country", values=variable)
    fig_line = px.line(
        pivot,
        labels={
            "label": "",
            "value": "Predicted fatalities/month" if variable == "main_mean" else "Probability",
        },
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig_line.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig_line, width="stretch")

    # Snapshot bar charts
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Feb 2026 snapshot — predicted fatalities")
        snap = summary_table(df_all[df_all["country"].isin(selected_countries)])
        fig_bar = px.bar(
            snap.head(20),
            x="fatalities_forecast",
            y="country",
            orientation="h",
            color="fatalities_forecast",
            color_continuous_scale="Reds",
            labels={"fatalities_forecast": "Fatalities/month", "country": ""},
        )
        fig_bar.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_bar, width="stretch")

    with col_b:
        st.subheader("Probability of ≥25 battle-related deaths")
        snap_prob = snap.sort_values("prob_25brd", ascending=True).tail(20)
        fig_prob = px.bar(
            snap_prob,
            x="prob_25brd",
            y="country",
            orientation="h",
            color="prob_25brd",
            color_continuous_scale="RdYlGn_r",
            range_color=[0, 1],
            labels={"prob_25brd": "Probability", "country": ""},
        )
        fig_prob.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_prob, width="stretch")

    # Raw data
    with st.expander("Raw data table"):
        st.dataframe(
            df[["label", "country", "isoab", "main_mean", "main_mean_ln", "main_dich"]]
            .sort_values(["country", "label"])
            .reset_index(drop=True),
            width="stretch",
        )

    # Export
    st.divider()
    if st.button("Export dashboard JSON"):
        out_path = Path(__file__).parent / "dashboard_data.json"
        result = to_dashboard_json(df_all, countries=selected_countries, output_path=out_path)
        st.success(f"Saved {len(result)} countries → {out_path}")
        st.download_button(
            "Download JSON",
            data=json.dumps(result, indent=2),
            file_name="views_dashboard_data.json",
            mime="application/json",
        )

# ===========================================================================
# TAB 2: GDELT News Signal
# ===========================================================================
with tab_news:
    st.title("📰 GDELT Conflict News Signal")
    st.caption(
        "Real-time news conflict signal from GDELT DOC 2.0 · "
        "Volume = article intensity, Tone = avg sentiment (negative = worse) · "
        "Cached 6h"
    )

    days_back = st.select_slider(
            "Days of news history",
            options=[30, 60, 90, 120, 150, 180],
            value=180,
        )

    if not selected_countries:
        st.info("Select countries in the sidebar.")
    else:
        gdelt_raw, gdelt_monthly = get_gdelt_data(
            tuple(sorted(selected_countries)), days_back=days_back
        )

        if gdelt_raw.empty:
            st.warning(
                "No GDELT data returned. The API may be temporarily unavailable — try again in a few minutes."
            )
        else:
            # --- News volume timeline ---
            st.subheader("News conflict volume over time")
            fig_vol = px.line(
                gdelt_raw,
                x="date",
                y="volume",
                color="country",
                labels={"date": "", "volume": "Article intensity"},
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig_vol.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0),
                hovermode="x unified",
            )
            st.plotly_chart(fig_vol, width="stretch")

            # --- News tone timeline ---
            st.subheader("News tone over time (negative = more hostile coverage)")
            fig_tone = px.line(
                gdelt_raw,
                x="date",
                y="tone",
                color="country",
                labels={"date": "", "tone": "Average tone"},
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig_tone.add_hline(y=0, line_dash="dot", line_color="grey")
            fig_tone.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0),
                hovermode="x unified",
            )
            st.plotly_chart(fig_tone, width="stretch")

            # --- Monthly conflict score bar ---
            if not gdelt_monthly.empty:
                st.subheader("Monthly composite conflict score (latest month)")
                latest = gdelt_monthly[
                    (gdelt_monthly["year"] == gdelt_monthly["year"].max())
                ]
                latest = latest[latest["month"] == latest["month"].max()].sort_values(
                    "conflict_score", ascending=True
                )
                fig_score = px.bar(
                    latest,
                    x="conflict_score",
                    y="country",
                    orientation="h",
                    color="conflict_score",
                    color_continuous_scale="Reds",
                    range_color=[0, 1],
                    labels={"conflict_score": "Conflict score [0–1]", "country": ""},
                )
                fig_score.update_layout(
                    showlegend=False,
                    coloraxis_showscale=True,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig_score, width="stretch")

            with st.expander("Raw GDELT data"):
                st.dataframe(gdelt_raw.sort_values(["country", "date"]).reset_index(drop=True),
                             width="stretch")

# ===========================================================================
# TAB 3: Combined View — VIEWS forecast + GDELT signal
# ===========================================================================
with tab_combined:
    st.title("🔀 Combined Risk View")
    st.caption(
        "VIEWS fatalities forecast + GDELT news conflict score · "
        "Snapshot for the most recent overlapping month"
    )

    if not selected_countries:
        st.info("Select countries in the sidebar.")
    else:
        gdelt_raw_c, gdelt_monthly_c = get_gdelt_data(
            tuple(sorted(selected_countries)), days_back=90
        )

        if gdelt_monthly_c.empty:
            st.warning("GDELT data unavailable — run the News Signal tab first.")
        else:
            # Use VIEWS first-month snapshot
            views_snap = summary_table(df_all[df_all["country"].isin(selected_countries)])

            # Latest GDELT monthly scores
            latest_gdelt = gdelt_monthly_c[
                (gdelt_monthly_c["year"] == gdelt_monthly_c["year"].max())
            ]
            latest_gdelt = latest_gdelt[
                latest_gdelt["month"] == latest_gdelt["month"].max()
            ][["country", "conflict_score", "news_volume", "news_tone"]]

            # Merge
            combined = views_snap.merge(latest_gdelt, on="country", how="left")
            combined["conflict_score"] = combined["conflict_score"].fillna(0)

            # Normalise VIEWS fatalities to [0,1] for scatter
            fmax = combined["fatalities_forecast"].max()
            combined["fatalities_norm"] = combined["fatalities_forecast"] / fmax if fmax > 0 else 0

            st.subheader("Risk scatter: VIEWS fatalities vs GDELT news signal")
            st.caption("Top-right = highest combined risk")

            fig_scatter = px.scatter(
                combined,
                x="conflict_score",
                y="fatalities_forecast",
                text="country",
                color="prob_25brd",
                size="fatalities_forecast",
                size_max=50,
                color_continuous_scale="Reds",
                range_color=[0, 1],
                labels={
                    "conflict_score": "GDELT conflict score [0–1]",
                    "fatalities_forecast": "VIEWS predicted fatalities",
                    "prob_25brd": "Prob ≥25 BRD",
                },
            )
            fig_scatter.update_traces(textposition="top center")
            fig_scatter.update_layout(margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_scatter, width="stretch")

            st.subheader("Combined risk table")
            display = combined[[
                "country", "fatalities_forecast", "prob_25brd",
                "conflict_score", "news_volume", "news_tone",
            ]].sort_values("fatalities_forecast", ascending=False).reset_index(drop=True)
            display.columns = [
                "Country", "VIEWS fatalities", "Prob ≥25 BRD",
                "GDELT score", "News volume", "News tone",
            ]
            st.dataframe(display, width="stretch")
