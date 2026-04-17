"""
Jigsaw Validation Engine for Thai Election OCR Results.

Provides the ``ElectionValidator`` class — a self-contained validation
component that aligns raw pipeline output against master candidate/party lists,
propagates ``numpy.nan`` for missing data, and produces structured flag outputs
that can be consumed by the ``election_pipeline`` without coupling the two
codebases together.

Usage::

    from validation.engine import ElectionValidator

    validator = ElectionValidator(master_candidates, master_parties)
    cleaned_data, flags = validator.validate(raw_data, form_type="แบ่งเขต")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import re

from thefuzz import fuzz

from validation.linguistic_validator import clean_score_to_int, validate_score

# Matches Thai consonants/vowels/tone marks (excludes Thai digits ๐-๙)
_THAI_WORD_RE = re.compile(r"[\u0E01-\u0E3A\u0E40-\u0E4E]")

# Minimum fuzzy-match ratio (0–100) for an OCR name to be mapped to a master
# name.  Scores below this threshold are kept as-is and raise flag_name_mismatch.
_FUZZY_THRESHOLD = 80

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

RawData = Dict[str, Any]
Flags = Dict[str, Any]


class ElectionValidator:
    """Validates raw election OCR records against master reference lists.

    Args:
        master_candidates: List of dicts each containing at least ``"name"``
            and optionally ``"party"`` keys, representing the authoritative
            candidate roster for the constituency (used for แบ่งเขต forms).
        master_parties:    List of strings (or dicts with ``"name"`` key)
            representing the authoritative party list (used for บัญชีรายชื่อ forms).
    """

    def __init__(
        self,
        master_candidates: List[Dict[str, Any]],
        master_parties: List[Any],
    ) -> None:
        self._master_candidates: List[str] = [
            c if isinstance(c, str) else c.get("name", str(c))
            for c in master_candidates
        ]
        self._master_parties: List[str] = [
            p if isinstance(p, str) else p.get("name", str(p))
            for p in master_parties
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        raw_data: RawData,
        form_type: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Flags]:
        """Validate *raw_data* and return cleaned data together with flags.

        The validation pipeline:

        1. **Score cleaning** — sentinel values (``None``, ``""``, ``"-"``,
           ``"—"``, ``"."``) become ``numpy.nan``.

        2. **Master list selection** — choose the correct reference list based
           on *form_type*:
           - ``"บัญชีรายชื่อ"`` → fuzzy-match against ``master_parties``
           - ``"แบ่งเขต"`` (or ``None``) → fuzzy-match against ``master_candidates``

        3. **Fuzzy name alignment** — OCR-extracted names are matched against
           the selected master list using ``fuzz.ratio`` (threshold: 80).
           Matched names are remapped to their canonical master name.
           Unmatched names raise ``flag_name_mismatch``.

        4. **Gap-filling** — master names absent after alignment are inserted
           with ``numpy.nan``.

        5. **Math consistency checks** and **flag assembly**.

        Args:
            raw_data:  Dict representing one polling station's OCR output.
            form_type: ``"บัญชีรายชื่อ"`` or ``"แบ่งเขต"``.  Determines which
                       master list is used for fuzzy alignment.

        Returns:
            ``(cleaned_data, flags)``
        """
        cleaned = dict(raw_data)

        # Step 1: clean raw scores
        raw_scores: Dict[str, Any] = dict(cleaned.get("scores", {}))
        cleaned_scores: Dict[str, Any] = {
            name: clean_score_to_int(val) for name, val in raw_scores.items()
        }

        # Step 2: select the correct master list for this form type
        if form_type == "บัญชีรายชื่อ":
            master_names = self._master_parties
        else:
            master_names = self._master_candidates

        # Step 3: fuzzy-align OCR names → master names
        cleaned_scores, unrecognised = self._align_to_master(cleaned_scores, master_names)

        # Step 4: fill any master names still absent after alignment with NaN
        for name in master_names:
            if name not in cleaned_scores:
                cleaned_scores[name] = np.nan

        # scores is the single source of truth for both form types
        cleaned["scores"] = cleaned_scores
        cleaned.pop("party_scores", None)

        # Step 5: clean ballot summary fields
        ballot_fields = ("valid_ballots", "invalid_ballots", "no_vote_ballots", "ballots_used")
        for field in ballot_fields:
            cleaned[field] = clean_score_to_int(cleaned[field]) if field in cleaned else np.nan

        # Step 6: assemble flags
        flags = self._compute_flags(cleaned, raw_data, unrecognised)
        return cleaned, flags

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _align_to_master(
        self,
        scores: Dict[str, Any],
        master_names: List[str],
        threshold: int = _FUZZY_THRESHOLD,
    ) -> Tuple[Dict[str, Any], Set[str]]:
        """Fuzzy-map OCR-extracted names to master list names.

        For each extracted name the best-matching master name is found using
        ``fuzz.ratio``.  If the ratio is at or above *threshold* the key is
        remapped to the canonical master name; otherwise the original name is
        kept and added to the returned *unrecognised* set.

        When multiple OCR rows map to the same master name their scores are
        summed (non-NaN + non-NaN), or the non-NaN value is kept when one
        side is NaN.

        Returns:
            ``(aligned_scores, unrecognised_names)``
        """
        aligned: Dict[str, Any] = {}
        unrecognised: Set[str] = set()

        for raw_name, score in scores.items():
            if not raw_name:  # empty string — OCR noise
                unrecognised.add(raw_name)
                continue

            best_master, best_ratio = None, 0
            for master_name in master_names:
                ratio = fuzz.ratio(raw_name, master_name)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_master = master_name

            if best_ratio >= threshold:
                if best_master in aligned:
                    existing = aligned[best_master]
                    if not self._is_nan(existing) and not self._is_nan(score):
                        aligned[best_master] = int(existing) + int(score)
                    elif self._is_nan(existing):
                        aligned[best_master] = score
                    # else: keep existing (score is NaN)
                else:
                    aligned[best_master] = score
            else:
                aligned[raw_name] = score
                unrecognised.add(raw_name)

        return aligned, unrecognised

    def _is_nan(self, value: Any) -> bool:
        if value is None:
            return True
        try:
            return bool(np.isnan(value))
        except (TypeError, ValueError):
            return False

    def _compute_flags(
        self,
        cleaned: Dict[str, Any],
        raw_data: RawData,
        unrecognised: Set[str],
    ) -> Flags:
        flags: Flags = {}

        # --- flag_missing_data -------------------------------------------
        any_score_nan = any(self._is_nan(v) for v in cleaned.get("scores", {}).values())
        ballot_fields = ("valid_ballots", "invalid_ballots", "no_vote_ballots", "ballots_used")
        any_ballot_nan = any(self._is_nan(cleaned.get(f)) for f in ballot_fields)
        flags["flag_missing_data"] = any_score_nan or any_ballot_nan

        # --- flag_math_total_used ----------------------------------------
        v, inv, no_v, used = (cleaned.get(f) for f in ballot_fields)
        if any(self._is_nan(x) for x in (v, inv, no_v, used)):
            flags["flag_math_total_used"] = True
            flags["flag_math_total_used_detail"] = "(Missing Data)"
        else:
            expected = int(v) + int(inv) + int(no_v)
            actual = int(used)
            mismatch = expected != actual
            flags["flag_math_total_used"] = mismatch
            flags["flag_math_total_used_detail"] = f"{expected} != {actual}" if mismatch else "OK"

        # --- flag_math_valid_score ---------------------------------------
        valid_ballots = cleaned.get("valid_ballots")
        score_values = [v for v in cleaned.get("scores", {}).values() if not self._is_nan(v)]
        if self._is_nan(valid_ballots) or not score_values:
            flags["flag_math_valid_score"] = True
            flags["flag_math_valid_score_detail"] = "(Missing Data)"
        else:
            score_sum = sum(int(s) for s in score_values)
            expected_valid = int(valid_ballots)
            mismatch = score_sum != expected_valid
            flags["flag_math_valid_score"] = mismatch
            flags["flag_math_valid_score_detail"] = (
                f"{score_sum} != {expected_valid}" if mismatch else "OK"
            )

        # --- flag_name_mismatch ------------------------------------------
        flags["flag_name_mismatch"] = bool(unrecognised)
        flags["flag_name_mismatch_detail"] = sorted(unrecognised) if unrecognised else []

        # --- flag_linguistic_mismatch ------------------------------------
        mismatched: List[str] = []
        for name, raw_val in raw_data.get("scores", {}).items():
            raw_str = str(raw_val) if raw_val is not None else ""
            if _THAI_WORD_RE.search(raw_str):
                numeric_part = re.sub(r"[^\d๐-๙]", "", raw_str) or None
                result = validate_score(numeric_part, raw_str)
                if result["flag_linguistic_mismatch"]:
                    mismatched.append(name)

        flags["flag_linguistic_mismatch"] = bool(mismatched)
        flags["flag_linguistic_mismatch_detail"] = mismatched if mismatched else []

        return flags
