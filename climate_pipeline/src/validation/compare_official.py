"""Compare our firm-year scores with the official Sautner et al. firm-year csv.

Our column <m>_<s> is paired with official <m>_<s>_ew for m in cc/op/rg/ph and
s in expo/pos/neg/sent/risk. TF-IDF (Eq. 4) has no official column, so it is not compared.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.scoring import MEASURES, RISK_LISTS

SUFFIXES = ("expo", "pos", "neg", "sent", "risk")
PAIRS = [(f"{m}_{s}", f"{m}_{s}_ew") for m in MEASURES for s in SUFFIXES]
GAP_MEASURE = "cc_expo"


def load_official_all(path, verbose: bool = True) -> pd.DataFrame:
    """Official firm-year csv: isin, year and every <m>_<s>_ew column that exists."""
    head = pd.read_csv(path, nrows=0).columns
    used = [o for _, o in PAIRS if o in head]
    if verbose:
        missing = [o for _, o in PAIRS if o not in head]
        print(f"[compare_official] official columns used ({len(used)}): {', '.join(used)}")
        if missing:
            print(f"[compare_official] official columns missing: {', '.join(missing)}")
    return pd.read_csv(path, usecols=["isin", "year", *used], low_memory=False)


def merge_official(ours: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    """Inner merge on (isin, year); firm-years without an ISIN are dropped."""
    ours = ours[ours["isin"].notna()].copy()
    official = official.copy()
    for df in (ours, official):
        df["year"] = df["year"].astype("Int64")
    return ours.merge(official, on=["isin", "year"], how="inner", validate="many_to_one")


def compare_table(merged: pd.DataFrame) -> pd.DataFrame:
    """Per measure: n matched firm-years, Pearson, Spearman, median ratio ours/official.

    n counts firm-years where both values are non-missing; the ratio uses only those
    with official != 0 (n_ratio). Correlations are NaN when n < 3 or a side is constant.
    """
    return pd.DataFrame([{"measure": o, **_pair_stats(merged, o, e)}
                         for o, e in PAIRS if o in merged and e in merged])


def _pair_stats(merged: pd.DataFrame, ours_c: str, off_c: str) -> dict:
    """n, Pearson, Spearman, median ratio (official != 0), n_ratio, means for one column pair."""
    d = merged[[ours_c, off_c]].astype(float).dropna()
    x, y = d[ours_c], d[off_c]
    ok = len(d) >= 3 and x.nunique() > 1 and y.nunique() > 1
    nz = y != 0
    return {
        "n": len(d),
        "pearson": x.corr(y) if ok else np.nan,
        "spearman": x.corr(y, method="spearman") if ok else np.nan,
        "median_ratio": (x[nz] / y[nz]).median() if nz.any() else np.nan,
        "n_ratio": int(nz.sum()),
        "mean_ours": x.mean(),
        "mean_official": y.mean(),
    }


def risk_sensitivity(merged: pd.DataFrame) -> pd.DataFrame:
    """Our <m>_risk_<list> vs official <m>_risk_ew: one row per (measure, risk list).

    Needs the <m>_risk_<list> columns written by full-corpus scoring (RISK_VARIANT_COLS).
    """
    rows = []
    for m in MEASURES:
        off_c = f"{m}_risk_ew"
        for r in RISK_LISTS:
            ours_c = f"{m}_risk_{r}"
            if ours_c in merged and off_c in merged:
                rows.append({"measure": f"{m}_risk", "risk_list": r, **_pair_stats(merged, ours_c, off_c)})
    return pd.DataFrame(rows)


def largest_gaps(merged: pd.DataFrame, k: int = 5, measure: str = GAP_MEASURE) -> pd.DataFrame:
    """The k firm-years with the largest |ours - official| on `measure`."""
    off = f"{measure}_ew"
    cols = [c for c in ("ticker", "isin", "year", "n_transcripts") if c in merged]
    d = merged[cols + [measure, off]].dropna(subset=[measure, off]).copy()
    d["gap"] = d[measure] - d[off]
    d["ratio"] = d[measure] / d[off].replace(0, np.nan)
    return d.reindex(d["gap"].abs().sort_values(ascending=False).index).head(k).reset_index(drop=True)
