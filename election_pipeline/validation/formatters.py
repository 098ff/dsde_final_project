"""
Formatting Utilities for Thai Election Validation Output.

Provides helpers that ensure validated data is serialised consistently
across export formats:

- **CSV**:  ``NaN`` values are written as the string ``"MISSING"`` so that
  downstream consumers and auditors can unambiguously identify failed OCR
  extractions, rather than receiving empty cells that look like valid zeros.

- **JSON**: ``NaN`` (a floating-point concept not present in the JSON spec) is
  converted to ``None`` so the output is valid standard JSON that any JSON
  parser can consume.

Usage::

    from validation.formatters import prepare_df_for_csv, prepare_data_for_json

    # CSV export
    csv_bytes = prepare_df_for_csv(validated_df)

    # or write directly:
    prepare_df_for_csv(validated_df, path="output/results.csv")

    # JSON-safe conversion
    payload = prepare_data_for_json({"score": np.nan, "name": "สมชาย"})
    # -> {"score": null, "name": "สมชาย"}
"""

from __future__ import annotations

import io
import math
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def prepare_df_for_csv(
    df: pd.DataFrame,
    path: str | None = None,
    **kwargs: Any,
) -> str | None:
    """Serialise *df* to CSV with ``NaN`` values written as ``"MISSING"``.

    All keyword arguments beyond *path* are forwarded to
    :meth:`pandas.DataFrame.to_csv` so callers can customise encoding,
    separator, etc.

    Args:
        df:    DataFrame to serialise.  May contain ``numpy.nan`` / ``pd.NA``
               values in any column — they will appear as ``"MISSING"`` in the
               output.
        path:  If given, the CSV is written to this file path and ``None`` is
               returned.  If omitted (or ``None``), the CSV string is returned.
        **kwargs: Additional keyword arguments passed to ``DataFrame.to_csv``
               (e.g. ``encoding="utf-8-sig"``, ``sep=","``).

    Returns:
        CSV string when *path* is ``None``; ``None`` when a file path is given
        (the file is written as a side-effect).
    """
    kwargs.setdefault("na_rep", "MISSING")
    kwargs.setdefault("index", False)

    if path is not None:
        df.to_csv(path, **kwargs)
        return None

    return df.to_csv(**kwargs)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------


def _nan_to_none(value: Any) -> Any:
    """Recursively replace NaN/float('nan') with ``None`` in nested structures.

    Handles dicts, lists, and scalar values (numpy scalar types, plain floats).
    Non-numeric scalars are returned unchanged.
    """
    if isinstance(value, dict):
        return {k: _nan_to_none(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_nan_to_none(v) for v in value]
    # numpy scalar types (np.float64, np.int64, etc.)
    if isinstance(value, np.generic):
        scalar = value.item()
        if isinstance(scalar, float) and math.isnan(scalar):
            return None
        return scalar
    # plain Python float
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def prepare_data_for_json(data: Any) -> Any:
    """Convert *data* to a JSON-safe representation.

    ``numpy.nan`` and ``float("nan")`` are replaced with ``None`` (which
    serialises as JSON ``null``).  Numpy scalar types are unwrapped to their
    plain Python equivalents so the result is directly passable to
    ``json.dumps``.

    Args:
        data: Any Python value — typically a dict, list, or nested structure
              produced by :class:`~validation.engine.ElectionValidator`.

    Returns:
        A new object of the same shape with NaN replaced by ``None`` and numpy
        scalars replaced by native Python types.

    Example::

        import numpy as np
        result = prepare_data_for_json({"score": np.nan, "count": np.int64(5)})
        # -> {"score": None, "count": 5}
    """
    return _nan_to_none(data)
