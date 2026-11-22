"""Stage `presentation`: pure helpers (no data files needed)."""
import numpy as np
import pandas as pd
import pytest

from src.presentation import (SECTOR_COLOR, SECTORS, bootstrap_spearman, human_precision,
                              sector_of, table1)

CORPUS_TICKERS = ["BA", "CAT", "COP", "CVX", "D", "DAL", "DUK", "F", "GM", "HON", "JPM", "KO",
                  "MMM", "MSFT", "NEE", "OXY", "PFE", "SO", "UNH", "WMT", "XOM"]


def test_every_corpus_ticker_has_a_sector_with_a_colour():
    for t in CORPUS_TICKERS:
        assert sector_of(t) in SECTOR_COLOR
    assert sector_of("xom") == "oil & gas"
    assert len(set(SECTORS.values())) <= 8          # fixed categorical palette has 8 slots
    with pytest.raises(KeyError):
        sector_of("AAPL")


def test_bootstrap_point_estimate_matches_pandas_and_ci_brackets_it():
    rng = np.random.default_rng(0)
    y = rng.normal(size=80)
    df = pd.DataFrame({"off": y, "base": y + rng.normal(scale=2, size=80),
                       "good": y + rng.normal(scale=0.2, size=80)})
    df.loc[:9, "base"] = 0.0                         # ties
    tab, draws = bootstrap_spearman(df, ["base", "good"], "off", "base", n_boot=300, seed=1)
    for v in ("base", "good"):
        r = tab.set_index("variant").loc[v]
        assert r["spearman"] == pytest.approx(df[v].corr(df["off"], method="spearman"))
        assert r["spearman_ci_lo"] <= r["spearman"] <= r["spearman_ci_hi"]
    g = tab.set_index("variant")
    assert g.loc["base", "gain_vs_base"] == 0
    assert g.loc["good", "gain_ci_lo"] > 0           # clearly better variant: CI excludes 0
    assert draws.shape == (300, 2)
    tab2, _ = bootstrap_spearman(df, ["base", "good"], "off", "base", n_boot=300, seed=1)
    pd.testing.assert_frame_equal(tab, tab2)         # seeded -> reproducible


def test_human_precision_empty_and_filled():
    hc = pd.DataFrame({"source": ["t_only", "top_pct", "top_pct", "top_pct"],
                       "is_climate": [np.nan] * 4})
    assert human_precision(hc) is None
    hc["is_climate"] = [1, 1, 0, np.nan]
    p = human_precision(hc).set_index("group")
    assert p.loc["overall", "precision"] == pytest.approx(2 / 3)
    assert p.loc["overall", "n_labelled"] == 3
    assert p.loc["t_only", "precision"] == 1.0
    assert p.loc["top_pct", "precision"] == 0.5


def test_table1_reshapes_compare_official():
    cmp_ = pd.DataFrame({"measure": ["cc_expo", "cc_risk", "ph_expo"], "n": [362] * 3,
                         "pearson": [0.98, 0.68, 0.71], "spearman": [0.94, 0.63, 0.66],
                         "median_ratio": [0.84, 0.40, 0.48]})
    t = table1(cmp_)
    assert list(t.columns) == ["measure", "stat", "n", "pearson", "spearman", "median_ratio"]
    assert t[(t.measure == "cc") & (t.stat == "risk")]["pearson"].iloc[0] == 0.68
    assert len(t) == 3
