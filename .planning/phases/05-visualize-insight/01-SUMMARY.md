---
phase: "05"
plan: "01"
subsystem: visualize
tags: [streamlit, visualization, vote-buying, outlier-detection, pydeck, choropleth]
dependency_graph:
  requires:
    - visualize/data/small_party.csv
    - visualize/data/suspect.csv
    - visualize/data/merged_parties_with_ratio.csv
    - visualize/data/all_districts_bhumjaithai_ratio.csv
  provides:
    - visualize/app.py
    - visualize/data_loader.py
    - visualize/tabs/vote_buying.py
    - visualize/tabs/outliers.py
    - visualize/tabs/loyalty_map.py
    - visualize/requirements.txt
  affects: []
tech_stack:
  added:
    - streamlit>=1.32.0
    - pydeck>=0.8.0
    - geopandas>=0.14.0
    - requests>=2.31.0
  patterns:
    - "@st.cache_data for all CSV and GeoJSON loaders"
    - "Graceful degradation: pydeck map -> table/bar chart fallback"
    - "Modular tab architecture: tabs/*.py with render_* functions"
key_files:
  created:
    - visualize/app.py
    - visualize/data_loader.py
    - visualize/tabs/__init__.py
    - visualize/tabs/vote_buying.py
    - visualize/tabs/outliers.py
    - visualize/tabs/loyalty_map.py
    - visualize/requirements.txt
  modified: []
decisions:
  - "GeoJSON loaded from public GitHub URL with second fallback URL; returns None on failure so all map tabs degrade gracefully"
  - "BOM-aware CSV reading (utf-8-sig) for merged_parties_with_ratio.csv and all_districts_bhumjaithai_ratio.csv"
  - "Altair preferred for scatter/bar charts; native st.scatter_chart/st.bar_chart as fallback if altair not installed"
  - "Approximate Uthai Thani coordinates used as default map centre for suspect/ratio data (Ban Rai district origin)"
  - "tabs/ is a Python package with __init__.py; app.py imports render_* functions directly"
metrics:
  duration: "~4 minutes"
  completed_date: "2026-04-30"
  tasks_completed: 5
  tasks_total: 5
  files_created: 7
---

# Phase 05 Plan 01: Create Modular Streamlit Visualization Dashboard — Summary

**One-liner:** Modular Streamlit dashboard (3 tabs) for vote buying, outlier detection, and Bhumjaithai loyalty map using pydeck + altair with GeoJSON fallback.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Setup project structure (requirements.txt + data_loader.py) | e26b45f | visualize/requirements.txt, visualize/data_loader.py |
| 2 | Vote Buying tab (vote_buying.py) | ec7abc4 | visualize/tabs/__init__.py, visualize/tabs/vote_buying.py |
| 3 | Outlier Detection tab (outliers.py) | cb870dd | visualize/tabs/outliers.py |
| 4 | Bhumjaithai Loyalty Map tab (loyalty_map.py) | e707dd4 | visualize/tabs/loyalty_map.py |
| 5 | Entry point app.py with 3-tab navigation | 5d3c204 | visualize/app.py |

## Architecture

```
visualize/
├── app.py              # Entry point: st.set_page_config + 3 st.tabs
├── data_loader.py      # @st.cache_data loaders for 4 CSVs + GeoJSON
├── requirements.txt    # streamlit, pandas, pydeck, geopandas, requests
└── tabs/
    ├── __init__.py
    ├── vote_buying.py  # render_vote_buying_tab(small_df, suspect_df, geo_df)
    ├── outliers.py     # render_outliers_tab(merged_df)
    └── loyalty_map.py  # render_loyalty_tab(ratio_df, geo_df)
```

## Key Capabilities

### Tab 1: Vote Buying (การซื้อเสียง)
- Metrics: total parties analysed, small party count, suspicious station count
- Small party table: all parties where PCA_Index < 50%, sorted by PCA_Index
- Suspect stations: pydeck ScatterplotLayer map (red dots) with coordinate enrichment from GeoJSON; fallback to interactive table

### Tab 2: Outlier Detection
- Metrics: total parties, outlier count with percentage, max z-score
- Outlier party table sorted by z-score descending
- Altair scatter chart: party index vs z-score, red = outlier / blue = normal, with z=±3 threshold lines; fallback to st.scatter_chart

### Tab 3: Bhumjaithai Loyalty Map
- Metrics: Tambon count, mean ratio, max ratio with location
- pydeck ScatterplotLayer with blue colour gradient (light = low loyalty, dark = high loyalty)
- Coordinate enrichment via GeoJSON with hardcoded Uthai Thani fallback (approximate Ban Rai district coordinates)
- Altair horizontal bar chart fallback coloured with blues colour scheme

## Data Loading Strategy

| Function | CSV | Encoding | Notes |
|----------|-----|----------|-------|
| `load_small_party()` | small_party.csv | utf-8 | index_col=0; coerce 'small' to float |
| `load_suspect()` | suspect.csv | utf-8 | index_col=0; coerce 'Suspect' to float |
| `load_merged_parties()` | merged_parties_with_ratio.csv | utf-8-sig | BOM-aware; is_outlier coerced to bool |
| `load_bhumjaithai_ratio()` | all_districts_bhumjaithai_ratio.csv | utf-8-sig | BOM-aware; ratio coerced to float |
| `load_thailand_geojson()` | network | — | GET with 10s timeout; 2 URL fallbacks; returns None on failure |
| `load_geo_dataframe()` | derived | — | Parses GeoJSON features to flat lat/lon table |

## Deviations from Plan

### Auto-added enhancements

**1. [Rule 2 - Missing functionality] Added tabs/__init__.py**
- Found during: Task 2
- Issue: Python requires `__init__.py` for `tabs/` to be importable as a package when using `from tabs.vote_buying import ...`
- Fix: Created `visualize/tabs/__init__.py`
- Files modified: visualize/tabs/__init__.py
- Commit: ec7abc4

**2. [Rule 2 - Missing functionality] Added altair fallback for all chart tabs**
- Found during: Tasks 3 and 4
- Issue: pydeck is only useful for maps; bar/scatter charts require altair or native st.* widgets for proper rendering without external deps
- Fix: Added try/except altair import with graceful fallback to st.scatter_chart / st.bar_chart
- Files modified: visualize/tabs/outliers.py, visualize/tabs/loyalty_map.py

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: outbound_http | visualize/data_loader.py | load_thailand_geojson() makes GET requests to raw.githubusercontent.com URLs; timeout=10s, read-only, no auth |

The outbound request is display-only (GeoJSON boundaries for map rendering). It is not in the original plan's threat model but poses minimal risk: failure returns None and UI degrades gracefully to table display.

## Known Stubs

None — all tabs render real data from the 4 CSV files. Maps degrade to tables/bar charts (not stubs) when GeoJSON/pydeck is unavailable.

## Self-Check: PASSED

Files verified:
- FOUND: visualize/app.py
- FOUND: visualize/data_loader.py
- FOUND: visualize/tabs/__init__.py
- FOUND: visualize/tabs/vote_buying.py
- FOUND: visualize/tabs/outliers.py
- FOUND: visualize/tabs/loyalty_map.py
- FOUND: visualize/requirements.txt

Commits verified:
- e26b45f: feat(05-01): add requirements.txt and data_loader.py
- ec7abc4: feat(05-01): add vote_buying tab
- cb870dd: feat(05-01): add outliers tab
- e707dd4: feat(05-01): add loyalty_map tab
- 5d3c204: feat(05-01): add app.py entry point
