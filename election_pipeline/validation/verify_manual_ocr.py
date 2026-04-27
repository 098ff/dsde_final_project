"""
verify_manual_ocr.py
====================
Manual check verifier for OCR-processed Thai election data.

Performs two main checks:
1. STRUCTURE: Compares raw_pdf/ folder tree against verfied_ocr_data/,
   ensuring all unit folders are present and each has exactly
   summary_แบ่งเขต.csv and summary_บัญชีรายชื่อ.csv.
   (Skips ล่วงหน้านอกเขต* and ล่วงหน้าในเขต* for the 2-file check.)

2. MATH: For every *.csv file in verfied_ocr_data/, validates:
   - ballots_allocated == ballots_used + ballots_remaining
   - ballots_used      == valid_ballots + invalid_ballots + no_vote_ballots
   - sum(scores.*)     == valid_ballots

Outputs:
  - Pretty-printed, colourised terminal report
  - election_pipeline/output_data/verification_report.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "_expected_structure",
    Path(__file__).resolve().parent / "_expected_structure.py",
)
_mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)       # type: ignore[union-attr]
EXPECTED_UNITS: set[tuple[str, str, str]] = _mod.EXPECTED_UNITS

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]          # election_pipeline/
VERIFIED_DIR = ROOT / "verfied_ocr_data"
OUTPUT_DIR = ROOT / "output_data"
REPORT_CSV = OUTPUT_DIR / "verification_report.csv"

GDRIVE_URL = "https://drive.google.com/drive/folders/1c31r8sI94Azmv2pMX9k7fr1_9xzsBSjF"  # update as needed

# Folders whose *unit* directories are exempt from the 2-file structure check.
ADVANCE_PREFIXES = ("ล่วงหน้านอกเขต", "ล่วงหน้าในเขต")

# Expected CSV stems per regular unit folder
REQUIRED_FILES = {"summary_แบ่งเขต", "summary_บัญชีรายชื่อ"}

# ── ANSI colours ───────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
DIM    = "\033[2m"

def c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 – STRUCTURE CHECK
# ══════════════════════════════════════════════════════════════════════════════

def _is_advance_folder(path: Path) -> bool:
    """Return True if any component of *path* starts with an advance prefix."""
    for part in path.parts:
        if any(part.startswith(p) for p in ADVANCE_PREFIXES):
            return True
    return False


def build_raw_units() -> dict[tuple[str, str, str], Path]:
    """
    Returns the hard-coded expected unit structure (295 units).
    raw_pdf/ is NOT required to run this script.
    """
    # Paths are not real filesystem paths here — None signals “expected but not on disk”.
    return {key: Path() for key in EXPECTED_UNITS}


def build_verified_units() -> dict[tuple[str, str, str], Path]:
    """
    Walk verfied_ocr_data/ and collect all leaf (unit) directories.
    Returns {(amphoe, tambon, unit): absolute_path}.
    Handles advance folders (which are flat, no tambon/unit sub-levels)
    by representing them as (amphoe, '', '').
    """
    units: dict[tuple[str, str, str], Path] = {}
    for amphoe_dir in sorted(VERIFIED_DIR.iterdir()):
        if not amphoe_dir.is_dir():
            continue
        amphoe = amphoe_dir.name
        # Advance voting folders have no tambon/unit sub-directories
        if any(amphoe.startswith(p) for p in ADVANCE_PREFIXES):
            units[(amphoe, "", "")] = amphoe_dir
            continue
        for tambon_dir in sorted(amphoe_dir.iterdir()):
            if not tambon_dir.is_dir():
                continue
            tambon = tambon_dir.name
            for unit_dir in sorted(tambon_dir.iterdir()):
                if not unit_dir.is_dir():
                    continue
                unit = unit_dir.name
                units[(amphoe, tambon, unit)] = unit_dir
    return units


def check_structure(
    raw_units: dict[tuple[str, str, str], Path],
    verified_units: dict[tuple[str, str, str], Path],
) -> list[dict]:
    """
    Returns a list of structural issue dicts:
      {amphoe, tambon, unit, file_type, issue_type, issue_details}
    """
    issues: list[dict] = []

    # 1a. Folders present in raw_pdf but missing in verfied_ocr_data
    for key in raw_units:
        amphoe, tambon, unit = key
        if key not in verified_units:
            issues.append(
                dict(
                    amphoe=amphoe,
                    tambon=tambon,
                    unit=unit,
                    file_type="N/A",
                    issue_type="MISSING_FOLDER",
                    issue_details="Unit folder missing from verfied_ocr_data",
                )
            )

    # 1b. For each verified unit that is NOT an advance folder,
    #     check that exactly 2 required CSVs exist.
    for (amphoe, tambon, unit), unit_path in verified_units.items():
        if any(amphoe.startswith(p) for p in ADVANCE_PREFIXES):
            continue  # skip advance folders for this check

        # Collect actual CSV stems (without extension)
        csv_stems = {
            f.stem
            for f in unit_path.glob("*.csv")
        }

        missing = REQUIRED_FILES - csv_stems
        for stem in sorted(missing):
            issues.append(
                dict(
                    amphoe=amphoe,
                    tambon=tambon,
                    unit=unit,
                    file_type=stem,
                    issue_type="MISSING_CSV",
                    issue_details=f"{stem}.csv not found",
                )
            )

    return issues


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 – MATH CHECK
# ══════════════════════════════════════════════════════════════════════════════

def _safe_sum(series: pd.Series) -> float:
    """Sum a series, treating NaN as 0."""
    return float(series.fillna(0).sum())


def _val(row: pd.Series, col: str) -> float | None:
    v = row.get(col)
    if pd.isna(v):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def check_math_row(
    row: pd.Series,
    amphoe: str,
    tambon: str,
    unit: str,
    file_type: str,
) -> list[dict]:
    """
    Validate a single data row and return any issues found.
    """
    issues: list[dict] = []

    ballots_allocated = _val(row, "ballots_allocated")
    ballots_used      = _val(row, "ballots_used")
    ballots_remaining = _val(row, "ballots_remaining")
    valid_ballots     = _val(row, "valid_ballots")
    invalid_ballots   = _val(row, "invalid_ballots")
    no_vote_ballots   = _val(row, "no_vote_ballots")

    # Score columns
    score_cols = [c for c in row.index if str(c).startswith("scores.")]
    score_vals = [row[c] for c in score_cols]
    score_series = pd.Series([float(v) if not pd.isna(v) else float("nan") for v in score_vals])

    def issue(itype: str, detail: str) -> dict:
        return dict(
            amphoe=amphoe,
            tambon=tambon,
            unit=unit,
            file_type=file_type,
            issue_type=itype,
            issue_details=detail,
        )

    # Check 1: ballots_allocated == ballots_used + ballots_remaining
    if ballots_allocated is None or ballots_used is None or ballots_remaining is None:
        issues.append(
            issue(
                "MATH_MISSING_FIELD",
                f"Cannot check allocation: ballots_allocated={ballots_allocated}, "
                f"ballots_used={ballots_used}, ballots_remaining={ballots_remaining}",
            )
        )
    elif abs(ballots_allocated - (ballots_used + ballots_remaining)) > 0.5:
        issues.append(
            issue(
                "MATH_ALLOCATION",
                f"ballots_allocated ({ballots_allocated:.0f}) ≠ "
                f"ballots_used ({ballots_used:.0f}) + "
                f"ballots_remaining ({ballots_remaining:.0f}) = "
                f"{ballots_used + ballots_remaining:.0f}",
            )
        )

    # Check 2: ballots_used == valid + invalid + no_vote
    if ballots_used is None or valid_ballots is None or invalid_ballots is None or no_vote_ballots is None:
        issues.append(
            issue(
                "MATH_MISSING_FIELD",
                f"Cannot check ballots_used: valid={valid_ballots}, "
                f"invalid={invalid_ballots}, no_vote={no_vote_ballots}",
            )
        )
    elif abs(ballots_used - (valid_ballots + invalid_ballots + no_vote_ballots)) > 0.5:
        issues.append(
            issue(
                "MATH_USED",
                f"ballots_used ({ballots_used:.0f}) ≠ "
                f"valid ({valid_ballots:.0f}) + "
                f"invalid ({invalid_ballots:.0f}) + "
                f"no_vote ({no_vote_ballots:.0f}) = "
                f"{valid_ballots + invalid_ballots + no_vote_ballots:.0f}",
            )
        )

    # Check 3: sum(scores) == valid_ballots
    if score_cols:
        if valid_ballots is None:
            issues.append(
                issue("MATH_MISSING_FIELD", "valid_ballots is missing; cannot verify scores sum")
            )
        elif score_series.isna().all():
            issues.append(issue("MATH_MISSING_FIELD", "All score columns are NaN"))
        else:
            scores_total = _safe_sum(score_series)
            if abs(scores_total - valid_ballots) > 0.5:
                issues.append(
                    issue(
                        "MATH_SCORES",
                        f"sum(scores) ({scores_total:.0f}) ≠ valid_ballots ({valid_ballots:.0f})",
                    )
                )

    return issues


def check_math_all(verified_units: dict[tuple[str, str, str], Path]) -> list[dict]:
    """
    Iterate every *.csv in verfied_ocr_data/ and run math checks.
    """
    all_issues: list[dict] = []

    for (amphoe, tambon, unit), unit_path in sorted(verified_units.items()):
        # For advance folders, unit_path IS the folder containing the CSVs directly
        csv_files = sorted(unit_path.glob("*.csv"))
        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path, dtype=str)
            except Exception as e:
                all_issues.append(
                    dict(
                        amphoe=amphoe,
                        tambon=tambon,
                        unit=unit,
                        file_type=csv_path.stem,
                        issue_type="READ_ERROR",
                        issue_details=str(e),
                    )
                )
                continue

            # Convert numeric columns
            numeric_cols = [
                "ballots_allocated", "ballots_used", "ballots_remaining",
                "valid_ballots", "invalid_ballots", "no_vote_ballots",
            ] + [c for c in df.columns if str(c).startswith("scores.")]

            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            for _, row in df.iterrows():
                row_amphoe = str(row.get("metadata.amphoe", amphoe) or amphoe)
                row_tambon = str(row.get("metadata.tambon", tambon) or tambon)
                row_unit   = str(row.get("metadata.unit", unit)   or unit)
                row_issues = check_math_row(
                    row,
                    amphoe=row_amphoe,
                    tambon=row_tambon,
                    unit=row_unit,
                    file_type=csv_path.stem,
                )
                all_issues.extend(row_issues)

    return all_issues


# ══════════════════════════════════════════════════════════════════════════════
# REPORTING
# ══════════════════════════════════════════════════════════════════════════════

ISSUE_LABELS = {
    "MISSING_FOLDER": ("❌ MISSING FOLDER", RED),
    "MISSING_CSV":    ("📄 MISSING CSV",    YELLOW),
    "READ_ERROR":     ("⚠️  READ ERROR",     YELLOW),
    "MATH_ALLOCATION":  ("🔢 MATH (allocation)", RED),
    "MATH_USED":        ("🔢 MATH (used)",       RED),
    "MATH_SCORES":      ("🔢 MATH (scores)",     RED),
    "MATH_MISSING_FIELD": ("⚠️  MATH (missing field)", YELLOW),
}


def _location(amphoe: str, tambon: str, unit: str) -> str:
    parts = [p for p in (amphoe, tambon, unit) if p]
    return " / ".join(parts)


def print_report(structure_issues: list[dict], math_issues: list[dict]) -> None:
    total = len(structure_issues) + len(math_issues)

    print()
    print(c(BOLD + CYAN, "═" * 68))
    print(c(BOLD + CYAN, "  OCR Manual Check Verifier — Report"))
    print(c(BOLD + CYAN, "═" * 68))

    # ── Structure ──
    print()
    print(c(BOLD, "▶ STRUCTURE CHECKS"))
    print(c(DIM, "─" * 68))
    if not structure_issues:
        print(c(GREEN, "  ✅  No structural issues found."))
    else:
        for iss in structure_issues:
            label, color = ISSUE_LABELS.get(iss["issue_type"], (iss["issue_type"], YELLOW))
            loc = _location(iss["amphoe"], iss["tambon"], iss["unit"])
            print(f"  {c(color, label)}")
            print(f"      {c(BOLD, loc)}")
            print(f"      {c(DIM, iss['issue_details'])}")
            print()

    # ── Math ──
    print()
    print(c(BOLD, "▶ MATH CHECKS"))
    print(c(DIM, "─" * 68))
    if not math_issues:
        print(c(GREEN, "  ✅  No math issues found."))
    else:
        # Group by location for readability
        from itertools import groupby

        def key_fn(i: dict) -> tuple:
            return (i["amphoe"], i["tambon"], i["unit"])

        sorted_math = sorted(math_issues, key=key_fn)
        for (amphoe, tambon, unit), group in groupby(sorted_math, key=key_fn):
            loc = _location(amphoe, tambon, unit)
            print(f"  {c(BOLD, loc)}")
            for iss in group:
                label, color = ISSUE_LABELS.get(iss["issue_type"], (iss["issue_type"], YELLOW))
                print(f"    {c(color, label)}  [{iss['file_type']}]")
                print(f"    {c(DIM, iss['issue_details'])}")
            print()

    # ── Summary ──
    print(c(BOLD + CYAN, "═" * 68))
    status_color = GREEN if total == 0 else RED
    print(
        c(BOLD, "  SUMMARY: ") +
        c(status_color, f"{total} issue(s) found") +
        c(DIM, f"  ({len(structure_issues)} structural, {len(math_issues)} math)")
    )
    print(c(BOLD + CYAN, "═" * 68))
    print()


def save_report(structure_issues: list[dict], math_issues: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_issues = structure_issues + math_issues

    fieldnames = ["amphoe", "tambon", "unit", "file_type", "issue_type", "issue_details"]

    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_issues)

    total = len(all_issues)
    if total == 0:
        print(c(GREEN, f"  ✅  Report saved (0 issues): {REPORT_CSV}"))
    else:
        print(c(YELLOW, f"  📋  Report saved ({total} issues): {REPORT_CSV}"))


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print(c(DIM, "\nScanning directories…"))

    if not VERIFIED_DIR.exists():
        print(c(RED, "\u274c  ERROR: verfied_ocr_data/ folder not found."))
        print(c(YELLOW, "   Please download it from Google Drive and place it at:"))
        print(c(BOLD,   f"   {VERIFIED_DIR}"))
        print(c(DIM,    f"   URL: {GDRIVE_URL}"))
        sys.exit(1)

    # Step 1: Structure
    print(c(DIM, f"  → Using {len(EXPECTED_UNITS)} hard-coded expected units…"))
    raw_units = build_raw_units()

    print(c(DIM, "  → Building verfied_ocr_data unit list…"))
    verified_units = build_verified_units()
    print(c(DIM, f"     {len(verified_units)} unit(s) found in verfied_ocr_data/"))

    structure_issues = check_structure(raw_units, verified_units)

    # Step 2: Math
    print(c(DIM, "  → Checking math across all CSV files…"))
    math_issues = check_math_all(verified_units)

    # Report
    print_report(structure_issues, math_issues)
    save_report(structure_issues, math_issues)


if __name__ == "__main__":
    main()
