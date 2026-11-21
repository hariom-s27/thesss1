"""Sautner et al. (2023) scoring, for the 4 authors' dictionaries: cc (CCExposure),
op (Opp), rg (Reg), ph (Phy). Bigrams come from the shared cleaner (src/preprocess.py).

Eq. (1) <m>_expo  = (count of transcript bigrams in dictionary D) / B,
        B = the transcript's total bigram count.
Eq. (2) <m>_pos / <m>_neg = (1/B) * climate bigrams in sentences that contain a
        Loughran-McDonald positive / negative word. <m>_neg is stored NEGATIVE (as the
        authors do) and <m>_sent = (pos - neg) / B = <m>_pos + <m>_neg.
Eq. (3) <m>_risk  = (1/B) * climate bigrams in sentences that contain a risk word
        (config settings.risk_list: narrow | curated | lm_unc).
Eq. (4) <m>_expo_tfidf = (1/B) * sum_b count(b) * log(N / f_b), N = transcripts in the
        scored set, f_b = transcripts containing b. Depends on the scored set (see add_tfidf).

Eq. 2-3 copy week1_thesis/phase2_sentiment_risk.py measures(); Eq. 4 copies
week1_thesis/phase3_tfidf.py.
"""
from __future__ import annotations

import pickle
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocess import sentence_bigram_matrix

MEASURES = ("cc", "op", "rg", "ph")
EXPO_COLS = [f"{m}_expo" for m in MEASURES]
TONE_SUFFIXES = ("pos", "neg", "sent", "risk")
TONE_COLS = [f"{m}_{s}" for m in MEASURES for s in TONE_SUFFIXES]
TFIDF_COLS = [f"{m}_expo_tfidf" for m in MEASURES]
SCORE_COLS = EXPO_COLS + TONE_COLS + TFIDF_COLS

# ---- Eq. 3 risk vocabularies (same three lists as phase2_sentiment_risk.py) --------
# The paper says "risk", "uncertainty", or their synonyms but never lists them.
RISK_NARROW = frozenset({"risk", "risky", "uncertainty", "uncertain"})
RISK_CURATED = RISK_NARROW | {
    "volatile", "volatility", "threat", "hazard", "danger", "doubt", "doubtful",
    "unpredictable", "unclear", "exposure", "fluctuate", "fluctuation",
    "probable", "possible", "likelihood", "chance", "vary", "variable",
}
RISK_LISTS = ("narrow", "curated", "lm_unc")  # lm_unc = narrow | whole LM Uncertainty list


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


def load_lm_words() -> dict[str, frozenset[str]]:
    """Loughran-McDonald POS / NEG / UNC word sets from pysentiment2's static/LM.csv."""
    import pysentiment2

    lm = pd.read_csv(Path(pysentiment2.__file__).parent / "static" / "LM.csv")
    return {
        "pos": frozenset(lm.loc[lm["Positive"] > 0, "Word"].str.lower()),
        "neg": frozenset(lm.loc[lm["Negative"] > 0, "Word"].str.lower()),
        "unc": frozenset(lm.loc[lm["Uncertainty"] > 0, "Word"].str.lower()),
    }


def load_lexicons(cfg: dict, verbose: bool = True) -> dict[str, frozenset[str]]:
    """{"pos", "neg", "risk"} word sets for Eq. 2-3; risk list from settings.risk_list.

    NOTE (known limitation, kept on purpose to match the old script): transcript words
    are spaCy lemmas, but the LM words are NOT lemmatized, so inflected LM entries
    (e.g. "losses", "risks") can never match a lemma. Do not change this now.
    """
    choice = cfg["settings"].get("risk_list", "curated")
    if choice not in RISK_LISTS:
        raise ValueError(f"settings.risk_list must be one of {RISK_LISTS}, got {choice!r}")
    lm = load_lm_words()
    risk = {"narrow": RISK_NARROW, "curated": RISK_CURATED,
            "lm_unc": RISK_NARROW | lm["unc"]}[choice]
    if verbose:
        print(f"[score] risk_list = {choice} ({len(risk)} words); "
              f"LM pos={len(lm['pos'])}, neg={len(lm['neg'])}")
    return {"pos": lm["pos"], "neg": lm["neg"], "risk": frozenset(risk)}


