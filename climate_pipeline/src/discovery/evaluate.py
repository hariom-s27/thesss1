"""Discovery task 2.6: compare C_discovered with the authors' cc dictionary (9,641 bigrams),
plus the T-rule sensitivity DIAGNOSTIC (defaults are not changed by it).

Metrics
  precision@k   share of our top-k discovered bigrams (seeds excluded; ranked by king_score,
                which for T-only bigrams is increasing in n_kT) that are in the authors' list;
                k = 50, 100, 500, all.
  reachable recall
                of the authors' bigrams that occur at least once in OUR corpus (R ∪ S), the
                share in C_discovered. Also reported: seeds excluded, and restricted to authors'
                bigrams that occur in S (only S bigrams are candidates, so bigrams seen only in
                R sentences can never be discovered).
  T quality     share of T sentences vs S\\T sentences containing >= 1 authors' bigram (seeds
                excluded; S holds no seed anyway) and the ratio T rate / S\\T rate.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.discovery.build_dict import KEPT, build_dictionary
from src.discovery.classify import MODELS
from src.discovery.rank import load_s_bigrams, rank_from_matrix, rank_params
from src.discovery.split import discovery_dir, load_seeds
from src.preprocess import make_vectorizer

KS = (50, 100, 500, None)  # None = all


def ranked_discovered(ranked: pd.DataFrame, seeds) -> pd.DataFrame:
    """Kept non-seed bigrams, best first (king_score desc, as stored by rank_counts)."""
    kept = ranked[ranked["source"].isin(KEPT) & ~ranked["bigram"].isin(set(seeds))]
    return kept.sort_values(["king_score", "n_kT", "bigram"], ascending=[False, False, True],
                            kind="stable").reset_index(drop=True)


def precision_at_k(bigrams, authors, ks=KS) -> dict:
    authors = set(authors)
    hits = np.array([b in authors for b in bigrams], dtype=bool)
    out = {}
    for k in ks:
        sel = hits if k is None else hits[:k]
        out["all" if k is None else k] = float(sel.mean()) if len(sel) else np.nan
    return out


def reachable_recall(authors, corpus_vocab, s_vocab, C, seeds) -> dict:
    authors, C, seeds = set(authors), set(C), set(seeds)
    reach = authors & set(corpus_vocab)
    reach_s = authors & set(s_vocab)
    reach_ns = reach - seeds
    return {
        "n_authors": len(authors),
        "n_reachable": len(reach),
        "n_found": len(reach & C),
        "recall": len(reach & C) / len(reach) if reach else np.nan,
        "recall_ex_seeds": len(reach_ns & C) / len(reach_ns) if reach_ns else np.nan,
        "n_reachable_S": len(reach_s),
        "recall_S": len(reach_s & C) / len(reach_s) if reach_s else np.nan,
    }


def t_quality(X, feats, in_T, authors_ex_seeds) -> dict:
    """Share of T / S\\T sentences (rows of binary X) holding >= 1 authors' bigram."""
    in_T = np.asarray(in_T, dtype=bool)
    authors_ex_seeds = set(authors_ex_seeds)
    cols = np.flatnonzero([f in authors_ex_seeds for f in feats])
    has = np.asarray(X[:, cols].sum(axis=1)).ravel() > 0
    rate_t = float(has[in_T].mean()) if in_T.any() else np.nan
    rate_st = float(has[~in_T].mean()) if (~in_T).any() else np.nan
    return {"rate_T": rate_t, "rate_ST": rate_st,
            "ratio": rate_t / rate_st if rate_st else np.nan}


def t_rules(scored: pd.DataFrame, thr: float = 0.8) -> dict[str, np.ndarray]:
    """The 3 diagnostic T rules on the stored probabilities (first = paper default)."""
    P = scored[[f"p_{k}" for k in MODELS]].to_numpy()
    return {
        f"any>{thr:g} (paper, default)": (P > thr).any(axis=1),
        "any>0.9": (P > 0.9).any(axis=1),
        f"2of3>{thr:g}": (P > thr).sum(axis=1) >= 2,
    }


def evaluate_rule(X, feats, in_T, seeds, authors, corpus_vocab, min_t: int, top_pct: float) -> dict:
    """Re-run 2.4 + 2.5 + 2.6 metrics for one T mask (used by the sensitivity table)."""
    ranked, info = rank_from_matrix(X, feats, in_T, min_t, top_pct, exclude=seeds)
    C = build_dictionary(ranked, seeds)
    disc = ranked_discovered(ranked, seeds)["bigram"].tolist()
    p = precision_at_k(disc, authors)
    rr = reachable_recall(authors, corpus_vocab, feats, C, seeds)
    tq = t_quality(X, feats, in_T, set(authors) - set(seeds))
    return {"T": info["N_T"], "T_quality_ratio": tq["ratio"], "C": len(C),
            "n_t_only": info["n_t_only"], "n_top_pct": info["n_top_pct"],
            "precision@100": p[100], "precision@500": p[500], "reachable_recall": rr["recall"]}


