---
phase: 05-visualize-insight
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - visualize/app.py
  - visualize/data_loader.py
  - visualize/tabs/__init__.py
  - visualize/tabs/vote_buying.py
  - visualize/tabs/outliers.py
  - visualize/tabs/loyalty_map.py
  - visualize/requirements.txt
findings:
  critical: 3
  warning: 5
  info: 2
  total: 10
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-04-30T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Seven files were reviewed covering the Streamlit dashboard entry point, a shared data loader, three tab-rendering modules, and requirements. The overall structure is clean and readable, with sensible fallback logic throughout. However, three blockers were found: (1) `sort_values` is called on a column name that may have been filtered out of the display list, causing a guaranteed `KeyError` crash when optional CSV columns are absent; (2) `str.contains` is called without `regex=False`, so any Tambon or Amphoe name containing regex special characters (e.g., `[`, `+`, `(`) raises an `ArrowInvalid`/`re.error` exception at runtime; and (3) the primary GeoJSON URL is a confirmed 404 (wrong repository), meaning the primary data source for geographic features silently fails every deployment. Additional warnings cover NaN propagation into an integer-coercing colour function, `idxmax()` crashing on all-NaN ratio columns, an undeclared `altair` dependency, and pervasive broad exception suppression that masks logic bugs.

---

## Critical Issues

### CR-01: `sort_values` on a column that may be absent after filtering — guaranteed KeyError

**File:** `visualize/tabs/vote_buying.py:109-112`

**Issue:** `display_cols_small` is built by filtering a candidate list to only columns that exist in `small_parties`. `"PCA_Index"` is included in the filter guard. However, `sort_values("PCA_Index")` is then called unconditionally on whatever subset survived the filter. If `PCA_Index` is absent from the CSV (it was filtered out), the `sort_values` call raises `KeyError: 'PCA_Index'` and crashes the tab. The same pattern occurs in `visualize/tabs/outliers.py:77` where `sort_values("z_score", ascending=False)` is called after `display_cols` is also filtered, and `z_score` may not be present.

```python
# vote_buying.py lines 109-112
display_cols_small = [c for c in display_cols_small if c in small_parties.columns]

st.dataframe(
    small_parties[display_cols_small].sort_values("PCA_Index")  # KeyError if PCA_Index absent
    ...
)

# outliers.py lines 71-77
display_cols = [
    c for c in
    ["party_name", ..., "z_score", "category"]
    if c in outlier_df.columns
]
st.dataframe(
    outlier_df[display_cols].sort_values("z_score", ascending=False)  # KeyError if z_score absent
    ...
)
```

**Fix:** Guard the sort key or provide a fallback:
```python
# vote_buying.py
sort_col = "PCA_Index" if "PCA_Index" in display_cols_small else display_cols_small[0] if display_cols_small else None
df_to_show = small_parties[display_cols_small]
if sort_col:
    df_to_show = df_to_show.sort_values(sort_col)
st.dataframe(df_to_show.reset_index(drop=True), ...)

# outliers.py — same pattern
sort_col = "z_score" if "z_score" in display_cols else None
df_to_show = outlier_df[display_cols]
if sort_col:
    df_to_show = df_to_show.sort_values(sort_col, ascending=False)
st.dataframe(df_to_show.reset_index(drop=True), ...)
```

---

### CR-02: `str.contains` without `regex=False` — crashes on special-character place names

**File:** `visualize/tabs/vote_buying.py:257,261` and `visualize/tabs/loyalty_map.py:207,209`

**Issue:** All four `str.contains` calls pass the raw Tambon/Amphoe string directly as a regex pattern without `regex=False`. If any Thai place name (read from CSV data) contains a regex metacharacter — `[`, `]`, `(`, `)`, `+`, `*`, `?`, `.` — the call raises `ArrowInvalid: Invalid regular expression` (when using the Arrow-backed pandas StringDtype) or `re.error`. This is a data-driven crash that will occur in production when an unexpected place name is encountered. Verified: `str.contains("[Ban", na=False)` raises `ArrowInvalid` in the test environment.

```python
# vote_buying.py:257 — WRONG
match = geo_df[geo_df["geo_name"].str.contains(tambon, na=False, case=False)]

# loyalty_map.py:207 — WRONG
match = geo_df[geo_df["geo_name"].str.contains(tambon, na=False, case=False)]
```

