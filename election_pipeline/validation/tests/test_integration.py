"""
Integration smoke tests confirming that election_pipeline/ wires correctly
with validation/.

Run with:
    PYTHONPATH=election_pipeline uv run pytest validation/tests/test_integration.py
"""

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Imports from both packages (wiring check)
# ---------------------------------------------------------------------------

from src.ocr_parser import ElectionOCRParser
from validation.engine import ElectionValidator
from validation.linguistic_validator import clean_score_to_int

# Note: src.processor imports cv2 (native package) so it is not imported
# directly here. Its integration is covered by the process_pages call-site
# changes and manual DAG execution.


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MASTER_CANDIDATES = [
    "นายอรรถพล โต๋วสัจจา",
    "นายชาดา ไทยเศรษฐ์",
    "นางสาวสุชาดา บัวพันธ์",
]

MASTER_PARTIES = [
    "เพื่อไทย",
    "ประชาธิปัตย์",
    "ภูมิใจไทย",
]

SAMPLE_RAW_DATA = {
    "valid_ballots": "100",
    "invalid_ballots": "5",
    "no_vote_ballots": "10",
    "ballots_used": "115",
    "scores": {
        "นายอรรถพล โต๋วสัจจา": "60",
        "นายชาดา ไทยเศรษฐ์": "40",
    },
}


# ---------------------------------------------------------------------------
# 1. ocr_parser.clean_score_to_int delegates to linguistic_validator
# ---------------------------------------------------------------------------

class TestOCRParserLinguisticDelegation:
    """Verify that ElectionOCRParser.clean_score_to_int delegates to
    validation.linguistic_validator.clean_score_to_int."""

    def setup_method(self):
        self.parser = ElectionOCRParser()

    def test_arabic_digits_parsed(self):
        assert self.parser.clean_score_to_int("177") == 177

    def test_thai_digits_parsed(self):
        assert self.parser.clean_score_to_int("๑๗๗") == 177

    def test_dash_returns_nan(self):
        result = self.parser.clean_score_to_int("-")
        assert isinstance(result, float) and np.isnan(result), (
            f"Expected np.nan for '-', got {result!r}"
        )

    def test_em_dash_returns_nan(self):
        result = self.parser.clean_score_to_int("\u2014")
        assert isinstance(result, float) and np.isnan(result)

    def test_empty_string_returns_nan(self):
        result = self.parser.clean_score_to_int("")
        assert isinstance(result, float) and np.isnan(result)

    def test_none_returns_nan(self):
        result = self.parser.clean_score_to_int(None)
        assert isinstance(result, float) and np.isnan(result)

    def test_mixed_arabic_thai_digits(self):
        # "1๒3" should normalise to "123"
        assert self.parser.clean_score_to_int("1๒3") == 123

    def test_score_with_commas_stripped(self):
        # commas are not digits; normalize_numerals strips them
        assert self.parser.clean_score_to_int("1,234") == 1234

    def test_delegation_matches_module_function(self):
        """parser.clean_score_to_int and module-level function must agree."""
        for val in ["0", "99", "๑", "-", "", None]:
            parser_result = self.parser.clean_score_to_int(val)
            module_result = clean_score_to_int(val)
            # Both should agree on NaN-ness and integer value
            if isinstance(module_result, float) and np.isnan(module_result):
                assert isinstance(parser_result, float) and np.isnan(parser_result), (
                    f"Mismatch for {val!r}: parser={parser_result}, module=nan"
                )
            else:
                assert parser_result == module_result, (
                    f"Mismatch for {val!r}: parser={parser_result}, module={module_result}"
                )


# ---------------------------------------------------------------------------
# 2. ElectionValidator end-to-end wiring
# ---------------------------------------------------------------------------

