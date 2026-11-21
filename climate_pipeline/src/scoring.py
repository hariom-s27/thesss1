"""Sautner et al. (2023) scoring.

Eq. (1): exposure = (count of transcript bigrams in dictionary D) / B, where B is the
transcript's total bigram count. Bigrams come from the shared cleaner (src/preprocess.py).
Computed for the 4 authors' dictionaries: cc (CCExposure), op (Opp), rg (Reg), ph (Phy).
Eq. 2-4 (sentiment, risk, TF-IDF) follow in tasks 1.2-1.3.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocess import bigram_counts

MEASURES = ("cc", "op", "rg", "ph")
EXPO_COLS = [f"{m}_expo" for m in MEASURES]


def load_dictionaries(cfg: dict, verbose: bool = True) -> dict[str, frozenset[str]]:
    """The 4 authors' .pkl dictionaries as lowercased sets: {"cc", "op", "rg", "ph"}."""
    d = Path(cfg["paths"]["authors_dictionaries"])
    out = {}
    for m in MEASURES:
        with open(d / cfg["dictionaries"][m], "rb") as f:
            out[m] = frozenset(str(x).lower() for x in pickle.load(f))
    if verbose:
        print("[score] dictionary sizes: " + ", ".join(f"{m}={len(out[m]):,}" for m in MEASURES))
    return out


def score_transcript(sentences: list[str], dicts: dict[str, frozenset[str]]) -> dict:
    """Eq. (1) for one transcript (list of lemmatized sentences).

    Returns {B, cc_expo, op_expo, rg_expo, ph_expo}. A transcript with no bigrams
    gets B=0 and NaN exposures.
    """
    counts = bigram_counts(list(sentences))
    B = sum(counts.values())
    out = {"B": int(B)}
    for m in MEASURES:
        hit = sum(c for b, c in counts.items() if b in dicts.get(m, ()))
        out[f"{m}_expo"] = hit / B if B else np.nan
    return out


def score_sentences_df(sent_df: pd.DataFrame, dicts: dict, log_every: int = 50) -> pd.DataFrame:
    """Score every transcript in a sentences table (file, ticker, year, quarter, sentence_id, sentence)."""
    keys = ["file", "ticker", "year", "quarter"]
    sent_df = sent_df.sort_values(["file", "sentence_id"])
    groups = sent_df.groupby("file", sort=True)
    rows = []
    for i, (_, g) in enumerate(groups, 1):
        rec = {k: g[k].iloc[0] for k in keys if k in g}
        rec.update(score_transcript(g["sentence"].tolist(), dicts))
        rows.append(rec)
        if i % log_every == 0 or i == groups.ngroups:
            print(f"[score] {i}/{groups.ngroups} transcripts")
    return pd.DataFrame(rows)


def firm_year(scores_df: pd.DataFrame) -> pd.DataFrame:
    """Firm-year score = mean of the quarterly transcript scores by (ticker, isin, year)."""
    keys = ["ticker", "isin", "year"]
    g = scores_df.groupby(keys, dropna=False, sort=True)
    out = g[EXPO_COLS].mean()
    out["n_transcripts"] = g.size()
    return out.reset_index()


def load_official(cfg: dict, isin: str) -> pd.DataFrame:
    """Official firm-year exposures for one ISIN, columns year + <m>_expo_ew."""
    cols = ["isin", "year", *[f"{c}_ew" for c in EXPO_COLS]]
    off = pd.read_csv(cfg["paths"]["official_scores"], usecols=cols, low_memory=False)
    return off[off["isin"] == isin].drop(columns="isin")


def check_xom(cfg: dict) -> pd.DataFrame:
    """Score the PDF transcripts (all XOM), average to firm-year, compare with official.

    Returns one row per year with our <m>_expo, official <m>_expo_ew and <m>_pct (% of official).
    """
    from src.io_utils import list_transcripts, read_text
    from src.preprocess import lemmatize

    pdfs = list_transcripts(cfg, sources=("pdf",))
    if pdfs.empty:
        raise FileNotFoundError(f"no PDFs in pdf_dir: {cfg['paths']['pdf_dir']}")
    dicts = load_dictionaries(cfg)
    rows = []
    for r in pdfs.itertuples(index=False):
        rec = {"file": r.file, "ticker": r.ticker, "isin": r.isin, "year": r.year, "quarter": r.quarter}
        rec.update(score_transcript(lemmatize(read_text(r.path)), dicts))
        rows.append(rec)
        print(f"[check_xom] {r.file}: B={rec['B']:,} cc_expo={rec['cc_expo']:.5f}")
    fy = firm_year(pd.DataFrame(rows))

    isin = cfg["settings"]["pdf_isin"]
    fy["year"] = fy["year"].astype("Int64")
    off = load_official(cfg, isin)
    off["year"] = off["year"].astype("Int64")
    out = fy.merge(off, on="year", how="left")
    for c in EXPO_COLS:
        m = c.split("_")[0]
        out[f"{m}_pct"] = 100 * out[c] / out[f"{c}_ew"].replace(0, np.nan)
    return out
