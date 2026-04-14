# Phase 01: Linguistic Validation (Thai Word Cross-Check) - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the `ElectionOCRParser` to extract and cross-verify numeric scores (Arabic or Thai digits) against their written Thai word equivalents. This phase introduces linguistic validation using `PyThaiNLP`.

</domain>

<decisions>
## Implementation Decisions

### 1. Extraction & Digits
- **D-01: Flexible Extraction**: Support scores in formats like `193 หนึ่งร้อยเก้าสิบสาม` and `193 (หนึ่งร้อยเก้าสิบสาม)`.
- **D-02: Multi-Numeral Support**: The numeric part can be either Arabic digits (`0-9`) or Thai digits (`๐-๙`). Both must be normalized to standard integers before cross-checking.

### 2. Matching & Error Handling
- **D-03: Strict Match Requirement**: A score is only considered valid if the numeric part matches the converted Thai word value.
- **D-04: Mismatch Outcome**: If a mismatch occurs (e.g., `177` and `หนึ่งร้อยหกสิบ`), the value MUST be set to `np.nan`, `flag_linguistic_mismatch` set to `True`, and `needs_manual_check` triggered.
- **D-05: Human Verification**: Any linguistic discrepancy triggers an immediate requirement for manual human audit.

### 3. Normalization Strategy
- **D-06: Word Cleanup**: Before passing to `PyThaiNLP.util.thaiword_to_num`, the word segment must be normalized:
    - Remove all punctuation, parentheses, and noise symbols.
    - Remove **all whitespace** (e.g., `ห นึ ่ ง` → `หนึ่ง`) to counteract OCR-induced spacing.
    - Fix common character artifacts (e.g., duplicate vowels or floating tone marks).

### 4. Logic Priority
- **D-07: Presence of Word**: If the OCR fails to find *any* Thai words where they are expected (i.e., the text lacks a word component entirely), this should be flagged as a warning, but the numeric value may be kept if it is unambiguous.

</decisions>

<canonical_refs>
## Canonical References

### Dependencies
- `pythainlp.util.thaiword_to_num` — Primary conversion engine.
- `np.nan` (NumPy) — Standard missing value representation.

### Project Specs
- [REQUIREMENTS.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/REQUIREMENTS.md) — REQ-001 (Linguistic Cross-Check).

</canonical_refs>

<deferred>
## Deferred Ideas
- None.
</deferred>

---
*Created: 2026-04-14*
