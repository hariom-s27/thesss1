"""Task 3.1 evaluation: discovery variants side by side (stage `discover_variants`).

Variants come from config `discovery_variants` (each overrides keys of `discovery`):
  S0 seeds-only baseline: dictionary = the 50 seeds, no discovery (paper Figure 2 logic:
     discovery must beat seeds-only)
  A  prototype: M = all sentences
  B  + rough library (task 3.1, uncleaned): M = sentences with >= 1 IPCC rough bigram
  C  = B + N2 (drop candidate bigrams in N before ranking)
  D  = C + F  (drop candidates seen in T sentences of < min_firms_in_T tickers)
  B2/C2/D2 = B/C/D with the cleaned task-3.1b rough library (discovery.rough_clean: true)

For each variant: 2.2-2.3 (cached per M definition, src.discovery.pipeline), 2.4 ranking,
2.5 dictionary, 2.6 metrics, and Eq. 1 scoring of the 200-transcript sample with the
variant's C. Metrics in outputs/discovery_variants.csv:
  M, R, S, T, T_quality_ratio, C, n_t_only, n_top_pct, precision@100, precision@500,
  reachable_recall, mean_cc_expo (transcript mean on the sample), pearson / spearman vs the
  official cc_expo_ew on matched firm-years (+ a reference row for the authors' dictionary),
  M_share = |M| / corpus sentences, spearman_gain_vs_seeds = Spearman - S0 Spearman.
  reachable_recall uses ONE denominator for all variants: the authors' bigrams that occur
  anywhere in the corpus (so a smaller M cannot inflate it).
Precision vs the authors' list is a weak metric (their list holds noise too); correlation with
the official scores and the human check are the main ones.

Best variant (discovery.best_variant; auto = highest spearman_gain_vs_seeds among the
variants with >= discovery.best_min_discovered discovered bigrams, so the 100-row human-check
sheet can be filled):
  outputs/vocab_shift.csv          per discovered bigram: T sentences before / from
                                   discovery.vocab_shift_year and n_firms_T; the printed top 20
                                   keeps bigrams with >= vocab_shift_min_firms tickers (drops
                                   executive names such as "ketchum chairman")
  outputs/human_check_top100.csv   rank, bigram, source, n_kT, n_firms, 3 example T sentences
                                   (lemmatized), is_climate (empty, to fill by hand)
"""
from __future__ import annotations

import copy
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from src.discovery.build_dict import build_dictionary
from src.discovery.evaluate import precision_at_k, ranked_discovered, reachable_recall, t_quality
from src.discovery.pipeline import file_meta, get_classified
from src.discovery.rank import (FIRM_COL, candidate_exclusions, filter_params, load_s_bigrams,
                                rank_from_matrix, rank_params)
from src.discovery.split import load_seeds, uses_rough
from src.preprocess import make_vectorizer

TABLE_COLS = ["variant", "description", "M", "M_share", "R", "S", "T", "T_quality_ratio", "C",
              "n_t_only", "n_top_pct", "n_discovered", "precision@100", "precision@500",
              "reachable_recall", "mean_cc_expo", "pearson_official", "spearman_official",
              "spearman_gain_vs_seeds", "n_matched"]
SEEDS_ONLY = "S0"


# ---- pure helpers ------------------------------------------------------------------------

def variant_cfg(cfg: dict, overrides: dict) -> dict:
    """Deep copy of cfg with discovery keys overridden (paths stay shared)."""
    v = copy.deepcopy({k: val for k, val in cfg.items() if k != "paths"})
    v["paths"] = cfg["paths"]
    v["discovery"].update(overrides)
    return v


def describe(vcfg: dict) -> str:
    if vcfg["discovery"].get("seeds_only", False):
        return "seeds only (no discovery)"
    use_N, min_f = filter_params(vcfg)
    rough = "M=rough_clean" if vcfg["discovery"].get("rough_clean", False) else "M=rough"
    parts = [rough if uses_rough(vcfg) else "M=all"]
    if use_N:
        parts.append("N2")
    if min_f > 1:
        parts.append(f"F>={min_f}")
    return " + ".join(parts)


