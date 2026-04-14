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

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from validation.linguistic_validator import clean_score_to_int

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

        2. **Master-list alignment** — any candidate or party in the master
           lists that is absent from *raw_data* is added with score
           ``numpy.nan``.  Candidates/parties present in *raw_data* but not in
           the master lists are kept (not silently dropped) so no data is
           lost.

        3. **Math consistency** — checks that::

               valid_ballots + invalid_ballots + no_vote_ballots == ballots_used

           If any operand is ``np.nan`` the check is skipped (flag set to
           ``True`` with detail ``"(Missing Data)"``).

        4. **Flag assembly** — produces a flags dict with:
           ``flag_math_total_used``, ``flag_math_valid_score``,
           ``flag_name_mismatch``, ``flag_missing_data``.

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

        # Step 2: master-list alignment
        candidate_names = [c.get("name", str(c)) for c in self._master_candidates]
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

        # Step 3: clean ballot summary fields
        ballot_fields = ("valid_ballots", "invalid_ballots", "no_vote_ballots", "ballots_used")
        for field in ballot_fields:
            if field in cleaned:
                cleaned[field] = clean_score_to_int(cleaned[field])
            else:
                cleaned[field] = np.nan

        # Step 4: assemble flags
        flags = self._compute_flags(cleaned, raw_data)
        return cleaned, flags

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_nan(self, value: Any) -> bool:
        """Return True if *value* is NaN or None."""
        if value is None:
            return True
        try:
            return bool(np.isnan(value))
        except (TypeError, ValueError):
            return False

    def _compute_flags(self, cleaned: Dict[str, Any], raw_data: RawData) -> Flags:
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

        # --- flag_name_mismatch: candidate in raw_data not in master list ----
        master_names = {c.get("name", str(c)) for c in self._master_candidates}
        raw_names = set(raw_data.get("scores", {}).keys())
        unrecognised = raw_names - master_names
        flags["flag_name_mismatch"] = bool(unrecognised)
        flags["flag_name_mismatch_detail"] = sorted(unrecognised) if unrecognised else []

        return flags