class TestElectionValidatorWiring:
    """Verify ElectionValidator is correctly wired: string master lists work,
    NaN propagation is correct, and flags are populated."""

    def setup_method(self):
        self.validator = ElectionValidator(MASTER_CANDIDATES, MASTER_PARTIES)

    def test_validate_returns_tuple(self):
        cleaned, flags = self.validator.validate(SAMPLE_RAW_DATA)
        assert isinstance(cleaned, dict)
        assert isinstance(flags, dict)

    def test_scores_are_integers_not_strings(self):
        cleaned, _ = self.validator.validate(SAMPLE_RAW_DATA)
        for name, val in cleaned["scores"].items():
            if not (isinstance(val, float) and np.isnan(val)):
                assert isinstance(val, int), (
                    f"Expected int for {name}, got {type(val)}"
                )

    def test_missing_master_candidate_gets_nan(self):
        """นางสาวสุชาดา บัวพันธ์ is in MASTER_CANDIDATES but not in raw scores."""
        cleaned, _ = self.validator.validate(SAMPLE_RAW_DATA)
        missing_candidate = "นางสาวสุชาดา บัวพันธ์"
        assert missing_candidate in cleaned["scores"]
        assert np.isnan(cleaned["scores"][missing_candidate])

    def test_string_master_list_accepted(self):
        """String-only master_candidates must not raise AttributeError."""
        validator = ElectionValidator(
            master_candidates=["Candidate A", "Candidate B"],
            master_parties=["Party X"],
        )
        raw = {"scores": {"Candidate A": "50"}, "valid_ballots": "50",
               "invalid_ballots": "0", "no_vote_ballots": "0", "ballots_used": "50"}
        cleaned, flags = validator.validate(raw)
        assert cleaned["scores"]["Candidate A"] == 50

    def test_flag_missing_data_set_when_score_nan(self):
        cleaned, flags = self.validator.validate(SAMPLE_RAW_DATA)
        # At least one score is NaN (missing candidate), so flag_missing_data True
        assert flags["flag_missing_data"] is True

    def test_flag_math_total_used_correct(self):
        """115 == 100 + 5 + 10 -> no math error."""
        cleaned, flags = self.validator.validate(SAMPLE_RAW_DATA)
        assert flags["flag_math_total_used"] is False

    def test_flag_math_total_used_mismatch(self):
        bad_data = dict(SAMPLE_RAW_DATA)
        bad_data["ballots_used"] = "999"
        _, flags = self.validator.validate(bad_data)
        assert flags["flag_math_total_used"] is True

    def test_dash_score_produces_nan(self):
        raw = dict(SAMPLE_RAW_DATA)
        raw["scores"] = {"นายอรรถพล โต๋วสัจจา": "-", "นายชาดา ไทยเศรษฐ์": "40"}
        cleaned, flags = self.validator.validate(raw)
        assert np.isnan(cleaned["scores"]["นายอรรถพล โต๋วสัจจา"])
        assert flags["flag_missing_data"] is True


# ---------------------------------------------------------------------------
# 3. parse_markdown -> ElectionValidator pipeline
# ---------------------------------------------------------------------------

class TestParseMarkdownToValidator:
    """Integration test: parse OCR markdown then validate with ElectionValidator."""

    MOCK_MARKDOWN = """
    ผู้มีสิทธิเลือกตั้ง จำนวน 1,200
    มาแสดงตน จำนวน 800
    ได้รับจัดสรร จำนวน 810
    บัตรเลือกตั้งที่ใช้ จำนวน 800
    บัตรดี จำนวน 750
    บัตรเสีย จำนวน 30
    ไม่เลือก จำนวน 20
    บัตรเลือกตั้งที่เหลือ จำนวน 10

    | ที่ | ชื่อผู้สมัคร | คะแนน |
    |-----|-------------|--------|
    | 1   | นายอรรถพล โต๋วสัจจา | 450 |
    | 2   | นายชาดา ไทยเศรษฐ์ | 300 |
    """

    def setup_method(self):
        self.parser = ElectionOCRParser()
        self.validator = ElectionValidator(MASTER_CANDIDATES, MASTER_PARTIES)

    def test_parse_then_validate_no_exceptions(self):
        parsed = self.parser.parse_markdown(self.MOCK_MARKDOWN)
        cleaned, flags = self.validator.validate(parsed)
        assert isinstance(cleaned, dict)
        assert isinstance(flags, dict)

    def test_scores_extracted_and_cleaned(self):
        parsed = self.parser.parse_markdown(self.MOCK_MARKDOWN)
        cleaned, _ = self.validator.validate(parsed)
        assert cleaned["scores"].get("นายอรรถพล โต๋วสัจจา") == 450
        assert cleaned["scores"].get("นายชาดา ไทยเศรษฐ์") == 300

    def test_missing_candidate_added_with_nan(self):
        parsed = self.parser.parse_markdown(self.MOCK_MARKDOWN)
        cleaned, _ = self.validator.validate(parsed)
        # นางสาวสุชาดา บัวพันธ์ was not in markdown -> should be NaN
        assert "นางสาวสุชาดา บัวพันธ์" in cleaned["scores"]
        assert np.isnan(cleaned["scores"]["นางสาวสุชาดา บัวพันธ์"])