def add_seed_gain(table: pd.DataFrame, baseline: str = SEEDS_ONLY) -> pd.DataFrame:
    """spearman_gain_vs_seeds = Spearman vs official minus the seeds-only baseline's (NaN without it)."""
    t = table.copy()
    b = t.loc[t["variant"] == baseline, "spearman_official"]
    t["spearman_gain_vs_seeds"] = t["spearman_official"] - (b.iloc[0] if len(b) else np.nan)
    return t


def pick_best(table: pd.DataFrame, choice: str = "auto", min_discovered: int = 0) -> str:
    """Highest spearman_gain_vs_seeds (= highest Spearman vs official) among discovery variants
    with >= min_discovered discovered bigrams (all of them if none qualifies), or the configured
    variant. The authors' row and the seeds-only baseline are never picked."""
    if choice != "auto":
        if choice not in set(table["variant"]):
            raise ValueError(f"best_variant {choice!r} not among {list(table['variant'])}")
        return choice
    v = table[~table["variant"].isin(["authors", SEEDS_ONLY])].copy()
    if "n_discovered" in v and (v["n_discovered"] >= min_discovered).any():
        v = v[v["n_discovered"] >= min_discovered]
    key = "spearman_gain_vs_seeds" if "spearman_gain_vs_seeds" in v else "spearman_official"
    v["_s"] = v[key].fillna(v["spearman_official"])
    return str(v.sort_values("_s", ascending=False, kind="stable")["variant"].iloc[0])


def vocab_shift(X, feats, in_T, years, bigrams, split_year: int) -> tuple[pd.DataFrame, float]:
    """Per bigram: T sentences before / from split_year and the share from split_year.

    Returns (table, base share of all T sentences from split_year).
    """
    in_T = np.asarray(in_T, dtype=bool)
    years = np.asarray(years, dtype=float)
    col = {f: i for i, f in enumerate(feats)}
    bigrams = [b for b in bigrams if b in col]
    cols = np.array([col[b] for b in bigrams], dtype=np.int64)
    post = in_T & (years >= split_year)
    pre = in_T & (years < split_year)
    XT = X[:, cols] if len(cols) else X[:, :0]
    n_post = np.asarray(XT[post].sum(axis=0)).ravel()
    n_pre = np.asarray(XT[pre].sum(axis=0)).ravel()
    tot = n_pre + n_post
    base = post.sum() / max(in_T.sum(), 1)
    out = pd.DataFrame({"bigram": bigrams, f"n_T_pre{split_year}": n_pre,
                        f"n_T_{split_year}plus": n_post, "n_kT": tot})
    out[f"share_{split_year}plus"] = np.where(tot > 0, n_post / np.maximum(tot, 1), np.nan)
    out["lift_vs_base"] = out[f"share_{split_year}plus"] / base if base else np.nan
    return out, float(base)


def top_shift(shift: pd.DataFrame, split_year: int, min_nkT: int, k: int = 20,
              min_firms: int = 0) -> pd.DataFrame:
    """Bigrams most concentrated from split_year on, with >= min_nkT T sentences and (when the
    table has n_firms_T) T sentences from >= min_firms tickers."""
    sc = f"share_{split_year}plus"
    if min_firms > 1:
        shift = shift[shift[FIRM_COL] >= min_firms]
    return (shift[shift["n_kT"] >= min_nkT]
            .sort_values([sc, "n_kT", "bigram"], ascending=[False, False, True], kind="stable")
            .head(k).reset_index(drop=True))


def example_sentences(X, feats, in_T, sentences, tickers, bigrams, n: int = 3,
                      seed: int = 42, max_chars: int = 400) -> dict[str, list[str]]:
    """Up to n T sentences per bigram, from distinct tickers first, prefixed with the ticker."""
    rng = np.random.default_rng(seed)
    col = {f: i for i, f in enumerate(feats)}
    t_rows = np.flatnonzero(np.asarray(in_T, dtype=bool))
    XT = X[t_rows].tocsc()
    out = {}
    for b in bigrams:
        if b not in col:
            out[b] = []
            continue
        c = col[b]
        rows = t_rows[XT.indices[XT.indptr[c]:XT.indptr[c + 1]]]
        rows = rng.permutation(rows)
        picked, seen = [], set()
        for r in rows:                      # one per ticker first
            if tickers[r] not in seen:
                picked.append(r)
                seen.add(tickers[r])
            if len(picked) == n:
                break
        for r in rows:                      # then fill up
            if len(picked) == n:
                break
            if r not in picked:
                picked.append(r)
        out[b] = [f"[{tickers[r]}] {sentences[r][:max_chars]}" for r in picked]
    return out


