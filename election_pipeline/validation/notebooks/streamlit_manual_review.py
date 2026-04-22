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
REVIEWED_CSV_PATH = Path(__file__).parent.parent.parent / "output_data" / "reviewed_units.csv"

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

def load_reviewed_units() -> set[tuple[str, str, str]]:
    if not REVIEWED_CSV_PATH.exists():
        return set()
    try:
        df_rev = pd.read_csv(REVIEWED_CSV_PATH)
        if df_rev.empty:
            return set()
        return set(zip(df_rev["amphoe"].astype(str), df_rev["tambon"].astype(str), df_rev["unit"].astype(str)))
    except Exception:
        return set()

def save_reviewed_units(reviewed: set[tuple[str, str, str]]):
    df_rev = pd.DataFrame(list(reviewed), columns=["amphoe", "tambon", "unit"])
    REVIEWED_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_rev.to_csv(REVIEWED_CSV_PATH, index=False)

def toggle_review_callback(id_tuple: tuple[str, str, str], cb_key: str):
    """Callback to update reviewed units without manual rerun lag."""
    if st.session_state[cb_key]:
        st.session_state.reviewed_units.add(id_tuple)
    else:
        st.session_state.reviewed_units.discard(id_tuple)
    save_reviewed_units(st.session_state.reviewed_units)

if "reviewed_units" not in st.session_state:
    st.session_state.reviewed_units = load_reviewed_units()

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
all_amphoes: list[str] = sorted(df_full["amphoe"].dropna().unique().tolist())
selected_amphoes: list[str] = st.sidebar.multiselect(
    "Amphoe (อำเภอ)",
    options=all_amphoes,
    default=all_amphoes,
    help="Filter by district",
)

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

hide_reviewed = st.sidebar.checkbox("Hide reviewed units", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Pagination")
units_per_page = st.sidebar.number_input(
    "Units per page",
    min_value=1,
    max_value=500,
    value=20,
    help="Reducing this number improves performance",
)

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------

df = df_full.copy()

if selected_amphoes:
    df = df[df["amphoe"].isin(selected_amphoes)]

if selected_tambons:
    df = df[df["tambon"].isin(selected_tambons)]

if selected_types:
    df = df[df["type"].isin(selected_types)]

if selected_flag_cols:
    mask = df[selected_flag_cols].all(axis=1)
    df = df[mask]

if hide_reviewed and st.session_state.reviewed_units:
    # Vectorized filtering for better performance
    rev_keys = {f"{a}|{t}|{u}" for a, t, u in st.session_state.reviewed_units}
    df_keys = df["amphoe"].astype(str) + "|" + df["tambon"].astype(str) + "|" + df["unit"].astype(str)
    df = df[~df_keys.isin(rev_keys)]

# Apply pagination to the unique units to limit rendered components
unique_units = df[["amphoe", "tambon", "unit"]].drop_duplicates()
total_units = len(unique_units)
total_pages = (total_units - 1) // units_per_page + 1
page_num = st.sidebar.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1)

if not unique_units.empty:
    start_idx = (page_num - 1) * int(units_per_page)
    end_idx = start_idx + int(units_per_page)
    current_units_slice = unique_units.iloc[start_idx:end_idx]
    df = df.merge(current_units_slice, on=["amphoe", "tambon", "unit"])

# ---------------------------------------------------------------------------
# Section 1 — Flag summary
# ---------------------------------------------------------------------------

st.header("Flag Summary")
st.caption(
    f"Counts for **{len(df)}** filtered records"
    + (f" (full dataset: {len(df_full)})" if len(df) != len(df_full) else "")
    + "."
)

# Per-flag counts from the filtered dataframe
flag_counts = {col: int(df[col].sum()) for col in FLAG_COLS}
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
        title="Records per Flag (filtered)",
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
    st.plotly_chart(fig, width="stretch")

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
        .properties(title="Records per Flag (filtered)", height=300)
    )
    st.altair_chart(chart, width="stretch")

else:
    st.warning("Neither plotly nor altair is installed — showing raw table instead.")
    st.dataframe(flag_summary_df[["label", "count"]].rename(columns={"label": "Flag", "count": "Count"}))

# Per-flag expandable detail sections (use filtered df so user can drill down)
st.subheader("Per-flag detail")

for col in FLAG_COLS:
    affected = df[df[col] == True]  # noqa: E712
    full_affected_count = int(df_full[col].sum())
    label = _pretty_flag(col)
    suffix = f" / {full_affected_count} total" if len(affected) != full_affected_count else ""

    with st.expander(f"{label} — {len(affected)} records{suffix}"):
        if affected.empty:
            st.write("No matching records under current filters.")
        else:
            detail_cols = ["tambon", "unit", "type", "details"]
            st.dataframe(
                affected[detail_cols].reset_index(drop=True),
                width="stretch",
                hide_index=True,
            )

# ---------------------------------------------------------------------------
# Section 2 — Hierarchical review queue
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
            
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.markdown(f"**หน่วยเลือกตั้ง {unit}**")
                st.caption(f"{record_count} records | {flag_hits} flag hits")
            
            with col2:
                amphoe_str = str(unit_df["amphoe"].iloc[0])
                tambon_str = str(tambon)
                unit_str = str(unit)
                key = (amphoe_str, tambon_str, unit_str)
                is_reviewed = key in st.session_state.reviewed_units
                cb_key = f"rev_{amphoe_str}_{tambon_str}_{unit_str}"
                st.checkbox(
                    "Reviewed",
                    value=is_reviewed,
                    key=cb_key,
                    on_change=toggle_review_callback,
                    args=(key, cb_key),
                )

            table_df = unit_df[display_cols].reset_index(drop=True)
            st.dataframe(
                table_df,
                column_config=col_config,
                width="stretch",
                hide_index=True,
            )

        st.divider()