**Fix:** Add `regex=False` to all four calls:
```python
match = geo_df[
    geo_df["geo_name"].str.contains(tambon, na=False, case=False, regex=False)
]
if match.empty:
    match = geo_df[
        geo_df["geo_name"].str.contains(amphoe, na=False, case=False, regex=False)
    ]
```

Apply the same change to both occurrences in `loyalty_map.py:207,209`.

---

### CR-03: Primary GeoJSON URL is a confirmed 404

**File:** `visualize/data_loader.py:31-34`

**Issue:** `_GEOJSON_URL` points to `https://raw.githubusercontent.com/cvdlab/react-leaflet-distance-layer/master/examples/data/thailand.json`. This URL returns HTTP 404 — the file does not exist in that repository. Every invocation of `load_thailand_geojson` will fail on the primary URL and fall through to the fallback. Since the 404 is swallowed silently inside the broad `except Exception`, users see no error. If the fallback URL also becomes unavailable (e.g., rate limit, private network), the map silently degrades with no actionable message to the operator. The current fallback URL (`apisit/thailand.json`) appears valid but is undocumented as "primary."

```python
# data_loader.py:31-34
_GEOJSON_URL = (
    "https://raw.githubusercontent.com/cvdlab/react-leaflet-distance-layer/"
    "master/examples/data/thailand.json"   # 404 — wrong repo
)
```

**Fix:** Remove the dead primary URL and promote the fallback to primary. Optionally log a warning when both URLs fail:
```python
_GEOJSON_URL = (
    "https://raw.githubusercontent.com/apisit/thailand.json/master/thailand.json"
)
# Remove _GEOJSON_FALLBACK_URL or replace with a second genuinely valid mirror.
```

---

## Warnings

### WR-01: `_blue_colour` crashes with `ValueError` when `ratio` column contains NaN

**File:** `visualize/tabs/loyalty_map.py:136-143`

**Issue:** `load_bhumjaithai_ratio` coerces the `ratio` column with `errors="coerce"` (line 114 of `data_loader.py`) but does not `fillna`. Any NaN value that survives into `_try_render_pydeck_map` reaches `_blue_colour`, which calls `int(...)` on a NaN-derived float. `int(float('nan'))` raises `ValueError: cannot convert float NaN to integer`. The broad `except Exception` at line 181 catches this and silently falls back to the bar chart — so the map never renders when any ratio row is NaN. This is a silent failure path.

```python
# data_loader.py:114 — coerces but does not fill
df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce")  # NaN rows left unfilled

# loyalty_map.py:136-142 — NaN explodes here
def _blue_colour(r: float) -> list[int]:
    norm = (r - ratio_min) / ratio_range
    blue = int(139 + (1 - norm) * (230 - 139))  # ValueError if r is NaN
```

**Fix:** Drop or fill NaN ratios before passing to the colour function:
```python
# In _try_render_pydeck_map, after _enrich_with_coords:
enriched = enriched.dropna(subset=["ratio"])
if enriched.empty:
    return False
```
Or fill in `data_loader.py`: `df["ratio"] = pd.to_numeric(df["ratio"], errors="coerce").fillna(0.0)`.

---

### WR-02: `idxmax()` raises `ValueError` when `ratio` column is all-NaN

**File:** `visualize/tabs/loyalty_map.py:69-71`

**Issue:** `ratio_df["ratio"].idxmax()` uses `skipna=True` by default, which is safe for partial NaN. However, if the entire `ratio` column consists of NaN values (e.g., corrupted CSV), `idxmax()` raises `ValueError: Encountered all NA values`. This crashes tab rendering before any try/except can catch it, because the call is at the top-level metric block.

```python
# loyalty_map.py:69-71
delta=ratio_df.loc[ratio_df["ratio"].idxmax(), "tambon"]
if "ratio" in ratio_df.columns and "tambon" in ratio_df.columns
else "",
```

**Fix:** Guard with a `skipna` check:
```python
ratio_valid = ratio_df["ratio"].dropna()
max_tambon = (
    ratio_df.loc[ratio_valid.idxmax(), "tambon"]
    if not ratio_valid.empty and "tambon" in ratio_df.columns
    else ""
)
delta = max_tambon
```

