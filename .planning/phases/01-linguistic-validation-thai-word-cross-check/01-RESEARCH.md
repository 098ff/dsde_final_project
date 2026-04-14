# Phase 01: Linguistic Validation - Research

## Standard Stack
- **PyThaiNLP (5.3.1)**: Uses `pythainlp.util.thaiword_to_num` for conversion.
- **NumPy**: For `np.nan` representation of mismatches.
- **Regex (re)**: For flexible capture of Arabic/Thai digits and accompanying words.

## Architecture Patterns

### 1. Dual Extraction Pipelining
The `ElectionOCRParser` should be updated to separate "Numeric Capture" from "Linguistic Capture".
- **Numeric Capture**: Standardize digits (Arabic or Thai) into integers.
- **Linguistic Capture**: Identify substrings containing Thai characters, normalize, and convert using `PyThaiNLP`.

### 2. Normalization Flow
Before linguistic conversion, the text segment undergoes:
1. `strip()` external whitespace.
2. `re.sub(r'[^\u0E01-\u0E3A\u0E40-\u0E4E]', '', text)`: Keep only Thai characters (excluding digits and punctuation).
3. `re.sub(r'\s+', '', text)`: Remove internal spaces.
4. Character normalization (e.g., `PyThaiNLP` provides `normalize()` for common vowel/tone issues).

## Common Pitfalls
- **OCR Garbage**: Symbols like `(` or `)` or `.` might be misinterpreted. The "only Thai characters" regex is critical.
- **Thai Digits vs. Words**: Some OCR might produce `๑๐๐` (Thai digits) instead of `หนึ่งร้อย` (words). Both need handling but linguistic conversion specifically targets words.
- **False Positives in Regex**: If a row has "Candidate Name" containing numbers, the score regex must be specific to the score column.

## Code Examples

### Standardizing Digits
```python
def normalize_digits(s):
    thai_digits = "๐๑๒๓๔๕๖๗๘๙"
    for i, d in enumerate(thai_digits):
        s = s.replace(d, str(i))
    return re.sub(r'[^\d]', '', s)
```

### Converting Thai Words
```python
from pythainlp.util import thaiword_to_num

def word_to_val(s):
    clean = re.sub(r'[^\u0E01-\u0E3A\u0E40-\u0E4E]', '', s)
    return thaiword_to_num(clean)
```

## Validation Architecture
- **Dimension 8 (Validation)**: Every score extraction MUST return a "Validation Record" containing:
    - `numeric_val`: The value from digits.
    - `linguistic_val`: The value from Thai words (if any).
    - `is_match`: Boolean.
- This record feeds into `validate_data` to set the `flag_linguistic_mismatch`.

---
*Created: 2026-04-14*
