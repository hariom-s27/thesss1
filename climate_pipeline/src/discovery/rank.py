"""Discovery task 2.4: rank candidate bigrams of S by how strongly they concentrate in T.

ROADMAP section 3, step 6 (Internet Appendix I). Unit = sentence.

Candidates = every bigram in S (shared cleaner src.preprocess.make_vectorizer, so bigrams
never cross sentences), minus the 50 seeds (S has no seed by construction; removed anyway).
For bigram k:
    n_kT  = #T sentences containing k        N_T  = |T|
    n_kST = #(S\\T) sentences containing k    N_ST = |S\\T|

(a) T-only bigrams (n_kST == 0): kept if n_kT >= discovery.min_t_only_df.
    The paper keeps ALL T-only bigrams, but its vocabulary was already pruned at preprocessing
    (bigrams with frequency < 10 dropped), so a one-off typo / name never reached this step.
    We do not prune the vocabulary, so the df floor plays that role.
(b) shared bigrams (n_kT > 0 and n_kST > 0): kept if n_kT / N_T > n_kST / N_ST.
    INTERPRETATION: the paper says "document frequency higher in T than in S\\T". With raw
    counts the small T set (~2% of S) would almost never win, so we compare PROPORTIONS.
    Survivors are ranked by the King, Lam & Roberts (2017) Beta-binomial likelihood
    (alpha = 1, log-gamma form, no overflow):
        king = betaln(n_kT + 1, n_kST + 1) + betaln(N_T - n_kT + 1, N_ST - n_kST + 1)
    Higher = the split of k between T and S\\T is less like the base split (the score is
    lowest for a bigram spread in proportion to the set sizes). The top discovery.top_pct
    of the survivors are kept.

The King score is stored for every candidate (also T-only ones, where it is increasing in
n_kT, so ranking T-only bigrams by king_score = ranking them by n_kT).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.special import betaln

from src.discovery.split import discovery_dir, load_seeds
from src.preprocess import make_vectorizer

SOURCES = ("t_only", "top_pct", "dropped")
RANK_COLS = ["bigram", "n_kT", "n_kST", "prop_T", "prop_ST", "king_score", "source"]


# ---- the S sentence x bigram matrix (binary), cached -----------------------------------

def s_bigram_matrix(sentences: list[str]) -> tuple[sparse.csr_matrix, np.ndarray]:
    """Binary (n_sentences x n_bigrams) CSR matrix of S and its bigram names."""
    vec = make_vectorizer()
    vec.set_params(binary=True, dtype=np.int8)
    X = vec.fit_transform(sentences).tocsr()
    return X, vec.get_feature_names_out().astype(object)


def load_s_bigrams(cfg: dict, S: pd.DataFrame, force: bool = False, verbose: bool = True):
    """Return (X, feats) for S, cached as cache/discovery/S_bigrams.npz + S_bigram_vocab.parquet.

    The cache is reused when its row count and (file, sentence_id) key hash match S.
    """
    d = discovery_dir(cfg)
    xp, vp, kp = d / "S_bigrams.npz", d / "S_bigram_vocab.parquet", d / "S_bigrams_key.txt"
    key = f"{len(S)}:{pd.util.hash_pandas_object(S[['file', 'sentence_id']], index=False).sum()}"
    if not force and xp.exists() and vp.exists() and kp.exists() and kp.read_text() == key:
        if verbose:
            print(f"[discover] reusing S bigram matrix {xp}")
        return sparse.load_npz(xp).tocsr(), pd.read_parquet(vp)["bigram"].to_numpy(dtype=object)
    if verbose:
        print(f"[discover] building S bigram matrix ({len(S):,} sentences) ...")
    X, feats = s_bigram_matrix(S["sentence"].tolist())
    sparse.save_npz(xp, X)
    pd.DataFrame({"bigram": feats}).to_parquet(vp, index=False)
    kp.write_text(key)
    if verbose:
        print(f"[discover] S bigram matrix: {X.shape[0]:,} x {X.shape[1]:,} (nnz {X.nnz:,}) -> {xp}")
    return X, feats


# ---- pure ranking core -----------------------------------------------------------------

def king_score(n_kT, n_kST, N_T: int, N_ST: int) -> np.ndarray:
    """King, Lam & Roberts (2017) log Beta-binomial likelihood, alpha = 1 (finite for big counts)."""
    n_kT = np.asarray(n_kT, dtype=float)
    n_kST = np.asarray(n_kST, dtype=float)
    return betaln(n_kT + 1, n_kST + 1) + betaln(N_T - n_kT + 1, N_ST - n_kST + 1)


def rank_counts(bigrams, n_kT, n_kST, N_T: int, N_ST: int, min_t_only_df: int,
                top_pct: float, exclude=()) -> pd.DataFrame:
    """Apply rules (a) + (b) to per-bigram sentence counts. Returns RANK_COLS, best first.

    Sort order: kept bigrams first (t_only + top_pct together, by king_score desc), then dropped.
    """
    df = pd.DataFrame({"bigram": np.asarray(bigrams, dtype=object),
                       "n_kT": np.asarray(n_kT, dtype=np.int64),
                       "n_kST": np.asarray(n_kST, dtype=np.int64)})
    if len(exclude):
        df = df[~df["bigram"].isin(set(exclude))]
    df = df[(df["n_kT"] + df["n_kST"]) > 0].reset_index(drop=True)
    df["prop_T"] = df["n_kT"] / N_T if N_T else 0.0
    df["prop_ST"] = df["n_kST"] / N_ST if N_ST else 0.0
    df["king_score"] = king_score(df["n_kT"], df["n_kST"], N_T, N_ST)
    df["source"] = "dropped"

    t_only = (df["n_kST"] == 0) & (df["n_kT"] >= min_t_only_df)
    df.loc[t_only, "source"] = "t_only"

    shared_ok = (df["n_kT"] > 0) & (df["n_kST"] > 0) & (df["prop_T"] > df["prop_ST"])
    n_keep = int(np.ceil(top_pct * shared_ok.sum())) if shared_ok.any() else 0
    if n_keep:
        top = df.loc[shared_ok].sort_values(["king_score", "n_kT", "bigram"],
                                            ascending=[False, False, True], kind="stable").index[:n_keep]
        df.loc[top, "source"] = "top_pct"

    df["_kept"] = df["source"] != "dropped"
    df = (df.sort_values(["_kept", "king_score", "n_kT", "bigram"],
                         ascending=[False, False, False, True], kind="stable")
          .drop(columns="_kept").reset_index(drop=True))
    return df[RANK_COLS]


def rank_from_matrix(X: sparse.csr_matrix, feats, in_T: np.ndarray, min_t_only_df: int,
                     top_pct: float, exclude=()) -> tuple[pd.DataFrame, dict]:
    """Counts from the binary S matrix and a T mask, then rank_counts. Returns (ranked, info)."""
    in_T = np.asarray(in_T, dtype=bool)
    n_kT = np.asarray(X[in_T].sum(axis=0)).ravel()
    n_kST = np.asarray(X[~in_T].sum(axis=0)).ravel()
    N_T, N_ST = int(in_T.sum()), int((~in_T).sum())
    ranked = rank_counts(feats, n_kT, n_kST, N_T, N_ST, min_t_only_df, top_pct, exclude)
    n_shared_ok = int(((ranked["n_kT"] > 0) & (ranked["n_kST"] > 0)
                       & (ranked["prop_T"] > ranked["prop_ST"])).sum())
    info = {"N_T": N_T, "N_ST": N_ST, "n_candidates": len(ranked),
            "n_in_T": int((ranked["n_kT"] > 0).sum()),
            "n_t_only_all": int((ranked["n_kST"] == 0).sum()),
            "n_shared_ok": n_shared_ok,
            **{f"n_{s}": int((ranked["source"] == s).sum()) for s in SOURCES}}
    return ranked, info


# ---- stage wrapper ---------------------------------------------------------------------

def rank_params(cfg: dict) -> tuple[int, float]:
    d = cfg["discovery"]
    return int(d.get("min_t_only_df", 3)), float(d.get("top_pct", 0.05))


def run_rank(cfg: dict, S: pd.DataFrame, scored: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    """Task 2.4 on the cached S / S_scored: save cache/discovery/ranked_bigrams.parquet."""
    if not (S[["file", "sentence_id"]].to_numpy() == scored[["file", "sentence_id"]].to_numpy()).all():
        raise ValueError("S.parquet and S_scored.parquet rows are not aligned; re-run --stage discover --force")
    min_t, top_pct = rank_params(cfg)
    X, feats = load_s_bigrams(cfg, S, force=force)
    ranked, info = rank_from_matrix(X, feats, scored["in_T"].to_numpy(), min_t, top_pct,
                                    exclude=load_seeds(cfg))
    out = discovery_dir(cfg) / "ranked_bigrams.parquet"
    ranked.to_parquet(out, index=False)
    print(f"[discover] task 2.4: N_T = {info['N_T']:,}  N_ST = {info['N_ST']:,}  "
          f"candidates = {info['n_candidates']:,} bigrams in S ({info['n_in_T']:,} occur in T)")
    print(f"[discover]   (a) T-only: {info['n_t_only_all']:,} bigrams, kept {info['n_t_only']:,} "
          f"with n_kT >= {min_t}")
    print(f"[discover]   (b) shared with prop_T > prop_ST: {info['n_shared_ok']:,}, kept top "
          f"{top_pct:.0%} by King score = {info['n_top_pct']:,}")
    print(f"[discover]   -> {out}")
    return ranked


def load_ranked(cfg: dict) -> pd.DataFrame:
    p = Path(discovery_dir(cfg)) / "ranked_bigrams.parquet"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run --stage discover first")
    return pd.read_parquet(p)