---

### WR-03: Empty-string Tambon/Amphoe matches all geo rows — assigns wrong coordinates

**File:** `visualize/tabs/vote_buying.py:256-266` and `visualize/tabs/loyalty_map.py:205-215`

**Issue:** When a CSV row has a missing or empty `Tambon` or `Amphoe` value, `str(row.get("Tambon", ""))` returns `""`. `str.contains("", ...)` matches every row in `geo_df`. The code then takes `iloc[0]` — the first GeoJSON feature in memory — and assigns those coordinates to the station. This silently places suspicious polling stations (or Tambon loyalty scores) at arbitrary geographic positions, corrupting map output without any warning.

**Fix:** Skip the geo lookup when the key is an empty string:
```python
tambon = str(row.get("Tambon", "")).strip()
amphoe = str(row.get("Amphoe", "")).strip()

match = pd.DataFrame()
if tambon:
    match = geo_df[geo_df["geo_name"].str.contains(tambon, na=False, case=False, regex=False)]
if match.empty and amphoe:
    match = geo_df[geo_df["geo_name"].str.contains(amphoe, na=False, case=False, regex=False)]
```

---

### WR-04: `altair` used in two tabs but absent from `requirements.txt`

**File:** `visualize/requirements.txt` (cross-referenced with `visualize/tabs/outliers.py:142` and `visualize/tabs/loyalty_map.py:258`)

**Issue:** Both `outliers.py` and `loyalty_map.py` attempt `import altair as alt` for chart rendering. `altair` is not listed in `requirements.txt`. Streamlit bundles a compatible `altair` in its own dependencies, so the import often succeeds — but this is an implicit transitive dependency. A Streamlit upgrade that drops or pins altair to an incompatible version, or a minimal install without Streamlit extras, will silently fall back to degraded (tooltip-free) charts with no warning to the operator.

**Fix:** Add an explicit pinned entry to `requirements.txt`:
```
altair>=5.0.0
```

---

### WR-05: Pervasive bare `except Exception` suppresses all map rendering errors silently

**File:** `visualize/tabs/vote_buying.py:221-222` and `visualize/tabs/loyalty_map.py:181-182`

**Issue:** Both `_render_suspect_map_or_table` and `_try_render_pydeck_map` wrap the entire map rendering path in `except Exception: pass` / `return False`. This means programming errors (attribute errors, wrong column names, pydeck API changes), network errors, and data shape bugs are all silently discarded. The user sees a fallback table or bar chart with a benign message, and the operator has no log trace indicating something broke. The `# noqa: BLE001` comments acknowledge the pattern but do not mitigate it.

**Fix:** At minimum, log the exception before falling back:
```python
except Exception as exc:  # noqa: BLE001
    st.warning(f"Map rendering failed ({type(exc).__name__}); showing table instead.")
    # or use Python logging: logging.warning("Map render failed", exc_info=True)
```

---

## Info

### IN-01: `geopandas` listed in `requirements.txt` but never imported or used

**File:** `visualize/requirements.txt:4`

**Issue:** `geopandas>=0.14.0` is declared as a dependency but no code in the `visualize/` package imports or uses it. GeoJSON parsing is done manually via `requests` + `json`. `geopandas` is a heavy dependency (GDAL/PROJ chain) that significantly increases install time and binary size without benefit.

**Fix:** Remove the `geopandas` line from `requirements.txt` unless a future feature is planned.

---

### IN-02: Metric label "Suspicious Polling Stations" shows `sum()` of an already-filtered column — redundant but harmless

**File:** `visualize/tabs/vote_buying.py:79-83`

**Issue:** `suspect_stations` is already filtered to `Suspect == 1.0`, so `suspect_stations["Suspect"].sum()` equals `len(suspect_stations)` (each value is 1.0). The `sum()` call is semantically misleading — it looks like it might be counting something different from `len`. It will also produce a float display value (`int()` wraps it correctly, but only because the values happen to be 1.0).

**Fix:** Replace with `len(suspect_stations)` for clarity:
```python
col3.metric(
    label="Suspicious Polling Stations",
    value=len(suspect_stations),
    ...
)
```

---

_Reviewed: 2026-04-30T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
