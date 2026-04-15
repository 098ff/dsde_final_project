"""
Streamlit Manual Review Queue
Visualises the 242 records from master_summary_log.csv that require manual
inspection, grouped hierarchically by tambon -> unit with flag breakdowns,
sidebar filters, and a flag-count bar chart summary.

Run with:
    streamlit run election_pipeline/validation/notebooks/streamlit_manual_review.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.express as px

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import altair as alt

    HAS_ALTAIR = True
except ImportError:
    HAS_ALTAIR = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CSV_PATH = Path(__file__).parent.parent.parent / "output_data" / "master_summary_log.csv"

_ALL_FLAG_COLS = [
    "flag_math_total_used",
    "flag_math_valid_score",
    "flag_name_mismatch",
    "flag_missing_counterpart",
    "flag_missing_data",
    "flag_linguistic_mismatch",
]


def _pretty_flag(col: str) -> str:
    """Return human-readable label for a flag column name."""
    return col.replace("flag_", "").replace("_", " ").title()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data
def load_data() -> tuple[pd.DataFrame, list[str]]:
    """Load and prepare the master summary CSV."""
    if not CSV_PATH.exists():
        return pd.DataFrame(), []

    df = pd.read_csv(CSV_PATH)

    # Only keep flag columns that actually exist in this CSV
    flag_cols = [c for c in _ALL_FLAG_COLS if c in df.columns]

    # Coerce NaN -> False so we never emit false positives
    for col in flag_cols:
        df[col] = df[col].fillna(False).astype(bool)

    df["flag_count"] = df[flag_cols].sum(axis=1)

    return df, flag_cols


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Manual Review Queue", layout="wide")


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

if not CSV_PATH.exists():
    st.error(f"CSV not found at {CSV_PATH}")
    st.stop()

df_full, FLAG_COLS = load_data()

if df_full.empty:
    st.error(f"CSV not found or is empty at {CSV_PATH}")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------

st.sidebar.header("Filters")

all_tambons: list[str] = sorted(df_full["tambon"].dropna().unique().tolist())
selected_tambons: list[str] = st.sidebar.multiselect(
    "Tambon (ตำบล)",
    options=all_tambons,
    default=all_tambons,
    help="Filter by sub-district",
)

all_types: list[str] = ["บัญชีรายชื่อ", "แบ่งเขต"]
selected_types: list[str] = st.sidebar.multiselect(
    "Type (ประเภท)",
    options=all_types,
    default=all_types,
    help="Filter by ballot type",
)

flag_labels: dict[str, str] = {col: _pretty_flag(col) for col in FLAG_COLS}
selected_flag_cols: list[str] = st.sidebar.multiselect(
    "Active flags (ธง)",
    options=FLAG_COLS,
    default=[],
    format_func=lambda col: flag_labels[col],
    help="Show only rows where ALL selected flags are True",
)

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------

df = df_full.copy()

if selected_tambons:
    df = df[df["tambon"].isin(selected_tambons)]

if selected_types:
    df = df[df["type"].isin(selected_types)]

if selected_flag_cols:
    mask = df[selected_flag_cols].all(axis=1)
    df = df[mask]

# ---------------------------------------------------------------------------
# Section 1 — Hierarchical review queue
# ---------------------------------------------------------------------------

st.header("Manual Review Queue")
st.caption(
    f"Showing **{len(df)}** of {len(df_full)} records "
    f"| {int(df['flag_count'].sum())} total flag hits"
)

if df.empty:
    st.info("No records match the current filters.")
else:
    display_cols = ["type", "flag_count"] + FLAG_COLS + ["details"]

    # Build column_config for st.dataframe
    col_config: dict = {
        "type": st.column_config.TextColumn("Type"),
        "flag_count": st.column_config.NumberColumn("# Flags", format="%d"),
        "details": st.column_config.TextColumn("Details", width="large"),
    }
    for col in FLAG_COLS:
        col_config[col] = st.column_config.CheckboxColumn(
            _pretty_flag(col),
            help=f"Flag: {col}",
        )

    for tambon, tambon_df in df.groupby("tambon", sort=True):
        st.subheader(f"ตำบล {tambon}")

        for unit, unit_df in tambon_df.groupby("unit", sort=True):
            record_count = len(unit_df)
            flag_hits = int(unit_df["flag_count"].sum())
            st.markdown(f"**หน่วยเลือกตั้ง {unit}**")
            st.caption(f"{record_count} records | {flag_hits} flag hits")

            table_df = unit_df[display_cols].reset_index(drop=True)
            st.dataframe(
                table_df,
                column_config=col_config,
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

# ---------------------------------------------------------------------------
# Section 2 — Flag summary
# ---------------------------------------------------------------------------

st.header("Flag Summary")
st.caption("Counts computed from the **full** dataset (all 242 records, ignoring filters above).")

# Per-flag counts from the unfiltered dataframe
flag_counts = {col: int(df_full[col].sum()) for col in FLAG_COLS}
flag_summary_df = pd.DataFrame(
    {
        "flag": list(flag_counts.keys()),
        "label": [_pretty_flag(c) for c in flag_counts.keys()],
        "count": list(flag_counts.values()),
    }
).sort_values("count", ascending=True)

if HAS_PLOTLY:
    fig = px.bar(
        flag_summary_df,
        x="count",
        y="label",
        orientation="h",
        title="Records per Flag (full dataset)",
        labels={"count": "Record count", "label": "Flag"},
        color="count",
        color_continuous_scale="Blues",
        text="count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        height=350,
        margin=dict(l=20, r=40, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

elif HAS_ALTAIR:
    chart = (
        alt.Chart(flag_summary_df)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Record count"),
            y=alt.Y("label:N", sort="-x", title="Flag"),
            color=alt.Color("count:Q", scale=alt.Scale(scheme="blues"), legend=None),
            tooltip=["label:N", "count:Q"],
        )
        .properties(title="Records per Flag (full dataset)", height=300)
    )
    st.altair_chart(chart, use_container_width=True)

else:
    st.warning("Neither plotly nor altair is installed — showing raw table instead.")
    st.dataframe(flag_summary_df[["label", "count"]].rename(columns={"label": "Flag", "count": "Count"}))

# Per-flag expandable detail sections (use filtered df so user can drill down)
st.subheader("Per-flag detail")

for col in FLAG_COLS:
    affected = df[df[col] == True]  # noqa: E712
    full_affected_count = int(df_full[col].sum())
    label = _pretty_flag(col)

    with st.expander(f"{label} — {full_affected_count} records (full) | {len(affected)} visible"):
        if affected.empty:
            st.write("No matching records under current filters.")
        else:
            detail_cols = ["tambon", "unit", "type", "details"]
            st.dataframe(
                affected[detail_cols].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
            )