def human_check_table(disc: pd.DataFrame, examples: dict[str, list[str]], k: int = 100) -> pd.DataFrame:
    top = disc.head(k).reset_index(drop=True)
    tab = pd.DataFrame({"rank": np.arange(1, len(top) + 1), "bigram": top["bigram"],
                        "source": top["source"], "n_kT": top["n_kT"],
                        "n_firms": top[FIRM_COL] if FIRM_COL in top else pd.NA})
    for j in range(3):
        tab[f"example_{j + 1}"] = [(examples.get(b, []) + [""] * 3)[j] for b in top["bigram"]]
    tab["is_climate"] = ""
    return tab


# ---- corpus-wide pieces ------------------------------------------------------------------

def corpus_vocab(cfg: dict, corpus: str, load_sents) -> set[str]:
    """All bigrams of the corpus (denominator of reachable recall), cached per corpus."""
    p = Path(cfg["paths"]["cache"]) / "discovery" / f"corpus_vocab_{corpus}.parquet"
    if p.exists() and not cfg.get("force", False):
        return set(pd.read_parquet(p)["bigram"])
    sents = load_sents()
    print(f"[variants] building corpus bigram vocabulary ({len(sents):,} sentences) ...")
    v = make_vectorizer().fit(sents["sentence"].tolist()).get_feature_names_out()
    pd.DataFrame({"bigram": v}).to_parquet(p, index=False)
    return set(v)


def _sample_scores(sample: pd.DataFrame, cc, isin_map: dict, official: pd.DataFrame):
    """(transcript mean cc_expo, Pearson, Spearman, n) of Eq. 1 with dictionary cc vs official."""
    from src.validation.compare_dicts import KEYS, _corr_row, cc_expo_by_transcript
    t = cc_expo_by_transcript(sample, frozenset(cc))
    t["isin"] = t["ticker"].map(lambda s: isin_map.get(str(s).upper()))
    fy = t.groupby(KEYS, dropna=False, sort=True)["cc_expo"].mean().reset_index()
    fy["year"] = fy["year"].astype("Int64")
    off = official[["isin", "year", "cc_expo_ew"]].drop_duplicates(["isin", "year"]).copy()
    off["year"] = off["year"].astype("Int64")
    m = fy.merge(off, on=["isin", "year"], how="inner")
    r = _corr_row("x", m["cc_expo"], m["cc_expo_ew"])
    return float(t["cc_expo"].mean()), r["pearson"], r["spearman"], int(r["n"])


# ---- stage -------------------------------------------------------------------------------

