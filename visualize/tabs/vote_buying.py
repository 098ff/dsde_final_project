"""
Vote Buying Detection tab for the Election Insights dashboard.

Insight: When vote buying occurs, voters mark the same party number on both
the constituency (แบ่งเขต) and party-list (บัญชีรายชื่อ) ballots. This causes
small/no-name parties to receive unexplained party-list votes. Polling
stations where any small party exceeded 6.5% of party-list votes are
flagged as suspicious.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st


def render_vote_buying_tab(
    small_df: pd.DataFrame,
    suspect_df: pd.DataFrame,
    geo_df: Optional[pd.DataFrame],
) -> None:
    """Render the Vote Buying Detection tab.

    Parameters
    ----------
    small_df:
        DataFrame from small_party.csv. Contains 'Party' and 'small'
        columns (1.0 = classified as small/no-name party).
    suspect_df:
        DataFrame from suspect.csv. Contains 'Amphoe', 'Tambon', 'Unit',
        'Suspect' columns (1.0 = suspicious polling station).
    geo_df:
        Optional flat DataFrame with columns (geo_name, lat, lon) from the
        GeoJSON loader. If None, the map falls back to an interactive table.
    """

    st.header("การซื้อเสียง (Vote Buying Detection)")
    st.markdown(
        """
        **Methodology:** When vote buying occurs, voters are instructed to mark the
        same party number on both ballots. This causes small/no-name parties (those
        with minimal branches, representatives, members, and social media presence)
        to receive disproportionate party-list votes.

        **Classification:** Parties are classified as *small* using PCA on 8 scaled
        variables (MP ratio, branches, representatives, members, social media followers,
        Google Trends, historical seats). A PCA index below 50% indicates a small party.

        **Suspicious Stations:** Any polling unit where a small party received
        **more than 6.5%** of party-list votes is flagged as suspicious.
        """
    )

    st.divider()

    # ── Key metrics ──────────────────────────────────────────────────────────

    if small_df.empty or suspect_df.empty:
        st.error("Data files could not be loaded. Check that data/ CSVs are present.")
        return

    small_parties = small_df[small_df["small"] == 1.0]
    suspect_stations = suspect_df[suspect_df["Suspect"] == 1.0]

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="Total Parties Analysed",
        value=len(small_df),
    )
    col2.metric(
        label="Small / No-Name Parties",
        value=len(small_parties),
        delta=f"{len(small_parties) / max(len(small_df), 1):.0%} of total",
        delta_color="off",
    )
    col3.metric(
        label="Suspicious Polling Stations",
        value=int(suspect_stations["Suspect"].sum()),
        delta="Stations with >6.5% small-party list votes",
        delta_color="inverse" if len(suspect_stations) > 0 else "off",
    )

    st.divider()

    # ── Small party table ────────────────────────────────────────────────────

    st.subheader("Small / No-Name Parties")
    st.caption(
        "Parties classified as small (PCA Index < 50%). "
        "These are the parties whose unexpectedly high party-list vote share "
        "may indicate vote buying."
    )

    display_cols_small = [
        "Party",
        "PCA_Index",
        "sent_pm_district_ratio",
        "sent_pm_partylist_ratio",
        "social_media_followers_scaled",
        "branch_scaled",
        "representative_scaled",
        "member_scaled",
        "trends_scaled",
        "past_pm",
        "KMeans_Cluster",
    ]
    display_cols_small = [c for c in display_cols_small if c in small_parties.columns]

    sort_col = (
        "PCA_Index"
        if "PCA_Index" in display_cols_small
        else (display_cols_small[0] if display_cols_small else None)
    )
    sorted_small = (
        small_parties[display_cols_small].sort_values(sort_col).reset_index(drop=True)
        if sort_col
        else small_parties[display_cols_small].reset_index(drop=True)
    )
    st.dataframe(
        sorted_small,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Party": st.column_config.TextColumn("Party Name (พรรค)"),
            "PCA_Index": st.column_config.NumberColumn(
                "PCA Index",
                format="%.3f",
                help="Lower = more 'small-party' characteristics",
            ),
            "sent_pm_district_ratio": st.column_config.NumberColumn(
                "District MP Ratio", format="%.3f"
            ),
            "sent_pm_partylist_ratio": st.column_config.NumberColumn(
                "Party-List MP Ratio", format="%.3f"
            ),
            "social_media_followers_scaled": st.column_config.NumberColumn(
                "Social Media (scaled)", format="%.3f"
            ),
            "branch_scaled": st.column_config.NumberColumn(
                "Branches (scaled)", format="%.3f"
            ),
            "representative_scaled": st.column_config.NumberColumn(
                "Representatives (scaled)", format="%.3f"
            ),
            "member_scaled": st.column_config.NumberColumn(
                "Members (scaled)", format="%.3f"
            ),
            "trends_scaled": st.column_config.NumberColumn(
                "Google Trends (scaled)", format="%.3f"
            ),
            "past_pm": st.column_config.NumberColumn("Past Seats (binary)"),
            "KMeans_Cluster": st.column_config.NumberColumn("KMeans Cluster"),
        },
    )

    st.divider()

    # ── Suspect stations map / table ─────────────────────────────────────────

    st.subheader("Suspicious Polling Stations (หน่วยเลือกตั้งที่น่าสงสัย)")
    st.caption(
        f"**{len(suspect_stations)}** stations flagged where a small party "
        "received >6.5% of party-list votes."
    )

    if suspect_stations.empty:
        st.info("No suspicious stations detected in the dataset.")
    else:
        _render_suspect_map_or_table(suspect_stations, geo_df)

    st.divider()

    # ── Full suspect data table ──────────────────────────────────────────────

    with st.expander("Full suspect.csv data table", expanded=False):
        st.dataframe(
            suspect_df.reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Amphoe": st.column_config.TextColumn("อำเภอ (District)"),
                "Tambon": st.column_config.TextColumn("ตำบล (Sub-district)"),
                "Unit": st.column_config.TextColumn("หน่วยเลือกตั้ง (Polling Unit)"),
                "Suspect": st.column_config.NumberColumn(
                    "Suspicious", help="1.0 = flagged, 0.0 = clean"
                ),
            },
        )


def _render_suspect_map_or_table(
    suspect_stations: pd.DataFrame,
    geo_df: Optional[pd.DataFrame],
) -> None:
    """Attempt to render a pydeck map; fall back to interactive table."""

    map_rendered = False

    try:
        import pydeck as pdk  # noqa: PLC0415

        station_rows = _enrich_suspect_with_coords(suspect_stations, geo_df)

        if not station_rows.empty and "lat" in station_rows.columns:
            with st.expander("Map view state tuner (copy values to code when done)", expanded=False):
                _c1, _c2 = st.columns(2)
                _lat    = _c1.number_input("latitude",            value=15.30,  step=0.01,  format="%.4f", key="vmap_lat")
                _lon    = _c2.number_input("longitude",           value=99.55,  step=0.01,  format="%.4f", key="vmap_lon")
                _zoom   = _c1.number_input("zoom",                value=9,      step=1,                    key="vmap_zoom")
                _pitch  = _c2.number_input("pitch",               value=0,      step=5,                    key="vmap_pitch")
                _radius = st.number_input( "get_radius (metres)", value=2000,   step=100,                  key="vmap_radius")
                st.code(f"latitude={_lat}, longitude={_lon}, zoom={_zoom}, pitch={_pitch}, get_radius={_radius}")

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=station_rows,
                get_position="[lon, lat]",
                get_color="[220, 50, 50, 200]",
                get_radius=_radius,
                pickable=True,
            )
            view_state = pdk.ViewState(
                latitude=_lat,
                longitude=_lon,
                zoom=_zoom,
                pitch=_pitch,
            )
            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip={"text": "{Amphoe} / {Tambon}\n{Unit}"},
                )
            )
            map_rendered = True
    except Exception:  # noqa: BLE001
        pass  # Fall through to table display

    if not map_rendered:
        st.info(
            "Map display requires GeoJSON data (network access) and pydeck. "
            "Showing interactive table instead."
        )
        st.dataframe(
            suspect_stations[["Amphoe", "Tambon", "Unit"]].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Amphoe": st.column_config.TextColumn("อำเภอ (District)"),
                "Tambon": st.column_config.TextColumn("ตำบล (Sub-district)"),
                "Unit": st.column_config.TextColumn("หน่วยเลือกตั้ง (Polling Unit)"),
            },
        )


def _enrich_suspect_with_coords(
    suspect_df: pd.DataFrame,
    geo_df: "Optional[pd.DataFrame]",
) -> pd.DataFrame:
    """Assign coordinates to suspect stations using Thai name lookup.

    Uses a hardcoded tambon/amphoe → (lat, lon) table so Thai names resolve
    correctly without requiring an English GeoJSON match.
    Adds a small per-row jitter so stations within the same tambon don't stack.
    """
    import math  # noqa: PLC0415
    try:
        from data_loader import resolve_thai_coords  # noqa: PLC0415
    except ImportError:
        from visualize.data_loader import resolve_thai_coords  # noqa: PLC0415

    rows = []
    for idx, row in enumerate(suspect_df.itertuples(index=False)):
        tambon = str(getattr(row, "Tambon", ""))
        amphoe = str(getattr(row, "Amphoe", ""))
        base_lat, base_lon = resolve_thai_coords(amphoe, tambon)
        # Spiral jitter so multiple units in the same tambon are visually distinct
        jitter = 0.008
        lat = base_lat + jitter * math.sin(idx * 0.7)
        lon = base_lon + jitter * math.cos(idx * 0.7)
        rows.append(
            {
                "Amphoe": amphoe,
                "Tambon": tambon,
                "Unit": getattr(row, "Unit", ""),
                "lat": lat,
                "lon": lon,
            }
        )

    return pd.DataFrame(rows)
