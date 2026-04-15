"""
Structural Auditor for Thai Election OCR Results.

Checks whether every (Tambon, Unit) station pair has both a "Constituency"
and a "Party List" form in the processed records. Stations missing one or
both form types are written to a CSV report for manual follow-up.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

import pandas as pd

from validation.form_identifier import FORM_CONSTITUENCY, FORM_PARTY_LIST

# ---------------------------------------------------------------------------
# Required form types every station must have
# ---------------------------------------------------------------------------

_REQUIRED_FORMS = {FORM_CONSTITUENCY, FORM_PARTY_LIST}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def audit_units(records: List[Dict]) -> List[Dict]:
    """Identify stations that are missing one or more election form types.

    Each record is expected to contain at least:
      - ``"Tambon"``    : sub-district name (str)
      - ``"Unit"``      : station number (str or int)
      - ``"form_type"`` : one of ``"Constituency"``, ``"Party List"``, or
                          ``"Unknown"``

    Records with ``form_type == "Unknown"`` are included in the grouping but
    will not satisfy either required form slot.

    Args:
        records: List of dicts representing processed OCR records.

    Returns:
        A list of dicts describing each missing form, with keys:
          - ``"Tambon"``        : sub-district
          - ``"Unit"``          : station number
          - ``"missing_form"``  : the form type that was not found
    """
    # Group form types seen per station key
    seen: dict[tuple, set] = defaultdict(set)
    for rec in records:
        key = (rec.get("Tambon", ""), rec.get("Unit", ""))
        form = rec.get("form_type", "")
        seen[key].add(form)

    missing_items: list[dict] = []
    for (tambon, unit), forms_present in seen.items():
        for required_form in sorted(_REQUIRED_FORMS):  # sorted for deterministic output
            if required_form not in forms_present:
                missing_items.append(
                    {
                        "Tambon": tambon,
                        "Unit": unit,
                        "missing_form": required_form,
                    }
                )

    return missing_items


def generate_missing_report(missing_items: List[Dict], output_path: str) -> None:
    """Write missing-unit findings to a CSV file.

    Creates a CSV with columns ``Tambon``, ``Unit``, ``missing_form``.
    If *missing_items* is empty the file is still written (with only the
    header row) so downstream consumers can rely on its existence.

    Args:
        missing_items: List of dicts as returned by :func:`audit_units`.
        output_path:   Absolute or relative path for the output CSV file.
    """
    df = pd.DataFrame(
        missing_items,
        columns=["Tambon", "Unit", "missing_form"],
    )
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
