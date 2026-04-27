"""
Streamlit Manual Review Queue
Visualises the 242 records from master_summary_log.csv that require manual
inspection, grouped hierarchically by tambon -> unit with flag breakdowns,
sidebar filters, and a flag-count bar chart summary.

Also includes a Verification Report tab that reads from verification_report.csv
(produced by election_pipeline/validation/verify_manual_ocr.py) and lets users
browse structure and math issues by อำเภอ / ตำบล / หน่วยเลือกตั้ง.

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

CSV_PATH = (
    Path(__file__).parent.parent.parent / "output_data" / "master_summary_log.csv"
)
REVIEWED_CSV_PATH = (
    Path(__file__).parent.parent.parent / "output_data" / "reviewed_units.csv"
)
VERIFICATION_CSV_PATH = (
    Path(__file__).parent.parent.parent / "output_data" / "verification_report.csv"
)
RESOLUTION_CSV_PATH = (
    Path(__file__).parent.parent.parent / "output_data" / "verification_resolutions.csv"
)

# Resolution options shown in the UI
_RESOLUTION_OPTIONS = [
    "",  # not reviewed yet
    "SOURCE_ERROR",  # error from source data, cannot fix
    "FIXED",  # we fixed it
]
_RESOLUTION_LABELS = {
    "": "— Not reviewed —",
    "SOURCE_ERROR": "⚛️ Source error (cannot fix)",
    "FIXED": "✅ Fixed by us",
}

_ALL_FLAG_COLS = [
    "flag_math_total_used",
    "flag_math_valid_score",
    "flag_name_mismatch",
    "flag_missing_counterpart",
    "flag_missing_data",
    "flag_linguistic_mismatch",
]

# Colour map for issue types in the verification tab
_ISSUE_COLORS = {
    "MISSING_FOLDER": "#EF4444",
    "MISSING_CSV": "#F59E0B",
    "READ_ERROR": "#F59E0B",
    "MATH_ALLOCATION": "#EF4444",
    "MATH_USED": "#EF4444",
    "MATH_SCORES": "#EF4444",
    "MATH_MISSING_FIELD": "#F59E0B",
}

_ISSUE_LABELS = {
    "MISSING_FOLDER": "❌ Missing Folder",
    "MISSING_CSV": "📄 Missing CSV",
    "READ_ERROR": "⚠️ Read Error",
    "MATH_ALLOCATION": "🔢 Math: Allocation",
    "MATH_USED": "🔢 Math: Used",
    "MATH_SCORES": "🔢 Math: Scores",
    "MATH_MISSING_FIELD": "⚠️ Math: Missing Field",
}


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


@st.cache_data
def load_verification_report() -> pd.DataFrame:
    """Load verification_report.csv produced by verify_manual_ocr.py."""
    if not VERIFICATION_CSV_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(VERIFICATION_CSV_PATH, dtype=str).fillna("")
    return df


def _resolution_key(row: pd.Series) -> str:
    """Stable string key for a verification issue row."""
    return "|".join(
        [
            str(row.get("amphoe", "")),
            str(row.get("tambon", "")),
            str(row.get("unit", "")),
            str(row.get("file_type", "")),
            str(row.get("issue_type", "")),
        ]
    )


def load_resolutions() -> dict[str, str]:
    """Load {key -> resolution} from verification_resolutions.csv."""
    if not RESOLUTION_CSV_PATH.exists():
        return {}
    try:
        df_res = pd.read_csv(RESOLUTION_CSV_PATH, dtype=str).fillna("")
        return dict(zip(df_res["key"], df_res["resolution"]))
    except Exception:
        return {}


def save_resolutions(resolutions: dict[str, str]) -> None:
    """Persist {key -> resolution} to verification_resolutions.csv."""
    RESOLUTION_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_res = pd.DataFrame(
        [(k, v) for k, v in resolutions.items()],
        columns=["key", "resolution"],
    )
    df_res.to_csv(RESOLUTION_CSV_PATH, index=False)


def set_resolution_callback(key: str, widget_key: str) -> None:
    """Selectbox on_change callback — persist the chosen resolution."""
    st.session_state.ver_resolutions[key] = st.session_state[widget_key]
    save_resolutions(st.session_state.ver_resolutions)


# ---------------------------------------------------------------------------
# Session-state helpers (review queue)
# ---------------------------------------------------------------------------


def load_reviewed_units() -> set[tuple[str, str, str]]:
    if not REVIEWED_CSV_PATH.exists():
        return set()
    try:
        df_rev = pd.read_csv(REVIEWED_CSV_PATH)
        if df_rev.empty:
            return set()
        return set(
            zip(
                df_rev["amphoe"].astype(str),
                df_rev["tambon"].astype(str),
                df_rev["unit"].astype(str),
            )
        )
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


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Manual Review Queue", layout="wide")

if "reviewed_units" not in st.session_state:
    st.session_state.reviewed_units = load_reviewed_units()

if "ver_resolutions" not in st.session_state:
    st.session_state.ver_resolutions = load_resolutions()

# tab_review, tab_verify = st.tabs(["📋 Manual Review Queue", "🔍 Verification Report"])
[tab_verify] = st.tabs(["🔍 Verification Report"])


# ============================================================
# TAB 1 — Manual Review Queue (existing behaviour)
# ============================================================

# with tab_review:
#     if not CSV_PATH.exists():
#         st.error(f"CSV not found at {CSV_PATH}")
#         st.stop()

#     df_full, FLAG_COLS = load_data()

#     if df_full.empty:
#         st.error(f"CSV not found or is empty at {CSV_PATH}")
#         st.stop()

#     # ── Sidebar filters ──────────────────────────────────────────────────────

#     st.sidebar.header("Filters")
#     all_amphoes: list[str] = sorted(df_full["amphoe"].dropna().unique().tolist())
#     selected_amphoes: list[str] = st.sidebar.multiselect(
#         "Amphoe (อำเภอ)",
#         options=all_amphoes,
#         default=all_amphoes,
#         help="Filter by district",
#     )

#     all_tambons: list[str] = sorted(df_full["tambon"].dropna().unique().tolist())
#     selected_tambons: list[str] = st.sidebar.multiselect(
#         "Tambon (ตำบล)",
#         options=all_tambons,
#         default=all_tambons,
#         help="Filter by sub-district",
#     )

#     all_types: list[str] = ["บัญชีรายชื่อ", "แบ่งเขต"]
#     selected_types: list[str] = st.sidebar.multiselect(
#         "Type (ประเภท)",
#         options=all_types,
#         default=all_types,
#         help="Filter by ballot type",
#     )

#     flag_labels: dict[str, str] = {col: _pretty_flag(col) for col in FLAG_COLS}
#     selected_flag_cols: list[str] = st.sidebar.multiselect(
#         "Active flags (ธง)",
#         options=FLAG_COLS,
#         default=[],
#         format_func=lambda col: flag_labels[col],
#         help="Show only rows where ALL selected flags are True",
#     )

#     hide_reviewed = st.sidebar.checkbox("Hide reviewed units", value=True)

#     st.sidebar.markdown("---")
#     st.sidebar.subheader("Pagination")
#     units_per_page = st.sidebar.number_input(
#         "Units per page",
#         min_value=1,
#         max_value=500,
#         value=20,
#         help="Reducing this number improves performance",
#     )

#     # ── Apply filters ────────────────────────────────────────────────────────

#     df = df_full.copy()

#     if selected_amphoes:
#         df = df[df["amphoe"].isin(selected_amphoes)]

#     if selected_tambons:
#         df = df[df["tambon"].isin(selected_tambons)]

#     if selected_types:
#         df = df[df["type"].isin(selected_types)]

#     if selected_flag_cols:
#         mask = df[selected_flag_cols].all(axis=1)
#         df = df[mask]

#     if hide_reviewed and st.session_state.reviewed_units:
#         rev_keys = {f"{a}|{t}|{u}" for a, t, u in st.session_state.reviewed_units}
#         df_keys = df["amphoe"].astype(str) + "|" + df["tambon"].astype(str) + "|" + df["unit"].astype(str)
#         df = df[~df_keys.isin(rev_keys)]

#     # Pagination
#     unique_units = df[["amphoe", "tambon", "unit"]].drop_duplicates()
#     total_units = len(unique_units)
#     total_pages = (total_units - 1) // units_per_page + 1
#     page_num = st.sidebar.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1)

#     if not unique_units.empty:
#         start_idx = (page_num - 1) * int(units_per_page)
#         end_idx = start_idx + int(units_per_page)
#         current_units_slice = unique_units.iloc[start_idx:end_idx]
#         df = df.merge(current_units_slice, on=["amphoe", "tambon", "unit"])

#     # ── Section 1 — Flag summary ─────────────────────────────────────────────

#     st.header("Flag Summary")
#     st.caption(
#         f"Counts for **{len(df)}** filtered records"
#         + (f" (full dataset: {len(df_full)})" if len(df) != len(df_full) else "")
#         + "."
#     )

#     flag_counts = {col: int(df[col].sum()) for col in FLAG_COLS}
#     flag_summary_df = pd.DataFrame(
#         {
#             "flag": list(flag_counts.keys()),
#             "label": [_pretty_flag(c) for c in flag_counts.keys()],
#             "count": list(flag_counts.values()),
#         }
#     ).sort_values("count", ascending=True)

#     if HAS_PLOTLY:
#         fig = px.bar(
#             flag_summary_df,
#             x="count",
#             y="label",
#             orientation="h",
#             title="Records per Flag (filtered)",
#             labels={"count": "Record count", "label": "Flag"},
#             color="count",
#             color_continuous_scale="Blues",
#             text="count",
#         )
#         fig.update_traces(textposition="outside")
#         fig.update_layout(
#             showlegend=False,
#             coloraxis_showscale=False,
#             height=350,
#             margin=dict(l=20, r=40, t=40, b=20),
#         )
#         st.plotly_chart(fig, width="stretch")

#     elif HAS_ALTAIR:
#         chart = (
#             alt.Chart(flag_summary_df)
#             .mark_bar()
#             .encode(
#                 x=alt.X("count:Q", title="Record count"),
#                 y=alt.Y("label:N", sort="-x", title="Flag"),
#                 color=alt.Color("count:Q", scale=alt.Scale(scheme="blues"), legend=None),
#                 tooltip=["label:N", "count:Q"],
#             )
#             .properties(title="Records per Flag (filtered)", height=300)
#         )
#         st.altair_chart(chart, width="stretch")

#     else:
#         st.warning("Neither plotly nor altair is installed — showing raw table instead.")
#         st.dataframe(flag_summary_df[["label", "count"]].rename(columns={"label": "Flag", "count": "Count"}))

#     # Per-flag expandable detail sections
#     st.subheader("Per-flag detail")

#     for col in FLAG_COLS:
#         affected = df[df[col] == True]  # noqa: E712
#         full_affected_count = int(df_full[col].sum())
#         label = _pretty_flag(col)
#         suffix = f" / {full_affected_count} total" if len(affected) != full_affected_count else ""

#         with st.expander(f"{label} — {len(affected)} records{suffix}"):
#             if affected.empty:
#                 st.write("No matching records under current filters.")
#             else:
#                 detail_cols = ["tambon", "unit", "type", "details"]
#                 st.dataframe(
#                     affected[detail_cols].reset_index(drop=True),
#                     width="stretch",
#                     hide_index=True,
#                 )

#     # ── Section 2 — Hierarchical review queue ───────────────────────────────

#     st.header("Manual Review Queue")
#     st.caption(
#         f"Showing **{len(df)}** of {len(df_full)} records "
#         f"| {int(df['flag_count'].sum())} total flag hits"
#     )

#     if df.empty:
#         st.info("No records match the current filters.")
#     else:
#         display_cols = ["type", "flag_count"] + FLAG_COLS + ["details"]

#         col_config: dict = {
#             "type": st.column_config.TextColumn("Type"),
#             "flag_count": st.column_config.NumberColumn("# Flags", format="%d"),
#             "details": st.column_config.TextColumn("Details", width="large"),
#         }
#         for col in FLAG_COLS:
#             col_config[col] = st.column_config.CheckboxColumn(
#                 _pretty_flag(col),
#                 help=f"Flag: {col}",
#             )

#         for tambon, tambon_df in df.groupby("tambon", sort=True):
#             st.subheader(f"ตำบล {tambon}")

#             for unit, unit_df in tambon_df.groupby("unit", sort=True):
#                 record_count = len(unit_df)
#                 flag_hits = int(unit_df["flag_count"].sum())

#                 col1, col2 = st.columns([0.8, 0.2])
#                 with col1:
#                     st.markdown(f"**หน่วยเลือกตั้ง {unit}**")
#                     st.caption(f"{record_count} records | {flag_hits} flag hits")

#                 with col2:
#                     amphoe_str = str(unit_df["amphoe"].iloc[0])
#                     tambon_str = str(tambon)
#                     unit_str = str(unit)
#                     key = (amphoe_str, tambon_str, unit_str)
#                     is_reviewed = key in st.session_state.reviewed_units
#                     cb_key = f"rev_{amphoe_str}_{tambon_str}_{unit_str}"
#                     st.checkbox(
#                         "Reviewed",
#                         value=is_reviewed,
#                         key=cb_key,
#                         on_change=toggle_review_callback,
#                         args=(key, cb_key),
#                     )

#                 table_df = unit_df[display_cols].reset_index(drop=True)
#                 st.dataframe(
#                     table_df,
#                     column_config=col_config,
#                     width="stretch",
#                     hide_index=True,
#                 )

#             st.divider()


# ============================================================
# TAB 2 — Verification Report
# ============================================================

with tab_verify:
    st.header("Verification Report")
    st.caption(
        "Results from `verify_manual_ocr.py` — structure and math checks "
        "on all CSVs in `verfied_ocr_data/`."
    )

    df_ver = load_verification_report()

    if df_ver.empty:
        st.warning(
            f"No verification report found at `{VERIFICATION_CSV_PATH}`.  \n"
            "Run `python election_pipeline/validation/verify_manual_ocr.py` to generate it."
        )
        st.stop()

    # Attach current resolution to every row
    df_ver["resolution"] = df_ver.apply(
        lambda r: st.session_state.ver_resolutions.get(_resolution_key(r), ""),
        axis=1,
    )

    # ── Summary metrics ──────────────────────────────────────────────────────

    total_issues = len(df_ver)
    struct_issues = len(
        df_ver[
            df_ver["issue_type"].isin(["MISSING_FOLDER", "MISSING_CSV", "READ_ERROR"])
        ]
    )
    math_issues = total_issues - struct_issues
    source_errors = int((df_ver["resolution"] == "SOURCE_ERROR").sum())
    fixed_count = int((df_ver["resolution"] == "FIXED").sum())
    unreviewed = total_issues - source_errors - fixed_count

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Total Issues", total_issues)
    mc2.metric("🏗️ Structural", struct_issues)
    mc3.metric("🔢 Math", math_issues)
    mc4.metric("⚛️ Source Errors", source_errors)
    mc5.metric("✅ Fixed", fixed_count)

    st.markdown("---")

    # ── Issue-type breakdown bar ─────────────────────────────────────────────

    type_counts = (
        df_ver["issue_type"]
        .value_counts()
        .reset_index()
        .rename(columns={"issue_type": "issue_type", "count": "count"})
    )
    type_counts["label"] = type_counts["issue_type"].map(
        lambda x: _ISSUE_LABELS.get(x, x)
    )

    if HAS_PLOTLY:
        fig_v = px.bar(
            type_counts,
            x="count",
            y="label",
            orientation="h",
            title="Issues by Type",
            labels={"count": "Count", "label": "Issue Type"},
            color="issue_type",
            color_discrete_map={k: v for k, v in _ISSUE_COLORS.items()},
            text="count",
        )
        fig_v.update_traces(textposition="outside")
        fig_v.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=20, r=40, t=40, b=20),
        )
        st.plotly_chart(fig_v, use_container_width=True)
    else:
        st.dataframe(
            type_counts[["label", "count"]].rename(
                columns={"label": "Issue Type", "count": "Count"}
            ),
            hide_index=True,
        )

    st.markdown("---")

    # ── Sidebar Filters ───────────────────────────────────────────────────────

    st.sidebar.header("Filters")

    all_ver_amphoes = sorted(df_ver["amphoe"].unique().tolist())
    sel_ver_amphoe = st.sidebar.multiselect(
        "อำเภอ (Amphoe)",
        options=all_ver_amphoes,
        default=[],
        placeholder="All",
        key="ver_amphoe",
    )

    _tambon_pool = (
        df_ver[df_ver["amphoe"].isin(sel_ver_amphoe)] if sel_ver_amphoe else df_ver
    )
    all_ver_tambons = sorted(_tambon_pool["tambon"].unique().tolist())
    sel_ver_tambon = st.sidebar.multiselect(
        "ตำบล (Tambon)",
        options=all_ver_tambons,
        default=[],
        placeholder="All",
        key="ver_tambon",
    )

    all_ver_types = sorted(df_ver["issue_type"].unique().tolist())
    sel_ver_type = st.sidebar.multiselect(
        "Issue Type",
        options=all_ver_types,
        format_func=lambda x: _ISSUE_LABELS.get(x, x),
        default=[],
        placeholder="All",
        key="ver_type",
    )

    all_ver_files = sorted(df_ver["file_type"].unique().tolist())
    sel_ver_file = st.sidebar.multiselect(
        "File Type",
        options=all_ver_files,
        default=[],
        placeholder="All",
        key="ver_file",
    )

    sel_ver_resolution = st.sidebar.multiselect(
        "Resolution",
        options=_RESOLUTION_OPTIONS,
        format_func=lambda x: _RESOLUTION_LABELS.get(x, x),
        default=[],
        placeholder="All",
        key="ver_resolution",
    )

    hide_ver_resolved = st.sidebar.checkbox(
        "Hide resolved issues (SOURCE_ERROR and FIXED)",
        value=False,
        key="hide_ver_resolved",
    )

    # Apply filters
    df_vf = df_ver.copy()
    if sel_ver_amphoe:
        df_vf = df_vf[df_vf["amphoe"].isin(sel_ver_amphoe)]
    if sel_ver_tambon:
        df_vf = df_vf[df_vf["tambon"].isin(sel_ver_tambon)]
    if sel_ver_type:
        df_vf = df_vf[df_vf["issue_type"].isin(sel_ver_type)]
    if sel_ver_file:
        df_vf = df_vf[df_vf["file_type"].isin(sel_ver_file)]
    if sel_ver_resolution:
        df_vf = df_vf[df_vf["resolution"].isin(sel_ver_resolution)]
    if hide_ver_resolved:
        df_vf = df_vf[~df_vf["resolution"].isin(["SOURCE_ERROR", "FIXED"])]

    st.caption(
        f"Showing **{len(df_vf)}** of {total_issues} issues "
        f"| {unreviewed} unreviewed · {source_errors} source errors · {fixed_count} fixed"
    )

    # ── Grouped display by อำเภอ / ตำบล / หน่วย ───────────────────────────

    if df_vf.empty:
        st.info("No issues match the current filters.")
    else:
        for amphoe, amp_df in df_vf.groupby("amphoe", sort=True):
            unrev_in_amp = int((amp_df["resolution"] == "").sum())
            amp_label = f"**{amphoe}** — {len(amp_df)} issue(s)"
            if unrev_in_amp:
                amp_label += f" · {unrev_in_amp} unreviewed"

            with st.expander(amp_label, expanded=(unrev_in_amp > 0)):
                for tambon, tam_df in amp_df.groupby("tambon", sort=True):
                    unrev_in_tam = int((tam_df["resolution"] == "").sum())
                    tam_label = f"ตำบล {tambon}" if tambon else "(no tambon)"
                    tam_label += f" — {len(tam_df)} issue(s)"
                    if unrev_in_tam:
                        tam_label += f" · {unrev_in_tam} unreviewed"

                    with st.expander(tam_label, expanded=(unrev_in_tam > 0)):
                        for unit, unit_df in tam_df.groupby("unit", sort=True):
                            if unit:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;หน่วยเลือกตั้ง **{unit}**")

                            # Render each issue as a row with a resolution selectbox
                            for _idx, (_, issue_row) in enumerate(unit_df.iterrows()):
                                rkey = _resolution_key(issue_row)
                                wkey = f"res_{rkey}__{_idx}"
                                current_res = st.session_state.ver_resolutions.get(rkey, "")
                                issue_label = _ISSUE_LABELS.get(
                                    issue_row["issue_type"], issue_row["issue_type"]
                                )

                                r_col1, r_col2 = st.columns([0.65, 0.35])
                                with r_col1:
                                    res_badge = _RESOLUTION_LABELS.get(
                                        current_res, current_res
                                    )
                                    st.markdown(
                                        f"**{issue_label}** &nbsp;`{issue_row['file_type']}`  \n"
                                        f"<small>{issue_row['issue_details']}</small>",
                                        unsafe_allow_html=True,
                                    )
                                with r_col2:
                                    st.selectbox(
                                        "Resolution",
                                        options=_RESOLUTION_OPTIONS,
                                        index=(
                                            _RESOLUTION_OPTIONS.index(current_res)
                                            if current_res in _RESOLUTION_OPTIONS
                                            else 0
                                        ),
                                        format_func=lambda x: _RESOLUTION_LABELS.get(x, x),
                                        key=wkey,
                                        on_change=set_resolution_callback,
                                        args=(rkey, wkey),
                                        label_visibility="collapsed",
                                    )

                            st.markdown("")

                    st.divider()
