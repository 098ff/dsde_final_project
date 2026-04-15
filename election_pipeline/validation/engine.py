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
    cleaned_data, flags = validator.validate(raw_data)
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import numpy as np
import re

from thefuzz import fuzz

from validation.linguistic_validator import clean_score_to_int, validate_score

# Matches Thai consonants/vowels/tone marks (excludes Thai digits ๐-๙)
_THAI_WORD_RE = re.compile(r"[\u0E01-\u0E3A\u0E40-\u0E4E]")

# Minimum fuzzy-match ratio (0–100) for an OCR name to be mapped to a master
# candidate.  Scores below this threshold are kept as-is and raise
# flag_name_mismatch.
_FUZZY_THRESHOLD = 80

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

RawData = Dict[str, Any]
Flags = Dict[str, Any]


class ElectionValidator:
    """Validates raw election OCR records against master reference lists.

    The validator follows a "Jigsaw" design: it exposes a single stable
    :meth:`validate` interface so the surrounding ``election_pipeline`` can
    call it without knowing its internals.  Internal validation logic can
    evolve (NaN handling, new flag types, linguistic cross-checks) without
    changing the call site.

    Args:
        master_candidates: List of dicts each containing at least ``"name"``
            and optionally ``"party"`` keys, representing the authoritative
            candidate roster for the constituency.
        master_parties:    List of strings (or dicts with ``"name"`` key)
            representing the authoritative party list for the election.
    """

    def __init__(
        self,
        master_candidates: List[Dict[str, Any]],
        master_parties: List[Any],
    ) -> None:
        self._master_candidates: List[Dict[str, Any]] = master_candidates
        self._master_parties: List[str] = [
            p if isinstance(p, str) else p.get("name", str(p))
            for p in master_parties
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, raw_data: RawData) -> Tuple[Dict[str, Any], Flags]:
        """Validate *raw_data* and return cleaned data together with flags.

        The validation pipeline:

        1. **Score cleaning** — run every score-like value through
           :func:`~validation.linguistic_validator.clean_score_to_int` so
           that all sentinels (``None``, ``""``, ``"-"``, ``"—"``, ``"."``)
           become ``numpy.nan``.

        2. **Fuzzy name alignment** — OCR-extracted candidate names are
           fuzzy-matched against the master list (threshold: 80).  Names that
           match are remapped to the canonical master name so downstream math
           checks and exports use consistent identifiers.  Names below the
           threshold are kept as-is and will raise ``flag_name_mismatch``.

        3. **Master-list gap-filling** — any master candidate not present
           after alignment is inserted with score ``numpy.nan``.

        4. **Math consistency** — checks that::

               valid_ballots + invalid_ballots + no_vote_ballots == ballots_used

           If any operand is ``np.nan`` the check is skipped (flag set to
           ``True`` with detail ``"(Missing Data)"``).

        5. **Flag assembly** — produces a flags dict with:
           ``flag_math_total_used``, ``flag_math_valid_score``,
           ``flag_name_mismatch``, ``flag_missing_data``,
           ``flag_linguistic_mismatch``.

        Args:
            raw_data: Dict representing one polling station's OCR output.
                Expected keys (all optional — missing ones are treated as NaN):
                ``scores`` (dict of candidate_name -> raw_score_string),
                ``valid_ballots``, ``invalid_ballots``, ``no_vote_ballots``,
                ``ballots_used``.

        Returns:
            A 2-tuple ``(cleaned_data, flags)`` where:

            - *cleaned_data* is a copy of *raw_data* with all score values
              replaced by integers or ``np.nan``, and any master-list gaps
              filled.
            - *flags* is a dict with boolean flags and human-readable detail
              strings.
        """
        cleaned = dict(raw_data)

        # Step 1: clean raw scores
        raw_scores: Dict[str, Any] = dict(cleaned.get("scores", {}))
        cleaned_scores: Dict[str, Any] = {
            name: clean_score_to_int(val) for name, val in raw_scores.items()
        }

        # Step 2: fuzzy-align OCR names → master candidate names
        candidate_names = [
            c if isinstance(c, str) else c.get("name", str(c))
            for c in self._master_candidates
        ]
        cleaned_scores, unrecognised_candidates = self._align_to_master(
            cleaned_scores, candidate_names
        )

        # Step 3: fill any master candidates still absent after alignment
        for name in candidate_names:
            if name not in cleaned_scores:
                cleaned_scores[name] = np.nan

        party_scores: Dict[str, Any] = dict(cleaned.get("party_scores", {}))
        for party in self._master_parties:
            if party not in party_scores:
                party_scores[party] = np.nan
            else:
                party_scores[party] = clean_score_to_int(party_scores[party])
        cleaned["party_scores"] = party_scores

        cleaned["scores"] = cleaned_scores

        # Step 4: clean ballot summary fields
        ballot_fields = ("valid_ballots", "invalid_ballots", "no_vote_ballots", "ballots_used")
        for field in ballot_fields:
            if field in cleaned:
                cleaned[field] = clean_score_to_int(cleaned[field])
            else:
                cleaned[field] = np.nan

        # Step 5: assemble flags
        flags = self._compute_flags(cleaned, raw_data, unrecognised_candidates)
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
        """Fuzzy-map OCR-extracted candidate names to master list names.

        For each extracted name the best-matching master name is found using
        ``fuzz.ratio``.  If the ratio is at or above *threshold* the key is
        remapped; otherwise the original name is kept and added to the
        returned *unrecognised* set.

        Args:
            scores:       Dict of {ocr_name: cleaned_score}.
            master_names: Authoritative candidate name list.
            threshold:    Minimum ratio (0–100) to accept a match.

        Returns:
            ``(aligned_scores, unrecognised_names)``
        """
        aligned: Dict[str, Any] = {}
        unrecognised: Set[str] = set()

        for raw_name, score in scores.items():
            if not raw_name:  # empty string from OCR noise
                unrecognised.add(raw_name)
                continue

            best_master, best_ratio = None, 0
            for master_name in master_names:
                ratio = fuzz.ratio(raw_name, master_name)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_master = master_name

            if best_ratio >= threshold:
                # Multiple OCR rows may map to the same master name — sum them
                if best_master in aligned:
                    existing = aligned[best_master]
                    if not self._is_nan(existing) and not self._is_nan(score):
                        aligned[best_master] = int(existing) + int(score)
                    # if one is NaN keep the non-NaN value (or NaN if both are)
                    elif self._is_nan(existing):
                        aligned[best_master] = score
                else:
                    aligned[best_master] = score
            else:
                aligned[raw_name] = score
                unrecognised.add(raw_name)

        return aligned, unrecognised

    def _is_nan(self, value: Any) -> bool:
        """Return True if *value* is NaN or None."""
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
        unrecognised_candidates: Set[str],
    ) -> Flags:
        """Compute validation flags from cleaned data."""
        flags: Flags = {}

        # --- flag_missing_data: any score in cleaned['scores'] is NaN -------
        any_score_nan = any(
            self._is_nan(v) for v in cleaned.get("scores", {}).values()
        ) or any(
            self._is_nan(v) for v in cleaned.get("party_scores", {}).values()
        )
        ballot_fields = ("valid_ballots", "invalid_ballots", "no_vote_ballots", "ballots_used")
        any_ballot_nan = any(self._is_nan(cleaned.get(f)) for f in ballot_fields)
        flags["flag_missing_data"] = any_score_nan or any_ballot_nan

        # --- flag_math_total_used: valid+invalid+no_vote == ballots_used -----
        v = cleaned.get("valid_ballots")
        inv = cleaned.get("invalid_ballots")
        no_v = cleaned.get("no_vote_ballots")
        used = cleaned.get("ballots_used")

        if any(self._is_nan(x) for x in (v, inv, no_v, used)):
            flags["flag_math_total_used"] = True
            flags["flag_math_total_used_detail"] = "(Missing Data)"
        else:
            expected = int(v) + int(inv) + int(no_v)
            actual = int(used)
            mismatch = expected != actual
            flags["flag_math_total_used"] = mismatch
            flags["flag_math_total_used_detail"] = (
                f"{expected} != {actual}" if mismatch else "OK"
            )

        # --- flag_math_valid_score: sum of candidate scores == valid_ballots -
        valid_ballots = cleaned.get("valid_ballots")
        score_values = [
            val for val in cleaned.get("scores", {}).values()
            if not self._is_nan(val)
        ]
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

        # --- flag_name_mismatch: OCR names with no master match above threshold
        flags["flag_name_mismatch"] = bool(unrecognised_candidates)
        flags["flag_name_mismatch_detail"] = (
            sorted(unrecognised_candidates) if unrecognised_candidates else []
        )

        # --- flag_linguistic_mismatch: numeric digit vs Thai word cross-check -
        mismatched_scores: list[str] = []
        for name, raw_val in raw_data.get("scores", {}).items():
            raw_str = str(raw_val) if raw_val is not None else ""
            if _THAI_WORD_RE.search(raw_str):
                numeric_part = re.sub(r"[^\d๐-๙]", "", raw_str) or None
                word_part = raw_str
                result = validate_score(numeric_part, word_part)
                if result["flag_linguistic_mismatch"]:
                    mismatched_scores.append(name)

        flags["flag_linguistic_mismatch"] = bool(mismatched_scores)
        flags["flag_linguistic_mismatch_detail"] = mismatched_scores if mismatched_scores else []

        return flags
