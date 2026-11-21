"""Discovery tasks 2.1-2.2: seeds and the R/S split (ROADMAP section 3, step 3).

M = the sentences split here. discovery.use_rough_library: false -> PROTOTYPE, M = all
sentences of the corpus; true -> M = sentences with >= 1 IPCC rough-library bigram (task 3.1,
src.discovery.rough_library; the caller filters before run_split). Each M definition has its
own cache folder (discovery_dir), so both can be kept side by side.

R = sentences of M containing >= 1 seed bigram, S = all other sentences. A sentence's bigrams
come from the shared cleaner (src.preprocess.make_vectorizer), the same one used for scoring.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocess import make_vectorizer

PROTOTYPE_NOTE = "PROTOTYPE: M = all sentences, no rough library"
ROUGH_NOTE = "M = sentences with >= 1 rough-library bigram (task 3.1)"
OUT_COLS = ["file", "sentence_id", "sentence"]


def uses_rough(cfg: dict) -> bool:
    return bool(cfg["discovery"].get("use_rough_library", False))


def m_note(cfg: dict) -> str:
    return ROUGH_NOTE if uses_rough(cfg) else PROTOTYPE_NOTE


def discovery_dir(cfg: dict) -> Path:
    """cache/discovery (M = all sentences) or cache/discovery/m_rough (M = rough-library sentences)."""
    d = Path(cfg["paths"]["cache"]) / "discovery"
    if uses_rough(cfg):
        d = d / "m_rough"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_seeds(cfg: dict) -> list[str]:
    """The 50 Table IA.III seeds from config (order kept, duplicates rejected)."""
    seeds = [str(s).strip().lower() for s in cfg["seeds"]]
    if len(set(seeds)) != len(seeds):
        raise ValueError("config seeds contain duplicates")
    return seeds


def seed_matrix(sentences: list[str], seeds: list[str]):
    """Sparse (n_sentences x n_seeds) count matrix: seed bigram counts per sentence."""
    vec = make_vectorizer(vocabulary=seeds)
    return vec.transform(sentences).tocsr()


def split_rs(sents: pd.DataFrame, seeds: list[str]):
    """Return (R, S, seed_counts).

    R/S keep the input columns; seed_counts = number of R sentences containing each seed
    (document frequency over sentences), sorted descending, including zeros.
    """
    m = seed_matrix(sents["sentence"].tolist(), seeds)
    has_seed = np.asarray((m > 0).sum(axis=1)).ravel() > 0
    sent_df = np.asarray((m > 0).sum(axis=0)).ravel()
    seed_counts = pd.Series(sent_df, index=seeds, name="n_sentences").sort_values(ascending=False, kind="stable")
    return sents.loc[has_seed].reset_index(drop=True), sents.loc[~has_seed].reset_index(drop=True), seed_counts


def run_split(cfg: dict, sents: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tasks 2.1 + 2.2 on M (already filtered by the caller): report seeds, split, save R/S parquet."""
    print(f"[discover] {m_note(cfg)}  (|M| = {len(sents):,} sentences, "
          f"{sents['file'].nunique()} transcripts)")
    seeds = load_seeds(cfg)
    print(f"[discover] task 2.1: {len(seeds)} seeds loaded from config "
          f"(topic seeds: " + ", ".join(f"{k}={len(v)}" for k, v in cfg["topic_seeds"].items()) + ")")

    R, S, seed_counts = split_rs(sents[OUT_COLS], seeds)
    found = seed_counts[seed_counts > 0]
    missing = sorted(seed_counts[seed_counts == 0].index)
    print(f"[discover] seeds occurring in the sample: {len(found)}/{len(seeds)}")
    print(f"[discover] seeds that never occur ({len(missing)}): {', '.join(missing) if missing else '-'}")

    out = discovery_dir(cfg)
    R.to_parquet(out / "R.parquet", index=False)
    S.to_parquet(out / "S.parquet", index=False)
    print(f"[discover] task 2.2: |R| = {len(R):,}  |S| = {len(S):,}  "
          f"(R share {len(R) / max(len(sents), 1):.2%}) -> {out / 'R.parquet'}, {out / 'S.parquet'}")
    print("[discover] 10 most frequent seeds in R (sentences containing them):")
    for s, n in found.head(10).items():
        print(f"    {s:<28s} {n:>6,}")
    return R, S
