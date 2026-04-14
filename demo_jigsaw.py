"""
Demo: Jigsaw Validation Engine Integration

This script demonstrates how the election_pipeline would call the new
validation module without any coupling between the two codebases.

The "Jigsaw" interface is:
    validator = ElectionValidator(master_candidates, master_parties)
    cleaned_data, flags = validator.validate(raw_data)

Run with:
    python demo_jigsaw.py
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd

from validation.engine import ElectionValidator
from validation.formatters import prepare_df_for_csv, prepare_data_for_json


# ---------------------------------------------------------------------------
# Step 1: Define master reference lists (normally loaded from a DB or file)
# ---------------------------------------------------------------------------

master_candidates = [
    {"name": "สมชาย ใจดี",   "party": "พรรค A"},
    {"name": "สมหญิง รักชาติ", "party": "พรรค B"},
    {"name": "วิชาญ แก้วมณี", "party": "พรรค C"},
]

master_parties = ["พรรค A", "พรรค B", "พรรค C", "พรรค D"]


# ---------------------------------------------------------------------------
# Step 2: Simulate a raw record as produced by election_pipeline
# (Some values are OCR failures represented as sentinels)
# ---------------------------------------------------------------------------

raw_data = {
    "station_id": "BKK-101-03",
    "scores": {
        "สมชาย ใจดี":   "๒๓๕",   # Thai digits — should parse to 235
        "สมหญิง รักชาติ": "198",    # Arabic digits — normal
        # วิชาญ แก้วมณี is absent (OCR missed entire row)
        "ผู้ไม่รู้จัก":    "5",     # Unknown candidate — triggers name mismatch
    },
    "party_scores": {
        "พรรค A": "200",
        "พรรค B": "150",
        # พรรค C and พรรค D absent
    },
    "valid_ballots": "433",
    "invalid_ballots": "-",    # OCR failure sentinel
    "no_vote_ballots": ".",    # OCR failure sentinel
    "ballots_used": "500",
}


# ---------------------------------------------------------------------------
# Step 3: Run validation (the Jigsaw call)
# ---------------------------------------------------------------------------

print("=" * 60)
print("JIGSAW VALIDATION DEMO")
print("=" * 60)

validator = ElectionValidator(master_candidates, master_parties)
cleaned_data, flags = validator.validate(raw_data)


# ---------------------------------------------------------------------------
# Step 4: Inspect cleaned data
# ---------------------------------------------------------------------------

print("\n--- Cleaned Scores ---")
for candidate, score in cleaned_data["scores"].items():
    nan_marker = " [NaN — MISSING]" if (isinstance(score, float) and np.isnan(score)) else ""
    print(f"  {candidate}: {score}{nan_marker}")

print("\n--- Cleaned Party Scores ---")
for party, score in cleaned_data["party_scores"].items():
    nan_marker = " [NaN — MISSING]" if (isinstance(score, float) and np.isnan(score)) else ""
    print(f"  {party}: {score}{nan_marker}")

print("\n--- Ballot Summary ---")
for field in ("valid_ballots", "invalid_ballots", "no_vote_ballots", "ballots_used"):
    val = cleaned_data[field]
    nan_marker = " [NaN — MISSING]" if (isinstance(val, float) and np.isnan(val)) else ""
    print(f"  {field}: {val}{nan_marker}")


# ---------------------------------------------------------------------------
# Step 5: Inspect flags
# ---------------------------------------------------------------------------

print("\n--- Validation Flags ---")
for flag, value in flags.items():
    print(f"  {flag}: {value}")


# ---------------------------------------------------------------------------
# Step 6: CSV export — NaN appears as "MISSING"
# ---------------------------------------------------------------------------

print("\n--- CSV Export (NaN -> 'MISSING') ---")
rows = [
    {"candidate": name, "score": score}
    for name, score in cleaned_data["scores"].items()
]
df = pd.DataFrame(rows)
csv_output = prepare_df_for_csv(df)
print(csv_output)


# ---------------------------------------------------------------------------
# Step 7: JSON export — NaN appears as null
# ---------------------------------------------------------------------------

print("--- JSON Export (NaN -> null) ---")
combined = {
    "station_id": cleaned_data.get("station_id", raw_data.get("station_id")),
    "scores": cleaned_data["scores"],
    "flags": flags,
}
json_safe = prepare_data_for_json(combined)
print(json.dumps(json_safe, ensure_ascii=False, indent=2))

print("\n" + "=" * 60)
print("Demo complete. Zero modifications to election_pipeline/.")
print("=" * 60)
