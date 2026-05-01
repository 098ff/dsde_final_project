
## Election Insights Dashboard

A second Streamlit app in `visualize/` presents three analytical insights derived from the OCR-validated election data.

```bash
streamlit run visualize/app.py
```

### Tab 1 — Vote Buying Detection (การซื้อเสียง)

**Hypothesis:** When vote buying occurs, voters mark the same party number on both the constituency (แบ่งเขต) and party-list (บัญชีรายชื่อ) ballots. This causes small/no-name parties to receive disproportionately high party-list votes at certain polling stations.

**Method:**
1. Parties are scored on 8 variables — MP ratio (district & party-list), branch count, representatives, members (log-scaled), Facebook followers (log-scaled), Google Trends (30-day sum), and historical seat wins (binary ≥ 10 seats).
2. All variables are Min-Max scaled to [0, 1], then reduced to a single **PCA Index** via PCA. Parties with PCA Index < 0.5 are classified as *small / no-name* (`small_party.csv`).
3. Any polling unit where a small party received **> 6.5%** of party-list votes is flagged as suspicious (`suspect.csv`).

**Displays:**
- Key metrics — total parties analysed, small-party count, suspicious station count
- Sortable table of small parties with PCA and scaled feature values
- Map of suspicious polling stations across Uthai Thani sub-districts

### Tab 2 — Outlier Detection

**Method:** Z-score analysis on the list/constituency vote ratio (`merged_parties_with_ratio.csv`). Parties with |z| > 2 are flagged as statistical outliers — their party-list vote share is anomalously high or low relative to the field.

**Displays:**
- Summary metrics — outlier count, mean and max z-score
- Scatter plot of z-scores across all parties, coloured by outlier status
- Filterable table of flagged parties with vote counts and ratio

### Tab 3 — Bhumjaithai Loyalty Map (แผนที่ความจงรักภักดี)

**Metric:** For each sub-district (ตำบล), the loyalty ratio is:

```
ratio = Bhumjaithai party-list votes / total valid party-list ballots
```

**Displays:**
- Summary metrics — tambon count, mean and peak loyalty ratio
- Scatter map coloured in shades of blue (light = low, dark = high Bhumjaithai support) across the 25 tambons in อ.บ้านไร่, อ.ลานสัก, อ.หนองฉาง, and อ.ห้วยคต
- Bar chart fallback with the same colour encoding when the map is unavailable

### Data files

All input files live in `visualize/data/` and are produced by the analysis notebooks in `visualization_prep_insight*/`.

| File | Source | Used by |
|---|---|---|
| `small_party.csv` | PCA party classification | Tab 1 |
| `suspect.csv` | Threshold detection (> 6.5%) | Tab 1 |
| `merged_parties_with_ratio.csv` | Z-score analysis | Tab 2 |
| `all_districts_bhumjaithai_ratio.csv` | District-level aggregation | Tab 3 |

### Dependencies

```bash
pip install visualize/requirements.txt
# streamlit, pandas, pydeck, geopandas, requests, altair
```

---