def run_variants(cfg: dict, corpus: str, load_sents, load_sample) -> pd.DataFrame:
    from src.discovery.rough_library import load_rough_library
    from src.io_utils import load_isin_map
    from src.scoring import load_dictionaries
    from src.validation.compare_official import load_official_all

    variants = cfg["discovery_variants"]
    seeds = load_seeds(cfg)
    min_t, top_pct = rank_params(cfg)
    dv = cfg["discovery"]
    seed = int(cfg["settings"]["sample_seed"])
    out_dir = Path(cfg["paths"]["outputs"])
    out_dir.mkdir(parents=True, exist_ok=True)
    vdir = Path(cfg["paths"]["cache"]) / "discovery" / "variants"
    vdir.mkdir(parents=True, exist_ok=True)

    # lazy, memoised corpus sentences (only needed when a classifier must run / vocab is new)
    memo: dict = {}

    def sents():
        if "s" not in memo:
            memo["s"] = load_sents()
        return memo["s"]

    roughs: dict = {}

    def rough_for(vcfg):
        """The rough library a variant uses (task 3.1 or cleaned 3.1b), built once each."""
        k = bool(vcfg["discovery"].get("rough_clean", False))
        if k not in roughs:
            roughs[k] = load_rough_library(vcfg)
        return roughs[k]

    authors = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
    vocab = corpus_vocab(cfg, corpus, sents)
    meta = file_meta(cfg)
    sample = load_sample()
    isin_map = load_isin_map(cfg)
    official = load_official_all(cfg["paths"]["official_scores"], verbose=False)
    n_corpus = len(sents())
    print(f"[variants] corpus = {corpus} ({n_corpus:,} sentences); scoring sample = "
          f"{sample['file'].nunique()} transcripts; variants: {', '.join(variants)}")

    rows, kept = [], {}
    for name, over in variants.items():
        vcfg = variant_cfg(cfg, over)
        print(f"\n[variants] ===== variant {name}: {describe(vcfg)} =====")
        if vcfg["discovery"].get("seeds_only", False):
            mean_cc, pr, sp, n = _sample_scores(sample, seeds, isin_map, official)
            rows.append({"variant": name, "description": describe(vcfg), "C": len(seeds),
                         "n_discovered": 0, "mean_cc_expo": mean_cc, "pearson_official": pr,
                         "spearman_official": sp, "n_matched": n})
            print(f"[variants] {name}: |C| = {len(seeds)} seeds  r(official) = {pr:.3f} / rho = {sp:.3f}")
            continue
        rough = rough_for(vcfg) if (uses_rough(vcfg) or filter_params(vcfg)[0]) else None
        R, S, scored = get_classified(vcfg, corpus, sents, rough if uses_rough(vcfg) else None)
        in_T = scored["in_T"].to_numpy()
        X, feats = load_s_bigrams(vcfg, S)
        tickers = S["file"].map(meta["ticker"]).to_numpy(dtype=object)
        use_N, min_f = filter_params(vcfg)
        ranked, info = rank_from_matrix(X, feats, in_T, min_t, top_pct,
                                        exclude=candidate_exclusions(seeds, rough["N"] if rough else None,
                                                                     use_N),
                                        tickers=tickers, min_firms=min_f)
        C = build_dictionary(ranked, seeds)
        disc = ranked_discovered(ranked, seeds)
        p = precision_at_k(disc["bigram"].tolist(), authors)
        rr = reachable_recall(authors, vocab, feats, C, seeds)
        tq = t_quality(X, feats, in_T, set(authors) - set(seeds))
        mean_cc, pr, sp, n = _sample_scores(sample, C, isin_map, official)
        ranked.to_parquet(vdir / f"{name}_ranked.parquet", index=False)
        with open(vdir / f"{name}_C.pkl", "wb") as f:
            pickle.dump(C, f)
        rows.append({"variant": name, "description": describe(vcfg), "M": len(R) + len(S),
                     "M_share": (len(R) + len(S)) / max(n_corpus, 1), "R": len(R), "S": len(S), "T": info["N_T"], "T_quality_ratio": tq["ratio"],
                     "C": len(C), "n_t_only": info["n_t_only"], "n_top_pct": info["n_top_pct"],
                     "n_discovered": len(disc), "precision@100": p[100], "precision@500": p[500],
                     "reachable_recall": rr["recall"], "mean_cc_expo": mean_cc,
                     "pearson_official": pr, "spearman_official": sp, "n_matched": n})
        kept[name] = (S, scored, X, feats, tickers, disc)
        print(f"[variants] {name}: |M| = {len(R) + len(S):,}  |R| = {len(R):,}  |T| = {info['N_T']:,}  "
              f"|C| = {len(C):,} (t_only {info['n_t_only']:,} + top_pct {info['n_top_pct']:,} + seeds)  "
              f"r(official) = {pr:.3f} / rho = {sp:.3f}")

    mean_cc, pr, sp, n = _sample_scores(sample, authors, isin_map, official)
    rows.append({"variant": "authors", "description": "authors' cc dictionary (reference)",
                 "C": len(authors), "mean_cc_expo": mean_cc, "pearson_official": pr,
                 "spearman_official": sp, "n_matched": n})
    table = add_seed_gain(pd.DataFrame(rows).reindex(columns=TABLE_COLS))[TABLE_COLS]
    table.to_csv(out_dir / "discovery_variants.csv", index=False)

    fmt = {c: "{:,.0f}".format for c in ("M", "R", "S", "T", "C", "n_t_only", "n_top_pct", "n_discovered")}
    fmt.update({c: "{:.3f}".format for c in ("T_quality_ratio", "precision@100", "precision@500",
                                             "reachable_recall", "pearson_official", "spearman_official")})
    fmt["spearman_gain_vs_seeds"] = "{:+.3f}".format
    fmt["M_share"] = "{:.1%}".format
    fmt["mean_cc_expo"] = "{:.5f}".format
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print("\n[variants] variant comparison:")
        print(table.to_string(index=False, na_rep="-", formatters=fmt))
    print(f"[variants] -> {out_dir / 'discovery_variants.csv'}")

    for name, (*_, disc) in kept.items():
        if disc.empty:
            continue
        print(f"\n[variants] top 15 discovered bigrams, variant {name}:")
        cols = ["bigram", "source", "n_kT", "n_kST", FIRM_COL]
        print(disc[cols].head(15).rename(index=lambda i: i + 1).rename_axis("rank")
              .to_string(formatters={"bigram": "{:<28s}".format}))

    choice, min_disc = str(dv.get("best_variant", "auto")), int(dv.get("best_min_discovered", 100))
    best = pick_best(table, choice, min_disc)
    raw = pick_best(table, choice, 0)
    S, scored, X, feats, tickers, disc = kept[best]
    in_T = scored["in_T"].to_numpy()
    print(f"\n[variants] best variant = {best} (discovery.best_variant = {choice}"
          + (f"; auto = highest spearman_gain_vs_seeds among variants with >= {min_disc} discovered "
             f"bigrams; without that floor it would be {raw})" if choice == "auto" else ")"))

    yr = int(dv.get("vocab_shift_year", 2021))
    years = S["file"].map(meta["year"]).astype(float).to_numpy()
    shift, base = vocab_shift(X, feats, in_T, years, disc["bigram"].tolist(), yr)
    shift = shift.merge(disc[["bigram", "source", FIRM_COL]], on="bigram", how="left")
    shift.insert(0, "variant", best)
    shift.to_csv(out_dir / "vocab_shift.csv", index=False)
    min_n = int(dv.get("vocab_shift_min_nkT", 10))
    min_fs = int(dv.get("vocab_shift_min_firms", 3))
    top = top_shift(shift, yr, min_n, min_firms=min_fs).drop(columns="variant")
    sc = f"share_{yr}plus"
    ok = (shift["n_kT"] >= min_n) & (shift[FIRM_COL] >= min_fs)
    print(f"[variants] vocabulary shift (variant {best}): {base:.1%} of all T sentences are from {yr}+; "
          f"{int(ok.sum()):,} discovered bigrams have >= {min_n} T sentences from >= {min_fs} firms; "
          f"{int((shift.loc[ok, sc] == 1).sum()):,} of them occur ONLY from {yr}")
    print(f"[variants] 20 discovered bigrams most concentrated in {yr}+ "
          f"(n_kT >= {min_n}, >= {min_fs} firms):")
    print(top.rename(index=lambda i: i + 1).to_string(formatters={sc: "{:.1%}".format,
                                                                  "lift_vs_base": "{:.2f}".format}))
    print(f"[variants] -> {out_dir / 'vocab_shift.csv'}")

    ex = example_sentences(X, feats, in_T, S["sentence"].tolist(), tickers,
                           disc["bigram"].head(100).tolist(), seed=seed)
    hc = human_check_table(disc, ex)
    hc.insert(0, "variant", best)
    hc.to_csv(out_dir / "human_check_top100.csv", index=False, encoding="utf-8-sig")
    print(f"[variants] human-check sheet ({len(hc)} rows, fill is_climate) -> "
          f"{out_dir / 'human_check_top100.csv'}")
    return table
