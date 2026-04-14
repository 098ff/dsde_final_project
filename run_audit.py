import sys
import pandas as pd
sys.path.insert(0, "election_pipeline")
from validation.structural_auditor import audit_units, generate_missing_report

df = pd.read_csv("election_pipeline/output_data/master_summary_log.csv", encoding="utf-8-sig")

records = [
    {
        "Tambon": row["tambon"],
        "Unit":   str(row["unit"]),
        "form_type": "Party List" if row["type"] == "บัญชีรายชื่อ" else "Constituency",
    }
    for _, row in df.iterrows()
]

missing = audit_units(records)
generate_missing_report(missing, "election_pipeline/output_data/missing_units.csv")

if missing:
    print(f"⚠ {len(missing)} missing form(s) — see output_data/missing_units.csv")
    for item in missing:
        print(f"  {item['Tambon']} / Unit {item['Unit']} — missing {item['missing_form']}")
else:
    print("✓ All stations have both form types")