def transcript_parts(sentences: list[str], dicts: dict[str, frozenset[str]],
                     lex: dict[str, frozenset[str]] | None = None) -> tuple[dict, dict]:
    """Eq. 1-3 for one transcript + the dictionary-bigram counts needed for Eq. 4.

    Returns (rec, counts): rec = {B, <m>_expo, and if lex given <m>_pos/neg/sent/risk};
    counts = {m: {bigram: count in this transcript}} for bigrams in dictionary m.
    A transcript with no bigrams gets B=0 and NaN scores.
    """
    sentences = list(sentences)
    M, feats = sentence_bigram_matrix(sentences)
    B = int(M.sum()) if M is not None else 0
    rec: dict = {"B": B}
    counts: dict[str, dict[str, int]] = {m: {} for m in MEASURES}
    if lex is not None:
        # per sentence: does it contain a pos / neg / risk word? (words = s.split(), as old)
        words = [set(s.split()) for s in sentences]
        has = {k: np.array([bool(w & lex[k]) for w in words], dtype=bool) for k in ("pos", "neg", "risk")}
    col_tot = np.asarray(M.sum(axis=0)).ravel() if M is not None else np.array([])
    for m in MEASURES:
        D = dicts.get(m, ())
        member = np.array([f in D for f in feats], dtype=np.int64)
        counts[m] = {feats[j]: int(col_tot[j]) for j in np.flatnonzero(member)}
        if not B:
            rec[f"{m}_expo"] = np.nan
            if lex is not None:
                rec.update({f"{m}_{s}": np.nan for s in TONE_SUFFIXES})
            continue
        hits = np.asarray(M @ member).ravel()  # climate bigrams per sentence (exact ints)
        rec[f"{m}_expo"] = int(hits.sum()) / B
        if lex is not None:
            pos, neg, risk = (int(hits[has[k]].sum()) for k in ("pos", "neg", "risk"))
            rec[f"{m}_pos"] = pos / B
            rec[f"{m}_neg"] = -neg / B  # stored NEGATIVE, matching the authors
            rec[f"{m}_sent"] = (pos - neg) / B
            rec[f"{m}_risk"] = risk / B
    return rec, counts


def score_transcript(sentences: list[str], dicts: dict[str, frozenset[str]],
                     lex: dict[str, frozenset[str]] | None = None) -> dict:
    """Eq. 1 (and Eq. 2-3 if lex is given) for one transcript of lemmatized sentences."""
    return transcript_parts(sentences, dicts, lex)[0]


def add_tfidf(recs: list[dict], counts: list[dict], verbose: bool = True) -> list[dict]:
    """Eq. (4), in place: <m>_expo_tfidf = (1/B) * sum_b count(b) * log(N / f_b).

    N = number of transcripts in recs (the scored set), f_b = transcripts containing b.
    A bigram present in every transcript gets weight log(1) = 0.
    """
    N = len(recs)
    if verbose:
        print(f"[score] WARNING: TF-IDF weights depend on N (= {N} transcripts here); "
              "sample and full-corpus runs give different weights and are not comparable.")
    for m in MEASURES:
        doc_freq = Counter(b for c in counts for b in c[m])  # +1 per transcript, not per occurrence
        for rec, c in zip(recs, counts):
            if not rec["B"]:
                rec[f"{m}_expo_tfidf"] = np.nan
                continue
            w = sum(n * np.log(N / doc_freq[b]) for b, n in c[m].items())
            rec[f"{m}_expo_tfidf"] = float(w) / rec["B"]
    return recs


def score_sentences_df(sent_df: pd.DataFrame, dicts: dict, lex: dict | None = None,
                       log_every: int = 50) -> pd.DataFrame:
    """Score every transcript in a sentences table (file, ticker, year, quarter, sentence_id, sentence).

    Eq. 1-3 per transcript, then Eq. 4 over the whole table (two passes, as phase3_tfidf.py).
    """
    keys = ["file", "ticker", "year", "quarter"]
    sent_df = sent_df.sort_values(["file", "sentence_id"])
    groups = sent_df.groupby("file", sort=True)
    recs, counts = [], []
    for i, (_, g) in enumerate(groups, 1):
        rec = {k: g[k].iloc[0] for k in keys if k in g}
        r, c = transcript_parts(g["sentence"].tolist(), dicts, lex)
        rec.update(r)
        recs.append(rec)
        counts.append(c)
        if i % log_every == 0 or i == groups.ngroups:
            print(f"[score] {i}/{groups.ngroups} transcripts")
    add_tfidf(recs, counts)
    return pd.DataFrame(recs)


def firm_year(scores_df: pd.DataFrame) -> pd.DataFrame:
    """Firm-year score = mean of the quarterly transcript scores by (ticker, isin, year)."""
    keys = ["ticker", "isin", "year"]
    cols = [c for c in SCORE_COLS if c in scores_df]
    g = scores_df.groupby(keys, dropna=False, sort=True)
    out = g[cols].mean()
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
