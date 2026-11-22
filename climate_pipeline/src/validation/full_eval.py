"""Full-corpus discovery evaluation (stage `discover_variants_full`). No classifier is re-run.

The 200-transcript evaluation (outputs/discovery_variants.csv, presentation/bootstrap_gains.csv)
is repeated on ALL transcripts of cache/discovery/sentences_full.parquet with the CACHED
variant dictionaries (cache/discovery/variants/<v>_C.pkl), the 50 seeds (S0) and the authors'
cc dictionary. Firm-year cc_expo = mean of quarterly transcript cc_expo by (ticker, isin, year),
as outputs/scores_firmyear_full.csv, matched to official cc_expo_ew on (isin, year).

Scoring is Eq. 1 from ONE transcript x bigram count matrix (cached in cache/discovery/
transcript_bigrams_full.*): the shared vectorizer (src.preprocess.make_vectorizer) is fitted on
all sentences, so bigrams never cross sentences and every per-transcript count equals what
src.scoring.score_transcript gives (it is checked against cache/scores_transcript_full.parquet).

Outputs:
  outputs/discovery_variants_full.csv          one row per variant: |C|, n_discovered, mean
                                               cc_expo, Pearson / Spearman vs official, gains vs S0
  outputs/presentation/bootstrap_gains_full.csv  Spearman + Pearson with 95% CIs (1,000 paired
                                               resamples of firm-years) and gains vs S0 with CIs
  outputs/presentation/fig2_seeds_vs_discovery_full.png
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

FULL_VARIANTS = ["S0", "A", "B", "B2", "C2", "D2", "authors"]
KEYS = ["ticker", "isin", "year"]


# ---- transcript x bigram matrix -----------------------------------------------------------

def transcript_matrix(sents: pd.DataFrame):
    """(X, feats, meta): CSR transcript x bigram counts, bigram names, and one meta row per
    transcript (file, ticker, year, quarter, B) in X row order (files sorted)."""
    from src.preprocess import make_vectorizer

    sents = sents.sort_values(["file", "sentence_id"], kind="stable")
    vec = make_vectorizer()
    Xs = vec.fit_transform(sents["sentence"].tolist()).tocsr()
    files, row = np.unique(sents["file"].to_numpy(), return_inverse=True)
    agg = sp.csr_matrix((np.ones(len(row), dtype=np.int64), (row, np.arange(len(row)))),
                        shape=(len(files), len(row)))
    X = (agg @ Xs).tocsr()
    meta = (sents.drop_duplicates("file").set_index("file").loc[files, ["ticker", "year", "quarter"]]
            .reset_index())
    meta["B"] = np.asarray(X.sum(axis=1)).ravel()
    return X, np.asarray(vec.get_feature_names_out(), dtype=object), meta


def load_transcript_matrix(cfg: dict, load_sents, force: bool = False):
    """transcript_matrix() of the full corpus, cached in cache/discovery/transcript_bigrams_full.*"""
    d = Path(cfg["paths"]["cache"]) / "discovery"
    pX, pf, pm = (d / "transcript_bigrams_full.npz", d / "transcript_bigrams_full_vocab.parquet",
                  d / "transcript_bigrams_full_meta.parquet")
    if not force and pX.exists() and pf.exists() and pm.exists():
        return sp.load_npz(pX).tocsr(), pd.read_parquet(pf)["bigram"].to_numpy(dtype=object), pd.read_parquet(pm)
    sents = load_sents()
    print(f"[full_eval] building transcript x bigram matrix ({sents['file'].nunique():,} transcripts, "
          f"{len(sents):,} sentences) ...")
    X, feats, meta = transcript_matrix(sents)
    sp.save_npz(pX, X)
    pd.DataFrame({"bigram": feats}).to_parquet(pf, index=False)
    meta.to_parquet(pm, index=False)
    print(f"[full_eval] {X.shape[0]:,} x {X.shape[1]:,} -> {pX.name}")
    return X, feats, meta


def dict_hits(X, feats, dictionary) -> np.ndarray:
    """Climate-bigram hits per transcript (row) for a dictionary (bigrams absent from feats count 0)."""
    D = set(dictionary)
    cols = np.array([j for j, f in enumerate(feats) if f in D], dtype=np.int64)
    if not len(cols):
        return np.zeros(X.shape[0], dtype=np.int64)
    return np.asarray(X[:, cols].sum(axis=1)).ravel().astype(np.int64)


def cc_expo(hits: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Eq. 1 per transcript: hits / B (NaN when B = 0, as src.scoring)."""
    B = np.asarray(B, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(B > 0, hits / np.where(B > 0, B, 1), np.nan)


def to_firm_year(meta: pd.DataFrame, cols: dict[str, np.ndarray], isin_map: dict) -> pd.DataFrame:
    """Firm-year mean of transcript-level columns by (ticker, isin, year)."""
    t = meta[["ticker", "year"]].copy()
    t["isin"] = t["ticker"].map(lambda s: isin_map.get(str(s).upper()))
    for k, v in cols.items():
        t[k] = v
    fy = t.groupby(KEYS, dropna=False, sort=True)[list(cols)].mean().reset_index()
    fy["year"] = fy["year"].astype("Int64")
    return fy


def match_official(fy: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    off = official[["isin", "year", "cc_expo_ew"]].drop_duplicates(["isin", "year"]).copy()
    off["year"] = off["year"].astype("Int64")
    return fy.merge(off, on=["isin", "year"], how="inner").dropna(subset=["cc_expo_ew"])


# ---- bootstrap ----------------------------------------------------------------------------

def _pearson_cols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    xc = x - x.mean(axis=0)
    yc = y - y.mean()
    den = np.sqrt((xc ** 2).sum(axis=0) * (yc ** 2).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        return (xc * yc[:, None]).sum(axis=0) / den


def bootstrap_corrs(df: pd.DataFrame, variants: list[str], official: str, baseline: str,
                    n_boot: int, seed: int) -> pd.DataFrame:
    """Paired firm-year bootstrap of Spearman AND Pearson vs official, gains vs baseline.

    The resample indices are drawn exactly as src.presentation.bootstrap_spearman draws them
    (same seed -> identical Spearman CIs), and both correlations use the same draws.
    """
    from src.presentation import _spearman_cols

    x = df[variants].to_numpy(dtype=float)
    y = df[official].to_numpy(dtype=float)
    fns = {"spearman": _spearman_cols, "pearson": _pearson_cols}
    point = {k: f(x, y) for k, f in fns.items()}
    rng = np.random.default_rng(seed)
    n = len(df)
    draws = {k: np.empty((n_boot, len(variants))) for k in fns}
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        for k, f in fns.items():
            draws[k][b] = f(x[idx], y[idx])
    j = variants.index(baseline)
    tab = pd.DataFrame({"variant": variants, "n": n})
    for k in fns:
        g = draws[k] - draws[k][:, [j]]
        lo, hi = np.nanpercentile(draws[k], [2.5, 97.5], axis=0)
        glo, ghi = np.nanpercentile(g, [2.5, 97.5], axis=0)
        tab[k] = point[k]
        tab[f"{k}_ci_lo"], tab[f"{k}_ci_hi"] = lo, hi
        tab[f"{k}_gain_vs_{baseline}"] = point[k] - point[k][j]
        tab[f"{k}_gain_ci_lo"], tab[f"{k}_gain_ci_hi"] = glo, ghi
        tab[f"{k}_p_gain_le_0"] = (g <= 0).mean(axis=0)
    return tab


# ---- dictionaries -------------------------------------------------------------------------

def variant_dicts(cfg: dict, variants: list[str]) -> dict[str, frozenset[str]]:
    from src.discovery.split import load_seeds
    from src.scoring import load_dictionaries

    vdir = Path(cfg["paths"]["cache"]) / "discovery" / "variants"
    out = {}
    for v in variants:
        if v == "S0":
            out[v] = frozenset(load_seeds(cfg))
        elif v == "authors":
            out[v] = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
        else:
            p = vdir / f"{v}_C.pkl"
            if not p.exists():
                raise FileNotFoundError(f"{p} missing: run --stage discover_variants first")
            with open(p, "rb") as f:
                out[v] = frozenset(pickle.load(f))
    return out


# ---- figure -------------------------------------------------------------------------------

def fig2_full(tab: pd.DataFrame, path: Path, n_boot: int) -> None:
    from src.presentation import INK, INK2, LABELS, PALETTE, _save, _style

    labels = {**LABELS, "C2": "C2\nclean + N"}
    plt = _style()
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    x = np.arange(len(tab))
    col = ["#9e9d98" if v == "S0" else INK if v == "authors" else PALETTE[0] for v in tab["variant"]]
    ax.bar(x, tab["spearman"], width=0.6, color=col, zorder=3)
    err = np.vstack([tab["spearman"] - tab["spearman_ci_lo"], tab["spearman_ci_hi"] - tab["spearman"]])
    ax.errorbar(x, tab["spearman"], yerr=err, fmt="none", ecolor=INK2, capsize=5, lw=1.3, zorder=4)
    for xi, (_, r) in zip(x, tab.iterrows()):
        ax.text(xi, r["spearman_ci_hi"] + 0.015, f"{r['spearman']:.3f}", ha="center",
                va="bottom", fontsize=10, color=INK)
    s0 = float(tab.loc[tab["variant"] == "S0", "spearman"].iloc[0])
    ax.axhline(s0, color="#9e9d98", lw=1, ls="--", zorder=2)
    ax.set_xticks(x, [labels.get(v, v) for v in tab["variant"]])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Spearman ρ with official cc_expo_ew")
    t = tab.set_index("variant")
    disc = [v for v in tab["variant"] if v not in ("S0", "authors")]
    best = max(disc, key=lambda v: t.loc[v, "spearman"])
    sig = [v for v in disc if t.loc[v, "spearman_gain_ci_lo"] > 0]
    verdict = (f"{len(sig)} of {len(disc)} discovery variants beat seeds only (CI excludes 0)"
               if sig else "no discovery variant beats seeds only with a CI excluding 0")
    ax.set_title(f"FULL CORPUS: {verdict};\nbest {best} ρ = {t.loc[best, 'spearman']:.3f} vs "
                 f"seeds {s0:.3f} vs authors {t.loc['authors', 'spearman']:.3f}")
    n = int(tab["n"].iloc[0])
    ax.text(0.0, -0.2, f"Full corpus. Bars: Spearman ρ on {n} matched firm-years (all 1,508 "
            f"transcripts). Whiskers: 95% bootstrap CI ({n_boot:,} resamples of firm-years). "
            "Dashed: S0.", transform=ax.transAxes, fontsize=9, color=INK2)
    _save(fig, path, plt)


# ---- stage --------------------------------------------------------------------------------

def run_full_eval(cfg: dict, load_sents) -> pd.DataFrame:
    from src.io_utils import load_isin_map
    from src.validation.compare_official import load_official_all

    out_dir = Path(cfg["paths"]["outputs"])
    pres = out_dir / "presentation"
    pres.mkdir(parents=True, exist_ok=True)
    pc = cfg.get("presentation", {})
    n_boot, seed = int(pc.get("n_boot", 1000)), int(pc.get("seed", cfg["settings"]["sample_seed"]))

    X, feats, meta = load_transcript_matrix(cfg, load_sents, force=cfg.get("force", False))
    _check_against_cached_scores(cfg, X, feats, meta)
    dicts = variant_dicts(cfg, FULL_VARIANTS)
    expo = {v: cc_expo(dict_hits(X, feats, d), meta["B"].to_numpy()) for v, d in dicts.items()}
    isin_map = load_isin_map(cfg)
    official = load_official_all(cfg["paths"]["official_scores"], verbose=False)
    m = match_official(to_firm_year(meta, expo, isin_map), official)
    print(f"[full_eval] {X.shape[0]:,} transcripts -> {len(m)} firm-years matched official "
          f"({m['ticker'].nunique()} firms)")

    boot = bootstrap_corrs(m, FULL_VARIANTS, "cc_expo_ew", "S0", n_boot, seed)
    sample = pd.read_csv(out_dir / "discovery_variants.csv").set_index("variant")
    # n_discovered (non-seed kept bigrams) is a property of the dictionary: copied from the sample table
    dv = pd.DataFrame({
        "variant": FULL_VARIANTS,
        "C": [len(dicts[v]) for v in FULL_VARIANTS],
        "n_discovered": [sample["n_discovered"].get(v, np.nan) for v in FULL_VARIANTS],
        "mean_cc_expo": [float(np.nanmean(expo[v])) for v in FULL_VARIANTS],
        "pearson_official": boot["pearson"], "spearman_official": boot["spearman"],
        "pearson_gain_vs_seeds": boot["pearson_gain_vs_S0"],
        "spearman_gain_vs_seeds": boot["spearman_gain_vs_S0"],
        "n_matched": len(m),
    })
    dv.insert(1, "description", [sample["description"].get(v, "") for v in FULL_VARIANTS])
    dv.to_csv(out_dir / "discovery_variants_full.csv", index=False)
    boot.insert(0, "corpus", "full")
    boot.to_csv(pres / "bootstrap_gains_full.csv", index=False)
    fig2_full(boot, pres / "fig2_seeds_vs_discovery_full.png", n_boot)
    print(f"[full_eval] -> {out_dir / 'discovery_variants_full.csv'}")
    print(f"[full_eval] -> {pres / 'bootstrap_gains_full.csv'}")
    print_side_by_side(cfg, boot)
    return boot


def _check_against_cached_scores(cfg: dict, X, feats, meta) -> None:
    """Authors' cc_expo from the matrix must equal cache/scores_transcript_full.parquet."""
    from src.scoring import load_dictionaries

    p = Path(cfg["paths"]["cache"]) / "scores_transcript_full.parquet"
    if not p.exists():
        return
    ref = pd.read_parquet(p, columns=["file", "B", "cc_expo"]).set_index("file").loc[meta["file"]]
    auth = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
    ours = cc_expo(dict_hits(X, feats, auth), meta["B"].to_numpy())
    if not (np.array_equal(ref["B"].to_numpy(), meta["B"].to_numpy())
            and np.allclose(ref["cc_expo"].to_numpy(), ours, equal_nan=True, rtol=0, atol=1e-12)):
        raise ValueError("transcript matrix scores differ from cache/scores_transcript_full.parquet")
    print(f"[full_eval] check: B and authors' cc_expo equal scores_transcript_full.parquet for all "
          f"{len(meta):,} transcripts")


def side_by_side(sample: pd.DataFrame, full: pd.DataFrame) -> pd.DataFrame:
    """Sample vs full: rho [CI] and gain vs S0 [CI] per variant (variants in the full table order)."""
    s = sample.set_index("variant")
    f = full.set_index("variant")

    def cell(t, v, a, lo, hi, sign=False):
        if v not in t.index:
            return "-"
        fmt = "{:+.3f}" if sign else "{:.3f}"
        return f"{fmt.format(t.loc[v, a])} [{fmt.format(t.loc[v, lo])}, {fmt.format(t.loc[v, hi])}]"

    rows = []
    for v in full["variant"]:
        rows.append({"variant": v,
                     "sample_rho [CI]": cell(s, v, "spearman", "spearman_ci_lo", "spearman_ci_hi"),
                     "sample_gain [CI]": cell(s, v, "gain_vs_S0", "gain_ci_lo", "gain_ci_hi", True),
                     "full_rho [CI]": cell(f, v, "spearman", "spearman_ci_lo", "spearman_ci_hi"),
                     "full_gain [CI]": cell(f, v, "spearman_gain_vs_S0", "spearman_gain_ci_lo",
                                            "spearman_gain_ci_hi", True),
                     "full_r [CI]": cell(f, v, "pearson", "pearson_ci_lo", "pearson_ci_hi"),
                     "full_r_gain [CI]": cell(f, v, "pearson_gain_vs_S0", "pearson_gain_ci_lo",
                                              "pearson_gain_ci_hi", True)})
    return pd.DataFrame(rows)


def print_side_by_side(cfg: dict, full: pd.DataFrame) -> None:
    p = Path(cfg["paths"]["outputs"]) / "presentation" / "bootstrap_gains.csv"
    if not p.exists():
        return
    sample = pd.read_csv(p)
    sample = sample[sample["firm_set"] == sample["firm_set"].iloc[0]]
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(f"\n[full_eval] Spearman vs official: 200-transcript sample (n = {int(sample['n'].iloc[0])}) "
              f"vs full corpus (n = {int(full['n'].iloc[0])}); '-' = not in the sample table")
        print(side_by_side(sample, full).to_string(index=False))