def r_vocab(R: pd.DataFrame) -> set[str]:
    if R.empty:
        return set()
    try:
        return set(make_vectorizer().fit(R["sentence"].tolist()).get_feature_names_out())
    except ValueError:
        return set()


def run_eval(cfg: dict, authors: frozenset[str], C: set[str], ranked: pd.DataFrame) -> pd.DataFrame:
    """Task 2.6 report + sensitivity diagnostic -> outputs/discovery_sensitivity.csv."""
    d = discovery_dir(cfg)
    S = pd.read_parquet(d / "S.parquet")
    R = pd.read_parquet(d / "R.parquet")
    scored = pd.read_parquet(d / "S_scored.parquet")
    seeds = load_seeds(cfg)
    min_t, top_pct = rank_params(cfg)
    X, feats = load_s_bigrams(cfg, S)
    corpus_vocab = set(feats) | r_vocab(R)
    in_T = scored["in_T"].to_numpy()

    disc = ranked_discovered(ranked, seeds)
    disc["in_authors"] = disc["bigram"].isin(authors)
    p = precision_at_k(disc["bigram"].tolist(), authors)
    rr = reachable_recall(authors, corpus_vocab, feats, C, seeds)
    tq = t_quality(X, feats, in_T, set(authors) - set(seeds))

    print(f"\n[discover_eval] task 2.6: C_discovered ({len(C):,}) vs authors' cc dictionary ({len(authors):,})")
    print(f"[discover_eval] overlap |C ∩ authors| = {len(C & authors):,}  "
          f"(seeds in authors: {len(set(seeds) & authors)}/{len(seeds)})")
    print("[discover_eval] precision@k (discovered, seeds excluded, by king_score): " + "  ".join(
        f"@{k}={v:.3f}" for k, v in p.items()) + f"   [all = {len(disc):,} bigrams]")
    print(f"[discover_eval] reachable recall: {rr['n_reachable']:,} of {rr['n_authors']:,} authors' bigrams occur "
          f"in our corpus; we found {rr['n_found']:,} -> recall {rr['recall']:.3f} "
          f"(seeds excluded {rr['recall_ex_seeds']:.3f}; among the {rr['n_reachable_S']:,} that occur in S: "
          f"{rr['recall_S']:.3f})")
    print(f"[discover_eval] T quality: {tq['rate_T']:.2%} of T vs {tq['rate_ST']:.2%} of S\\T sentences "
          f"contain >= 1 authors' bigram (seeds excluded) -> ratio {tq['ratio']:.2f}")

    fmt = {"king_score": "{:.1f}".format}
    show = disc.assign(in_authors=disc["in_authors"].map({True: "Y", False: "N"}))
    cols = ["bigram", "source", "n_kT", "n_kST", "king_score", "in_authors"]
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print("\n[discover_eval] top 50 discovered bigrams:")
        print(show[cols].head(50).rename_axis("rank").rename(index=lambda i: i + 1)
              .to_string(formatters=fmt))
        print("\n[discover_eval] 20 highest-ranked discovered bigrams NOT in the authors' list:")
        print(show.loc[~disc["in_authors"], cols].head(20).rename(index=lambda i: i + 1)
              .rename_axis("rank").to_string(formatters=fmt))

    print("\n[discover_eval] DIAGNOSTIC (defaults unchanged): T-rule sensitivity on stored probabilities")
    rows = []
    for name, mask in t_rules(scored, float(cfg["discovery"]["t_threshold"])).items():
        rows.append({"rule": name, **evaluate_rule(X, feats, mask, seeds, authors, corpus_vocab,
                                                   min_t, top_pct)})
    sens = pd.DataFrame(rows)
    out = Path(cfg["paths"]["outputs"]) / "discovery_sensitivity.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    sens.to_csv(out, index=False)
    with pd.option_context("display.width", 200):
        print(sens.to_string(index=False, formatters={
            "T": "{:,}".format, "C": "{:,}".format, "T_quality_ratio": "{:.2f}".format,
            "precision@100": "{:.3f}".format, "precision@500": "{:.3f}".format,
            "reachable_recall": "{:.3f}".format}))
    print(f"[discover_eval] -> {out}")
    return sens
