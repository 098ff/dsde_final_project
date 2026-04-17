"""
Unit and integration tests for the Jigsaw Validation Engine.

Tests cover:
- NaN propagation through clean_score_to_int
- Math consistency flags (total used, valid score sum)
- Master-list alignment (absent candidates filled with NaN)
- Name mismatch flagging
- Missing-data flag
- Formatters: CSV na_rep and JSON NaN->None
- Integration: mock "Jigsaw" connection simulating election_pipeline call
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from validation.linguistic_validator import clean_score_to_int
from validation.engine import ElectionValidator
from validation.formatters import prepare_df_for_csv, prepare_data_for_json


# ===========================================================================
# clean_score_to_int: NaN propagation
# ===========================================================================


class TestCleanScoreToInt:
    """Tests for the refactored clean_score_to_int function."""

    def test_none_returns_nan(self):
        result = clean_score_to_int(None)
        assert math.isnan(result), "None should return np.nan"

    def test_empty_string_returns_nan(self):
        result = clean_score_to_int("")
        assert math.isnan(result), "Empty string should return np.nan"

    def test_dash_returns_nan(self):
        result = clean_score_to_int("-")
        assert math.isnan(result), "'-' should return np.nan"

    def test_em_dash_returns_nan(self):
        result = clean_score_to_int("\u2014")
        assert math.isnan(result), "'—' should return np.nan"

    def test_dot_returns_nan(self):
        result = clean_score_to_int(".")
        assert math.isnan(result), "'.' should return np.nan"

    def test_whitespace_only_returns_nan(self):
        result = clean_score_to_int("   ")
        assert math.isnan(result), "Whitespace-only string should return np.nan"

    def test_arabic_digits(self):
        assert clean_score_to_int("177") == 177

    def test_thai_digits(self):
        assert clean_score_to_int("๑๗๗") == 177

    def test_mixed_digits(self):
        assert clean_score_to_int("1๗๗") == 177

    def test_digits_with_punctuation(self):
        assert clean_score_to_int("1,234") == 1234

    def test_zero(self):
        assert clean_score_to_int("0") == 0

    def test_thai_zero(self):
        assert clean_score_to_int("๐") == 0

    def test_non_numeric_string_returns_nan(self):
        result = clean_score_to_int("abc")
        assert math.isnan(result), "Non-numeric string should return np.nan"


# ===========================================================================
# ElectionValidator: NaN propagation and math flags
# ===========================================================================


MASTER_CANDIDATES = [
    {"name": "Alice"},
    {"name": "Bob"},
    {"name": "Charlie"},
]
MASTER_PARTIES = ["Party A", "Party B"]


def make_validator() -> ElectionValidator:
    return ElectionValidator(MASTER_CANDIDATES, MASTER_PARTIES)


class TestElectionValidatorNaNPropagation:
    """NaN propagation in scores and ballot fields."""

    def test_missing_candidate_filled_with_nan(self):
        raw = {
            "scores": {"Alice": "100", "Bob": "50"},  # Charlie missing
            "valid_ballots": "150",
            "invalid_ballots": "5",
            "no_vote_ballots": "5",
            "ballots_used": "160",
        }
        cleaned, flags = make_validator().validate(raw)
        assert math.isnan(cleaned["scores"]["Charlie"]), \
            "Master-list candidate absent from raw data should be np.nan"

    def test_nan_sentinel_in_score(self):
        raw = {
            "scores": {"Alice": "-", "Bob": "50", "Charlie": "30"},
            "valid_ballots": "80",
            "invalid_ballots": "0",
            "no_vote_ballots": "0",
            "ballots_used": "80",
        }
        cleaned, _ = make_validator().validate(raw)
        assert math.isnan(cleaned["scores"]["Alice"]), \
            "Dash score sentinel should become np.nan"

    def test_missing_ballot_field_filled_with_nan(self):
        raw = {
            "scores": {"Alice": "100", "Bob": "50", "Charlie": "0"},
        }
        cleaned, flags = make_validator().validate(raw)
        assert math.isnan(cleaned["ballots_used"]), \
            "Absent ballot field should become np.nan"

    def test_missing_party_in_master_filled_with_nan(self):
        raw = {
            "scores": {"Alice": "10", "Bob": "5", "Charlie": "5"},
            "party_scores": {"Party A": "20"},  # Party B absent
            "valid_ballots": "20",
            "invalid_ballots": "0",
            "no_vote_ballots": "0",
            "ballots_used": "20",
        }
        cleaned, _ = make_validator().validate(raw)
        assert math.isnan(cleaned["party_scores"]["Party B"]), \
            "Master-list party absent from party_scores should be np.nan"


class TestElectionValidatorMathFlags:
    """Math consistency flag generation."""

    def test_math_total_used_ok(self):
        raw = {
            "scores": {"Alice": "100", "Bob": "50", "Charlie": "0"},
            "valid_ballots": "150",
            "invalid_ballots": "5",
            "no_vote_ballots": "5",
            "ballots_used": "160",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_math_total_used"] is False
        assert flags["flag_math_total_used_detail"] == "OK"

    def test_math_total_used_mismatch(self):
        raw = {
            "scores": {"Alice": "100", "Bob": "50", "Charlie": "0"},
            "valid_ballots": "150",
            "invalid_ballots": "5",
            "no_vote_ballots": "5",
            "ballots_used": "999",  # intentionally wrong
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_math_total_used"] is True
        assert "160" in flags["flag_math_total_used_detail"]
        assert "999" in flags["flag_math_total_used_detail"]

    def test_math_total_used_nan_triggers_missing_data(self):
        raw = {
            "scores": {"Alice": "100", "Bob": "50", "Charlie": "0"},
            "valid_ballots": "150",
            "invalid_ballots": "-",   # NaN sentinel
            "no_vote_ballots": "5",
            "ballots_used": "160",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_math_total_used"] is True
        assert flags["flag_math_total_used_detail"] == "(Missing Data)"

    def test_math_valid_score_ok(self):
        raw = {
            "scores": {"Alice": "100", "Bob": "50", "Charlie": "0"},
            "valid_ballots": "150",
            "invalid_ballots": "5",
            "no_vote_ballots": "5",
            "ballots_used": "160",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_math_valid_score"] is False
        assert flags["flag_math_valid_score_detail"] == "OK"

    def test_math_valid_score_mismatch(self):
        raw = {
            "scores": {"Alice": "100", "Bob": "60", "Charlie": "0"},  # sum=160
            "valid_ballots": "150",   # != 160
            "invalid_ballots": "5",
            "no_vote_ballots": "5",
            "ballots_used": "160",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_math_valid_score"] is True

    def test_math_valid_score_nan_skips(self):
        """When valid_ballots is NaN the flag should be True / Missing Data."""
        raw = {
            "scores": {"Alice": "100", "Bob": "50", "Charlie": "0"},
            "valid_ballots": "-",     # NaN
            "invalid_ballots": "5",
            "no_vote_ballots": "5",
            "ballots_used": "160",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_math_valid_score"] is True
        assert flags["flag_math_valid_score_detail"] == "(Missing Data)"


class TestElectionValidatorNameMismatch:
    """flag_name_mismatch detects unrecognised candidates."""

    def test_no_mismatch_when_all_in_master(self):
        raw = {
            "scores": {"Alice": "10", "Bob": "5", "Charlie": "5"},
            "valid_ballots": "20",
            "invalid_ballots": "0",
            "no_vote_ballots": "0",
            "ballots_used": "20",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_name_mismatch"] is False
        assert flags["flag_name_mismatch_detail"] == []

    def test_mismatch_when_unknown_candidate(self):
        raw = {
            "scores": {"Alice": "10", "Bob": "5", "Dave": "5"},  # Dave unknown
            "valid_ballots": "20",
            "invalid_ballots": "0",
            "no_vote_ballots": "0",
            "ballots_used": "20",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_name_mismatch"] is True
        assert "Dave" in flags["flag_name_mismatch_detail"]


class TestElectionValidatorMissingDataFlag:
    """flag_missing_data is True when any score or ballot field is NaN."""

    def test_no_missing_when_all_present(self):
        raw = {
            "scores": {"Alice": "10", "Bob": "5", "Charlie": "5"},
            "party_scores": {"Party A": "8", "Party B": "2"},
            "valid_ballots": "20",
            "invalid_ballots": "0",
            "no_vote_ballots": "0",
            "ballots_used": "20",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_missing_data"] is False

    def test_missing_when_score_is_nan(self):
        raw = {
            "scores": {"Alice": "-", "Bob": "5", "Charlie": "5"},
            "valid_ballots": "10",
            "invalid_ballots": "0",
            "no_vote_ballots": "0",
            "ballots_used": "10",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_missing_data"] is True

    def test_missing_when_candidate_absent_from_raw(self):
        raw = {
            "scores": {"Alice": "10", "Bob": "5"},  # Charlie missing
            "valid_ballots": "15",
            "invalid_ballots": "0",
            "no_vote_ballots": "0",
            "ballots_used": "15",
        }
        _, flags = make_validator().validate(raw)
        assert flags["flag_missing_data"] is True


# ===========================================================================
# Formatters
# ===========================================================================


class TestPreparedfForCsv:
    """CSV export uses 'MISSING' for NaN values."""

    def test_nan_becomes_missing_string(self):
        df = pd.DataFrame({"score": [1, np.nan, 3], "name": ["A", "B", "C"]})
        csv_str = prepare_df_for_csv(df)
        lines = csv_str.strip().splitlines()
        assert lines[2] == "MISSING,B", f"Expected 'MISSING,B', got {lines[2]!r}"

    def test_none_becomes_missing_string(self):
        df = pd.DataFrame({"score": [1, None, 3]})
        csv_str = prepare_df_for_csv(df)
        assert "MISSING" in csv_str

    def test_no_index_by_default(self):
        df = pd.DataFrame({"a": [1, 2]})
        csv_str = prepare_df_for_csv(df)
        assert "0,1" not in csv_str, "Index should not be in output by default"

    def test_file_write(self, tmp_path):
        df = pd.DataFrame({"x": [np.nan]})
        path = str(tmp_path / "out.csv")
        result = prepare_df_for_csv(df, path=path)
        assert result is None
        with open(path) as f:
            contents = f.read()
        assert "MISSING" in contents


class TestPrepareDataForJson:
    """JSON conversion replaces NaN with None."""

    def test_nan_becomes_none(self):
        assert prepare_data_for_json(np.nan) is None

    def test_float_nan_becomes_none(self):
        assert prepare_data_for_json(float("nan")) is None

    def test_dict_nan_becomes_none(self):
        result = prepare_data_for_json({"score": np.nan, "name": "Alice"})
        assert result == {"score": None, "name": "Alice"}

    def test_list_nan_becomes_none(self):
        result = prepare_data_for_json([np.nan, 1, np.nan])
        assert result == [None, 1, None]

    def test_nested_structure(self):
        data = {"a": {"b": np.nan}, "c": [1, np.nan]}
        result = prepare_data_for_json(data)
        assert result == {"a": {"b": None}, "c": [1, None]}

    def test_numpy_int_unwrapped(self):
        result = prepare_data_for_json(np.int64(42))
        assert result == 42
        assert type(result) is int

    def test_numpy_float_unwrapped(self):
        result = prepare_data_for_json(np.float64(3.14))
        assert abs(result - 3.14) < 1e-9
        assert type(result) is float

    def test_non_nan_passthrough(self):
        assert prepare_data_for_json("hello") == "hello"
        assert prepare_data_for_json(0) == 0
        assert prepare_data_for_json(None) is None


# ===========================================================================
# Integration test: mock "Jigsaw" connection
# ===========================================================================


class TestJigsawIntegration:
    """Simulates election_pipeline calling ElectionValidator as a Jigsaw piece."""

    def _mock_pipeline_record(self) -> dict:
        """Simulate a raw record as produced by election_pipeline."""
        return {
            "station_id": "BKK-001-01",
            "scores": {
                "Alice": "๑๐๐",   # Thai digits
                "Bob": "50",
                # Charlie absent (OCR missed it)
            },
            "party_scores": {
                "Party A": "80",
                # Party B absent
            },
            "valid_ballots": "150",
            "invalid_ballots": "-",   # NaN sentinel — OCR failure
            "no_vote_ballots": "10",
            "ballots_used": ".",       # NaN sentinel — OCR failure
        }

    def test_jigsaw_validate_returns_tuple(self):
        validator = make_validator()
        raw = self._mock_pipeline_record()
        result = validator.validate(raw)
        assert isinstance(result, tuple) and len(result) == 2

    def test_jigsaw_cleaned_data_has_nan_for_missing(self):
        validator = make_validator()
        raw = self._mock_pipeline_record()
        cleaned, _ = validator.validate(raw)
        assert math.isnan(cleaned["scores"]["Charlie"]), "Charlie should be NaN"
        assert math.isnan(cleaned["party_scores"]["Party B"]), "Party B should be NaN"
        assert math.isnan(cleaned["invalid_ballots"]), "invalid_ballots '-' -> NaN"
        assert math.isnan(cleaned["ballots_used"]), "ballots_used '.' -> NaN"

    def test_jigsaw_thai_digits_converted(self):
        validator = make_validator()
        raw = self._mock_pipeline_record()
        cleaned, _ = validator.validate(raw)
        assert cleaned["scores"]["Alice"] == 100, "Thai digits ๑๐๐ should become 100"

    def test_jigsaw_missing_data_flag_set(self):
        validator = make_validator()
        raw = self._mock_pipeline_record()
        _, flags = validator.validate(raw)
        assert flags["flag_missing_data"] is True

    def test_jigsaw_math_total_missing_data(self):
        validator = make_validator()
        raw = self._mock_pipeline_record()
        _, flags = validator.validate(raw)
        assert flags["flag_math_total_used"] is True
        assert flags["flag_math_total_used_detail"] == "(Missing Data)"

    def test_jigsaw_cleaned_data_is_json_safe(self):
        import json
        validator = make_validator()
        raw = self._mock_pipeline_record()
        cleaned, flags = validator.validate(raw)
        from validation.formatters import prepare_data_for_json
        combined = {"cleaned": cleaned, "flags": flags}
        json_safe = prepare_data_for_json(combined)
        # Should not raise
        json_str = json.dumps(json_safe)
        assert "null" in json_str, "NaN values should appear as null in JSON"
