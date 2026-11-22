"""Task 2.7: score the same transcripts with two cc dictionaries (discovered vs authors) and
correlate firm-year cc_expo with each other and with the official cc_expo_ew.

Only Eq. 1 cc_expo is compared (op/rg/ph are the authors' in both runs until Phase 3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.scoring import score_transcript

KEYS = ["ticker", "isin", "year"]


def cc_expo_by_transcript(sent_df: pd.DataFrame, cc: frozenset[str]) -> pd.DataFrame:
    """file, ticker, year, quarter, B, cc_expo for every transcript (Eq. 1 with dictionary cc)."""
    rows = []
    for f, g in sent_df.sort_values(["file", "sentence_id"]).groupby("file", sort=True):
        r = score_transcript(g["sentence"].tolist(), {"cc": cc})
        rows.append({"file": f, "ticker": g["ticker"].iloc[0], "year": g["year"].iloc[0],
                     "quarter": g["quarter"].iloc[0], "B": r["B"], "cc_expo": r["cc_expo"]})
    return pd.DataFrame(rows)


def _corr_row(name: str, x: pd.Series, y: pd.Series) -> dict:
    d = pd.concat([x, y], axis=1).astype(float).dropna()
    a, b = d.iloc[:, 0], d.iloc[:, 1]
    ok = len(d) >= 3 and a.nunique() > 1 and b.nunique() > 1
    return {"pair": name, "n": len(d),
            "pearson": a.corr(b) if ok else np.nan,
            "spearman": a.corr(b, method="spearman") if ok else np.nan,
            "mean_x": a.mean(), "mean_y": b.mean()}


def compare_dicts(sent_df: pd.DataFrame, cc_discovered, cc_authors, isin_map: dict,
                  official: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (firm-year table, correlation table).

    firm-year table: ticker, isin, year, cc_expo_disc, cc_expo_auth, cc_expo_ew (official, may be NaN).
    Correlations vs official use only firm-years matched on (isin, year), the same set for both.
    """
    parts = []
    for tag, cc in (("disc", frozenset(cc_discovered)), ("auth", frozenset(cc_authors))):
        t = cc_expo_by_transcript(sent_df, cc)
        t["isin"] = t["ticker"].map(lambda s: isin_map.get(str(s).upper()))
        fy = (t.groupby(KEYS, dropna=False, sort=True)["cc_expo"].mean()
              .rename(f"cc_expo_{tag}"))
        parts.append(fy)
    fy = pd.concat(parts, axis=1).reset_index()
    fy["year"] = fy["year"].astype("Int64")

    if official is not None and len(official):
        off = official[["isin", "year", "cc_expo_ew"]].copy()
        off["year"] = off["year"].astype("Int64")
        fy = fy.merge(off.drop_duplicates(["isin", "year"]), on=["isin", "year"], how="left")
    else:
        fy["cc_expo_ew"] = np.nan

    m = fy.dropna(subset=["cc_expo_ew"])
    corr = pd.DataFrame([
        _corr_row("discovered vs authors (all firm-years)", fy["cc_expo_disc"], fy["cc_expo_auth"]),
        _corr_row("discovered vs authors (matched official)", m["cc_expo_disc"], m["cc_expo_auth"]),
        _corr_row("discovered vs official", m["cc_expo_disc"], m["cc_expo_ew"]),
        _corr_row("authors vs official", m["cc_expo_auth"], m["cc_expo_ew"]),
    ])
    return fy, corr
