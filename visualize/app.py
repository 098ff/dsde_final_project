"""
Election Insights Dashboard — Streamlit entry point.

Three tabs:
  1. Vote Buying (การซื้อเสียง)  — small-party analysis + suspect polling stations
  2. Outlier Detection           — Z-score anomaly detection on vote ratios
  3. Bhumjaithai Loyalty         — geographic loyalty ratio map

Run with:
    streamlit run visualize/app.py
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Election Insights",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Imports (after set_page_config)
# ---------------------------------------------------------------------------

from data_loader import (  # noqa: E402
    load_bhumjaithai_ratio,
    load_geo_dataframe,
    load_merged_parties,
    load_small_party,
    load_suspect,
)
from tabs.loyalty_map import render_loyalty_tab  # noqa: E402
from tabs.outliers import render_outliers_tab  # noqa: E402
from tabs.vote_buying import render_vote_buying_tab  # noqa: E402

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

small_df = load_small_party()
suspect_df = load_suspect()
merged_df = load_merged_parties()
ratio_df = load_bhumjaithai_ratio()
geo_df = load_geo_dataframe()

# ---------------------------------------------------------------------------
# App header
# ---------------------------------------------------------------------------

st.title("Thai Election 2026 — Insights Dashboard")
st.markdown(
    """
    **Data source:** OCR-validated ballot data from the 2026 Thai general election.
    This dashboard presents three analytical insights derived from the validation pipeline.
    """
)

st.divider()

# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------

tab_vote, tab_outlier, tab_loyalty = st.tabs(
    [
        "Vote Buying (การซื้อเสียง)",
        "Outlier Detection",
        "Bhumjaithai Loyalty",
    ]
)

with tab_vote:
    render_vote_buying_tab(small_df, suspect_df, geo_df)

with tab_outlier:
    render_outliers_tab(merged_df)

with tab_loyalty:
    render_loyalty_tab(ratio_df, geo_df)
