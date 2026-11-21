"""Task 1.4: comparison with the official firm-year csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

from src.validation.compare_official import compare_table, largest_gaps, merge_official  # noqa: E402


def _fake():
    ours = pd.DataFrame({
        "ticker": ["A", "A", "B", "C", "D"],
        "isin": ["I1", "I1", "I2", "I3", None],      # D has no ISIN -> dropped
        "year": [2020, 2021, 2020, 2020, 2020],
        "cc_expo": [1.0, 2.0, 3.0, 4.0, 9.0],
        "cc_neg": [-1.0, -2.0, -3.0, -4.0, -9.0],
    })
    off = pd.DataFrame({
        "isin": ["I1", "I1", "I2", "I3", "I9"],
        "year": [2020, 2021, 2020, 2020, 2020],
        "cc_expo_ew": [2.0, 4.0, 5.0, 10.0, 1.0],
        "cc_neg_ew": [-2.0, -4.0, -6.0, -8.0, -1.0],
        "op_expo_ew": [0.1, 0.2, 0.3, 0.4, 0.5],      # ours has no op_expo -> skipped
    })
    return merge_official(ours, off)


def test_merge_drops_unmatched_and_missing_isin():
    m = _fake()
    assert len(m) == 4 and set(m["ticker"]) == {"A", "B", "C"}


def test_correlations_and_ratio():
    tab = compare_table(_fake()).set_index("measure")
    x, y = np.array([1, 2, 3, 4.0]), np.array([2, 4, 5, 10.0])
    assert tab.loc["cc_expo", "n"] == 4
    assert tab.loc["cc_expo", "pearson"] == pytest.approx(np.corrcoef(x, y)[0, 1])
    assert tab.loc["cc_expo", "spearman"] == pytest.approx(1.0)
    assert tab.loc["cc_expo", "median_ratio"] == pytest.approx(np.median(x / y))
    assert tab.loc["cc_neg", "pearson"] == pytest.approx(1.0)       # ours = official / 2 exactly
    assert tab.loc["cc_neg", "median_ratio"] == pytest.approx(0.5)
    assert "op_expo" not in tab.index


def test_largest_gaps():
    g = largest_gaps(_fake(), k=2)
    assert list(g["ticker"]) == ["C", "A"] and list(g["year"]) == [2020, 2021]
    assert g.loc[0, "gap"] == pytest.approx(-6.0)
