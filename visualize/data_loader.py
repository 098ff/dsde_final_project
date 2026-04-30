"""
Data loader for the Election Insights Streamlit application.

All loader functions use @st.cache_data to avoid re-reading CSV files on
every interaction. The GeoJSON loader attempts to fetch a public dataset
of Thai Tambons and returns None gracefully if the network is unavailable
or the download fails.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"

_SMALL_PARTY_CSV = _DATA_DIR / "small_party.csv"
_SUSPECT_CSV = _DATA_DIR / "suspect.csv"
_MERGED_PARTIES_CSV = _DATA_DIR / "merged_parties_with_ratio.csv"
_BHUMJAITHAI_RATIO_CSV = _DATA_DIR / "all_districts_bhumjaithai_ratio.csv"

# Public GeoJSON for Thai administrative boundaries (Tambon level).
# Source: github.com/apisit/thailand.json  (tambon-level boundaries)
_GEOJSON_URL = (
    "https://raw.githubusercontent.com/cvdlab/react-leaflet-distance-layer/"
    "master/examples/data/thailand.json"
)

# Fallback: a simpler boundary set that is reliably available
_GEOJSON_FALLBACK_URL = (
    "https://raw.githubusercontent.com/apisit/thailand.json/"
    "master/thailand.json"
)


# ---------------------------------------------------------------------------
# Thai location lookup
# ---------------------------------------------------------------------------

_TAMBON_COORDS: dict[str, tuple[float, float]] = {
    # อำเภอบ้านไร่
    "ตำบลบ้านไร่":          (15.047, 99.629),
    "ตำบลคอกควาย":          (15.095, 99.700),
    "ตำบลหนองจอก":          (14.978, 99.748),
    "ตำบลเจ้าวัด":           (15.038, 99.820),
    "ตำบลวังหิน":            (14.993, 99.689),
    "ตำบลทัพหลวง":           (15.119, 99.858),
    "ตำบลบ้านบึง":           (15.072, 99.778),
    "ตำบลหูช้าง":            (14.912, 99.592),
    "ตำบลเมืองการุ้ง":        (14.995, 99.558),
    "ตำบลแก่นมะกรูด":        (14.851, 99.690),
    "ตำบลห้วยแห้ง":          (15.152, 99.524),
    "ตำบลหนองบ่มกล้วย":      (15.080, 99.480),
    "ตำบลบ้านใหม่คลองเคียน":  (15.188, 99.775),
    # อำเภอลานสัก
    "ตำบลลานสัก":            (15.406, 99.705),
    "ตำบลทุ่งนางาม":          (15.348, 99.651),
    "ตำบลน้ำรอบ":            (15.452, 99.765),
    "ตำบลประดู่ยืน":          (15.326, 99.726),
    "ตำบลป่าอ้อ":             (15.483, 99.693),
    "ตำบลระบำ":              (15.274, 99.642),
    # อำเภอหนองฉาง
    "ตำบลทุ่งโพ":             (15.412, 99.801),
    "ตำบลเขากวางทอง":         (15.280, 99.912),
    "ตำบลเขาบางแกรก":         (15.365, 99.925),
    # อำเภอห้วยคต
    "ตำบลทองหลาง":            (15.290, 99.614),
    "ตำบลห้วยคต":             (15.234, 99.547),
    "ตำบลสุขฤทัย":            (15.178, 99.482),
}

_AMPHOE_COORDS: dict[str, tuple[float, float]] = {
    "อำเภอบ้านไร่":  (15.047, 99.629),
    "บ้านไร่":       (15.047, 99.629),
    "อำเภอลานสัก":   (15.406, 99.705),
    "ลานสัก":        (15.406, 99.705),
    "อำเภอหนองฉาง":  (15.336, 99.857),
    "หนองฉาง":       (15.336, 99.857),
    "อำเภอห้วยคต":   (15.234, 99.547),
    "ห้วยคต":        (15.234, 99.547),
    "ล่วงหน้าในเขต":  (15.047, 99.629),
}


def resolve_thai_coords(amphoe: str, tambon: str) -> tuple[float, float]:
    """Return (lat, lon) for a Thai sub-district name.

    Looks up tambon first, then amphoe, then falls back to Uthai Thani centre.
    """
    if tambon in _TAMBON_COORDS:
        return _TAMBON_COORDS[tambon]
    if amphoe in _AMPHOE_COORDS:
        return _AMPHOE_COORDS[amphoe]
    return (15.384, 100.029)  # Uthai Thani province centre


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------


@st.cache_data
def load_small_party() -> pd.DataFrame:
    """Load small_party.csv.

    Returns a DataFrame with columns including 'Party' and 'small'
    (1.0 = small/no-name party, 0.0 = established party).
    """
    if not _SMALL_PARTY_CSV.exists():
        st.warning(f"Data file not found: {_SMALL_PARTY_CSV}")
        return pd.DataFrame()

    df = pd.read_csv(_SMALL_PARTY_CSV, index_col=0)
    df["small"] = pd.to_numeric(df["small"], errors="coerce").fillna(0.0)
    return df


@st.cache_data
def load_suspect() -> pd.DataFrame:
    """Load suspect.csv.

    Returns a DataFrame with columns: Amphoe, Tambon, Unit, Suspect.
    'Suspect' == 1.0 indicates a suspicious polling station.
    """
    if not _SUSPECT_CSV.exists():
        st.warning(f"Data file not found: {_SUSPECT_CSV}")
        return pd.DataFrame()

    df = pd.read_csv(_SUSPECT_CSV, index_col=0)
    df["Suspect"] = pd.to_numeric(df["Suspect"], errors="coerce").fillna(0.0)
    return df


@st.cache_data
def load_merged_parties() -> pd.DataFrame:
    """Load merged_parties_with_ratio.csv.

    Returns a DataFrame with columns including 'party_name', 'z_score',
    'is_outlier', and 'category'. The file has a UTF-8 BOM.
    """
    if not _MERGED_PARTIES_CSV.exists():
        st.warning(f"Data file not found: {_MERGED_PARTIES_CSV}")
        return pd.DataFrame()

    df = pd.read_csv(_MERGED_PARTIES_CSV, encoding="utf-8-sig")
    # Coerce boolean column in case it was stored as string
    if "is_outlier" in df.columns:
        df["is_outlier"] = df["is_outlier"].map(
            lambda v: str(v).strip().lower() in {"true", "1", "yes"}
            if not isinstance(v, bool)
            else v
        )
    return df


@st.cache_data
def load_bhumjaithai_ratio() -> pd.DataFrame:
    """Load all_districts_bhumjaithai_ratio.csv.

    Returns a DataFrame with columns: amphoe, tambon, bhumjaithai_votes,
    total_valid_ballots, ratio. The file has a UTF-8 BOM.
    """
    if not _BHUMJAITHAI_RATIO_CSV.exists():
        st.warning(f"Data file not found: {_BHUMJAITHAI_RATIO_CSV}")
        return pd.DataFrame()

    df = pd.read_csv(_BHUMJAITHAI_RATIO_CSV, encoding="utf-8-sig")
    df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# GeoJSON / spatial loader
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Fetching Thailand GeoJSON boundaries...")
def load_thailand_geojson() -> Optional[dict]:
    """Attempt to fetch a GeoJSON of Thailand province/district boundaries.

    Tries the primary URL first, then a fallback. Returns None if both fail
    so callers can gracefully degrade to table displays.
    """
    try:
        import requests  # noqa: PLC0415

        for url in (_GEOJSON_URL, _GEOJSON_FALLBACK_URL):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return data
            except Exception:  # noqa: BLE001
                continue

        return None
    except ImportError:
        return None


@st.cache_data
def load_geo_dataframe() -> Optional[pd.DataFrame]:
    """Build a flat DataFrame of (amphoe, tambon, lat, lon) from GeoJSON.

    Parses the GeoJSON features to extract centroid coordinates and
    administrative name strings for join with tabular data. Returns None
    if GeoJSON is unavailable.

    The Thailand GeoJSON typically encodes names in English. Thai names
    from the CSVs will be joined on a best-effort basis after normalization.
    """
    geojson = load_thailand_geojson()
    if geojson is None:
        return None

    rows: list[dict] = []

    features = geojson.get("features", [])
    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        if not geometry:
            continue

        geo_type = geometry.get("type", "")
        coordinates = geometry.get("coordinates", [])

        # Extract a representative centroid coordinate
        lat, lon = _extract_centroid(geo_type, coordinates)
        if lat is None:
            continue

        rows.append(
            {
                "geo_name": props.get("name", props.get("NAME", "")),
                "lat": lat,
                "lon": lon,
            }
        )

    if not rows:
        return None

    return pd.DataFrame(rows)


def _extract_centroid(geo_type: str, coordinates) -> tuple[Optional[float], Optional[float]]:
    """Return (lat, lon) centroid from GeoJSON geometry coordinates."""
    try:
        if geo_type == "Point":
            return coordinates[1], coordinates[0]
        elif geo_type in ("Polygon", "MultiPolygon"):
            # Flatten nested coordinate lists to find mean position
            flat = _flatten_coords(coordinates)
            if not flat:
                return None, None
            lons = [c[0] for c in flat]
            lats = [c[1] for c in flat]
            return sum(lats) / len(lats), sum(lons) / len(lons)
        elif geo_type == "MultiPoint":
            if coordinates:
                return coordinates[0][1], coordinates[0][0]
    except (IndexError, TypeError, ZeroDivisionError):
        pass
    return None, None


def _flatten_coords(coords) -> list:
    """Recursively flatten nested coordinate arrays."""
    if not coords:
        return []
    # If first element is a number, this is a single coord pair
    if isinstance(coords[0], (int, float)):
        return [coords]
    result = []
    for item in coords:
        result.extend(_flatten_coords(item))
    return result
