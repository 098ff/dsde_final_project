"""
Data loader for the Election Insights Streamlit application.

All loader functions use @st.cache_data to avoid re-reading CSV files on
every interaction.
"""

from __future__ import annotations

from pathlib import Path

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


# ---------------------------------------------------------------------------
# Thai location lookup
# ---------------------------------------------------------------------------

_TAMBON_COORDS: dict[str, tuple[float, float]] = {
    "ตำบลบ้านไร่":                       (15.107087, 99.634135),
    "ตำบลคอกควาย":                       (15.23317, 99.389511),
    "ตำบลหนองจอก":                       (15.046893, 99.689832),
    "ตำบลเจ้าวัด":                       (15.149801, 99.445044),
    "ตำบลวังหิน":                        (15.282827, 99.717694),
    "ตำบลทัพหลวง":                       (15.050689, 99.600735),
    "ตำบลบ้านบึง":                       (15.029448, 99.556222),
    "ตำบลหูช้าง":                        (15.140354, 99.667549),
    "ตำบลเมืองการุ้ง":                   (15.185668, 99.689832),
    "ตำบลแก่นมะกรูด":                    (15.159935, 99.290317),
    "ตำบลห้วยแห้ง":                      (15.16825, 99.556222),
    "ตำบลหนองบ่มกล้วย":                  (15.090257, 99.756716),
    "ตำบลบ้านใหม่คลองเคียน":             (15.230143, 99.664764),
    "ตำบลลานสัก":                        (15.533594, 99.41172),
    "ตำบลทุ่งนางาม":                     (15.374756, 99.600735),
    "ตำบลน้ำรอบ":                        (15.550078, 99.567348),
    "ตำบลประดู่ยืน":                     (15.442343, 99.645271),
    "ตำบลป่าอ้อ":                        (15.401764, 99.511733),
    "ตำบลระบำ":                          (15.537375, 99.322921),
    "ตำบลทุ่งโพ":                        (15.367956, 99.756716),
    "ตำบลเขากวางทอง":                    (15.394052, 99.689832),
    "ตำบลเขาบางแกรก":                    (15.32553, 99.667549),
    "ตำบลห้วยคต":                        (15.259899, 99.578475),
    "ตำบลสุขฤทัย":                       (15.28018, 99.645271),
    "ตำบลทองหลาง":                       (15.3406, 99.4795),
}

_AMPHOE_COORDS: dict[str, tuple[float, float]] = {
    "อำเภอบ้านไร่":  (15.052, 99.879),
    "บ้านไร่":       (15.052, 99.879),
    "อำเภอลานสัก":   (15.424, 99.766),
    "ลานสัก":        (15.424, 99.766),
    "อำเภอหนองฉาง":  (15.333, 100.083),
    "หนองฉาง":       (15.333, 100.083),
    "อำเภอห้วยคต":   (15.173, 99.945),
    "ห้วยคต":        (15.173, 99.945),
    "ล่วงหน้าในเขต":  (15.052, 99.879),
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
