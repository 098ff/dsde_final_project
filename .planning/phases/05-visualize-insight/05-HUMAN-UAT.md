---
status: partial
phase: 05-visualize-insight
source: [05-VERIFICATION.md]
started: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Full App Launch
expected: Run `streamlit run visualize/app.py` — dashboard title visible, all three tabs (Vote Buying, Outlier Detection, Bhumjaithai Loyalty) load without error and each renders metrics + chart.
result: [pending]

### 2. Loyalty Map Colour Gradient
expected: Open "Bhumjaithai Loyalty" tab — blue colour variation is visually apparent between high- and low-ratio Tambons (darker blue = higher Bhumjaithai support, clearly distinguishable).
result: [pending]

### 3. Vote Buying Map / Fallback
expected: Open "Vote Buying" tab — either the pydeck map (red dots) or the fallback table appears for the 279 suspect stations. All suspect stations visible in one of the two display paths.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
