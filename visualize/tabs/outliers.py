"""
Outlier Detection tab for the Election Insights dashboard.

Uses Z-score analysis on district-to-party-list vote ratio to identify
parties with statistically anomalous vote distributions.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_outliers_tab(merged_df: pd.DataFrame) -> None:
    """Render the Outlier Detection tab.

    Parameters
    ----------
    merged_df:
        DataFrame from merged_parties_with_ratio.csv. Expected columns:
        party_name, district_votes, list_votes, ratio, party_number,
        z_score, is_outlier, category.
    """

    st.header("Outlier Detection (การตรวจจับความผิดปกติ)")
    st.markdown(
        """
        **Methodology:** For each party, the ratio of *party-list votes* to
        *constituency votes* is computed. Parties with a Z-score exceeding the
        threshold (|z| > 3) are flagged as statistical outliers — their
        party-list vote share is disproportionately large compared to the field.

        **Implication:** High ratios in small parties may indicate that votes
        were cast for the party-list number without any real organisational base.
        """
    )

    st.divider()

    if merged_df.empty:
        st.error("Data file could not be loaded. Check that merged_parties_with_ratio.csv exists.")
        return

    # ── Key metrics ──────────────────────────────────────────────────────────

    outlier_df = merged_df[merged_df["is_outlier"] == True]  # noqa: E712
    non_outlier_df = merged_df[merged_df["is_outlier"] != True]  # noqa: E712

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Parties", len(merged_df))
    col2.metric(
        "Outlier Parties",
        len(outlier_df),
        delta=f"{len(outlier_df) / max(len(merged_df), 1):.0%} of total",
        delta_color="inverse" if len(outlier_df) > 0 else "off",
    )
    col3.metric(
        "Max Z-Score",
        f"{merged_df['z_score'].max():.2f}" if "z_score" in merged_df.columns else "N/A",
    )

    st.divider()

    # ── Outlier party table ──────────────────────────────────────────────────

    st.subheader("Flagged Outlier Parties")

    if outlier_df.empty:
        st.success("No statistical outliers detected.")
    else:
        display_cols = [
            c for c in
            ["party_name", "district_votes", "list_votes", "ratio", "z_score", "category"]
            if c in outlier_df.columns
        ]
        sort_col = "z_score" if "z_score" in display_cols else (display_cols[0] if display_cols else None)
        sorted_df = outlier_df[display_cols].sort_values(sort_col, ascending=False).reset_index(drop=True) if sort_col else outlier_df[display_cols].reset_index(drop=True)
        st.dataframe(
            sorted_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "party_name": st.column_config.TextColumn("Party (พรรค)"),
                "district_votes": st.column_config.NumberColumn(
                    "Constituency Votes", format="%d"
                ),
                "list_votes": st.column_config.NumberColumn(
                    "Party-List Votes", format="%d"
                ),
                "ratio": st.column_config.NumberColumn(
                    "List/Constituency Ratio", format="%.2f"
                ),
                "z_score": st.column_config.NumberColumn(
                    "Z-Score", format="%.3f",
                    help="Standardised deviation from the mean ratio"
                ),
                "category": st.column_config.TextColumn("Category"),
            },
        )

    st.divider()

    # ── Scatter plot ─────────────────────────────────────────────────────────

    st.subheader("Z-Score Distribution (All Parties)")
    st.caption(
        "Each point is a party. Red points are flagged outliers. "
        "Hover to see party name."
    )

    if "z_score" in merged_df.columns and "party_name" in merged_df.columns:
        _render_scatter(merged_df)

    st.divider()

    # ── Full data table ──────────────────────────────────────────────────────

    with st.expander("Full merged_parties_with_ratio.csv data", expanded=False):
        all_display_cols = [
            c for c in
            ["party_name", "district_votes", "list_votes", "ratio",
             "z_score", "is_outlier", "category"]
            if c in merged_df.columns
        ]
        st.dataframe(
            merged_df[all_display_cols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )


def _render_scatter(merged_df: pd.DataFrame) -> None:
    """Render scatter plot of party index vs Z-score, highlighting outliers."""

    # Build a clean plot DataFrame
    plot_df = merged_df.copy().reset_index(drop=True)
    plot_df["party_index"] = range(len(plot_df))
    plot_df["is_outlier_label"] = plot_df["is_outlier"].map(
        lambda v: "Outlier" if v is True or str(v).lower() == "true" else "Normal"
    )

    # Try altair first (richer tooltips), fall back to st.scatter_chart
    try:
        import altair as alt  # noqa: PLC0415

        color_scale = alt.Scale(
            domain=["Outlier", "Normal"],
            range=["#EF4444", "#3B82F6"],
        )

        chart = (
            alt.Chart(plot_df)
            .mark_circle(size=80, opacity=0.8)
            .encode(
                x=alt.X(
                    "party_index:Q",
                    title="Party Index",
                    axis=alt.Axis(labelOverlap=True),
                ),
                y=alt.Y("z_score:Q", title="Z-Score"),
                color=alt.Color(
                    "is_outlier_label:N",
                    scale=color_scale,
                    legend=alt.Legend(title="Classification"),
                ),
                tooltip=[
                    alt.Tooltip("party_name:N", title="Party"),
                    alt.Tooltip("z_score:Q", title="Z-Score", format=".3f"),
                    alt.Tooltip("ratio:Q", title="List/Const. Ratio", format=".2f"),
                    alt.Tooltip("is_outlier_label:N", title="Classification"),
                ],
            )
            .properties(
                title="Party Z-Scores (List/Constituency Vote Ratio)",
                height=400,
            )
            .interactive()
        )

        # Add threshold line at z=3
        threshold_line = (
            alt.Chart(pd.DataFrame({"z": [3.0, -3.0]}))
            .mark_rule(color="#F59E0B", strokeDash=[6, 4], opacity=0.7)
            .encode(y="z:Q")
        )

        st.altair_chart(chart + threshold_line, use_container_width=True)

    except ImportError:
        # Fallback: native st.scatter_chart
        scatter_data = plot_df[["party_index", "z_score"]].copy()
        st.scatter_chart(
            scatter_data,
            x="party_index",
            y="z_score",
        )
        st.caption("Install `altair` for richer interactive charts with tooltips.")
