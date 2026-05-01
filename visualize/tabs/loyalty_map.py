"""
Bhumjaithai Loyalty Map tab for the Election Insights dashboard.

Visualises the ratio of Bhumjaithai party votes to total valid ballots
across Tambons in the dataset, coloured in shades of blue from low (light)
to high (dark) loyalty.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st


def render_loyalty_tab(
    ratio_df: pd.DataFrame,
    geo_df: Optional[pd.DataFrame],
) -> None:
    """Render the Bhumjaithai Loyalty Map tab.

    Parameters
    ----------
    ratio_df:
        DataFrame from all_districts_bhumjaithai_ratio.csv. Expected columns:
        amphoe, tambon, bhumjaithai_votes, total_valid_ballots, ratio.
    geo_df:
        Optional flat DataFrame with (geo_name, lat, lon) from the GeoJSON
        loader. Used for choropleth-style map rendering. Falls back to a
        bar chart if not available.
    """

    st.header("Bhumjaithai Loyalty Map (แผนที่ความจงรักภักดีของพรรคภูมิใจไทย)")
    st.markdown(
        """
        **Metric:** The *loyalty ratio* is computed as:

        > **ratio = Bhumjaithai party-list votes / total valid party-list ballots**

        Higher values indicate greater local support for the Bhumjaithai party.
        The map (or chart below) shows the geographic distribution of this ratio
        across Tambons in the dataset.

        **Data:** Uthai Thani province (อุทัยธานี) — อำเภอบ้านไร่ sub-districts.
        """
    )

    st.divider()

    if ratio_df.empty:
        st.error(
            "Data file could not be loaded. "
            "Check that all_districts_bhumjaithai_ratio.csv exists."
        )
        return

    # ── Summary metrics ──────────────────────────────────────────────────────

    col1, col2, col3 = st.columns(3)
    col1.metric("Tambons in Dataset", ratio_df["tambon"].nunique() if "tambon" in ratio_df.columns else len(ratio_df))
    col2.metric(
        "Mean Loyalty Ratio",
        f"{ratio_df['ratio'].mean():.1%}" if "ratio" in ratio_df.columns else "N/A",
    )
    col3.metric(
        "Max Loyalty Ratio",
        f"{ratio_df['ratio'].max():.1%}" if "ratio" in ratio_df.columns else "N/A",
        delta=(
            ratio_df.loc[ratio_df["ratio"].idxmax(), "tambon"]
            if "ratio" in ratio_df.columns and "tambon" in ratio_df.columns and ratio_df["ratio"].notna().any()
            else ""
        ),
        delta_color="off",
    )

    st.divider()

    # ── Map or bar chart ─────────────────────────────────────────────────────

    map_rendered = _try_render_pydeck_map(ratio_df, geo_df)

    if not map_rendered:
        _render_bar_chart_fallback(ratio_df)

    st.divider()

    # ── Tabular data ─────────────────────────────────────────────────────────

    with st.expander("Full data table (all_districts_bhumjaithai_ratio.csv)", expanded=False):
        display_cols = [
            c for c in
            ["amphoe", "tambon", "bhumjaithai_votes", "total_valid_ballots", "ratio"]
            if c in ratio_df.columns
        ]
        st.dataframe(
            ratio_df[display_cols].sort_values("ratio", ascending=False).reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            column_config={
                "amphoe": st.column_config.TextColumn("อำเภอ (District)"),
                "tambon": st.column_config.TextColumn("ตำบล (Sub-district)"),
                "bhumjaithai_votes": st.column_config.NumberColumn(
                    "Bhumjaithai Votes", format="%d"
                ),
                "total_valid_ballots": st.column_config.NumberColumn(
                    "Total Valid Ballots", format="%d"
                ),
                "ratio": st.column_config.NumberColumn(
                    "Loyalty Ratio", format="%.4f"
                ),
            },
        )


def _try_render_pydeck_map(
    ratio_df: pd.DataFrame,
    geo_df: Optional[pd.DataFrame],
) -> bool:
    """Attempt to render a pydeck choropleth/scatter map coloured by ratio.

    Returns True if map was successfully rendered, False otherwise.
    """
    try:
        import pydeck as pdk  # noqa: PLC0415

        # Enrich ratio_df with coordinates
        enriched = _enrich_with_coords(ratio_df, geo_df)

        if enriched is None or enriched.empty or "lat" not in enriched.columns:
            return False

        # Normalise ratio to [0, 255] for blue-channel colour encoding
        ratio_min = enriched["ratio"].min()
        ratio_max = enriched["ratio"].max()
        ratio_range = ratio_max - ratio_min if ratio_max != ratio_min else 1.0

        def _blue_colour(r: float) -> list[int]:
            norm = (r - ratio_min) / ratio_range
            # Blues: low ratio -> light blue (173, 216, 230), high -> deep blue (0, 0, 139)
            blue = int(139 + (1 - norm) * (230 - 139))
            green = int(0 + (1 - norm) * 216)
            red = int(0 + (1 - norm) * 173)
            return [red, green, blue, 200]

        enriched["colour"] = enriched["ratio"].apply(_blue_colour)
        enriched["colour_r"] = enriched["colour"].apply(lambda c: c[0])
        enriched["colour_g"] = enriched["colour"].apply(lambda c: c[1])
        enriched["colour_b"] = enriched["colour"].apply(lambda c: c[2])
        enriched["ratio_pct"] = enriched["ratio"].apply(lambda r: f"{r:.1%}")

        with st.expander("Map view state tuner (copy values to code when done)", expanded=False):
            _c1, _c2 = st.columns(2)
            _lat    = _c1.number_input("latitude",            value=15.30,  step=0.01,  format="%.4f", key="lmap_lat")
            _lon    = _c2.number_input("longitude",           value=99.55,  step=0.01,  format="%.4f", key="lmap_lon")
            _zoom   = _c1.number_input("zoom",                value=9,      step=1,                    key="lmap_zoom")
            _pitch  = _c2.number_input("pitch",               value=0,      step=5,                    key="lmap_pitch")
            _radius = st.number_input( "get_radius (metres)", value=2000,   step=100,                  key="lmap_radius")
            st.code(f"latitude={_lat}, longitude={_lon}, zoom={_zoom}, pitch={_pitch}, get_radius={_radius}")

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=enriched,
            get_position="[lon, lat]",
            get_color="[colour_r, colour_g, colour_b, 200]",
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
                tooltip={
                    "text": "{tambon} ({amphoe})\nLoyalty Ratio: {ratio_pct}"
                },
            )
        )
        st.caption(
            "Colour scale: light blue = low Bhumjaithai support, "
            "dark blue = high Bhumjaithai support."
        )
        return True

    except Exception:  # noqa: BLE001
        return False


def _enrich_with_coords(
    ratio_df: pd.DataFrame,
    geo_df: Optional[pd.DataFrame],
) -> Optional[pd.DataFrame]:
    """Assign coordinates to tambon rows using Thai name lookup.

    Uses a hardcoded tambon/amphoe → (lat, lon) table so Thai names resolve
    correctly without requiring an English GeoJSON match.
    """
    try:
        from data_loader import resolve_thai_coords  # noqa: PLC0415
    except ImportError:
        from visualize.data_loader import resolve_thai_coords  # noqa: PLC0415

    enriched = ratio_df.copy().reset_index(drop=True)

    lats, lons = [], []
    for _, row in enriched.iterrows():
        tambon = str(row.get("tambon", ""))
        amphoe = str(row.get("amphoe", ""))
        lat, lon = resolve_thai_coords(amphoe, tambon)
        lats.append(lat)
        lons.append(lon)

    enriched["lat"] = lats
    enriched["lon"] = lons
    return enriched


def _render_bar_chart_fallback(ratio_df: pd.DataFrame) -> None:
    """Render a bar chart of Tambon loyalty ratios when map is unavailable."""
    st.subheader("Loyalty Ratio by Tambon (Bar Chart)")
    st.caption(
        "Map display unavailable — showing bar chart of loyalty ratio per Tambon. "
        "Install pydeck and ensure network access for the map view."
    )

    if "tambon" not in ratio_df.columns or "ratio" not in ratio_df.columns:
        st.warning("Expected columns 'tambon' and 'ratio' not found in data.")
        return

    chart_df = (
        ratio_df[["tambon", "ratio"]]
        .sort_values("ratio", ascending=False)
        .reset_index(drop=True)
    )
    chart_df.columns = ["Tambon (ตำบล)", "Loyalty Ratio"]

    try:
        import altair as alt  # noqa: PLC0415

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Loyalty Ratio:Q",
                    title="Bhumjaithai Vote Share",
                    axis=alt.Axis(format=".0%"),
                ),
                y=alt.Y(
                    "Tambon (ตำบล):N",
                    sort="-x",
                    title="Tambon",
                ),
                color=alt.Color(
                    "Loyalty Ratio:Q",
                    scale=alt.Scale(scheme="blues"),
                    legend=alt.Legend(title="Loyalty Ratio"),
                ),
                tooltip=[
                    alt.Tooltip("Tambon (ตำบล):N", title="Tambon"),
                    alt.Tooltip("Loyalty Ratio:Q", title="Ratio", format=".3f"),
                ],
            )
            .properties(
                title="Bhumjaithai Loyalty Ratio by Tambon",
                height=max(300, len(chart_df) * 22),
            )
        )
        st.altair_chart(chart, use_container_width=True)

    except ImportError:
        st.bar_chart(
            chart_df.set_index("Tambon (ตำบล)")["Loyalty Ratio"],
            use_container_width=True,
        )
