"""Dictionary drift (stage `drift`): how much climate talk the FIXED authors' dictionary misses.

NEW_TERMS = discovered bigrams of the best discovery variant (highest full-corpus Spearman gain
vs seeds among variants with >= discovery.best_min_discovered discovered bigrams, from
outputs/discovery_variants_full.csv) that
  - come from T sentences of >= discovery.vocab_shift_min_firms (3) firms (firm filter),
  - are NOT in the authors' cc dictionary,
  - occur in >= discovery.vocab_shift_min_nkT (10) T sentences.
The full corpus is scored twice with Eq. 1: (a) authors' cc, (b) authors' cc ∪ NEW_TERMS.
Since NEW_TERMS ∩ authors = ∅, union hits = authors hits + new hits per transcript, and
share_new_hits = new hits / union hits (pooled over the transcripts of a group).

This is a COVERAGE measure, not a validity claim: the official scores use the old dictionary,
so agreement with them cannot rank (a) against (b).

Outputs: outputs/new_terms.csv, outputs/dictionary_drift.csv,
outputs/presentation/fig6_dictionary_drift.png.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SPLIT_YEAR = 2021
DRIFT_SECTORS = {"utilities": "utilities", "oil & gas": "oil & gas", "autos": "autos"}


def drift_sector(ticker: str) -> str:
    from src.presentation import sector_of
    return DRIFT_SECTORS.get(sector_of(ticker), "others")


def pick_variant(dv_full: pd.DataFrame, min_discovered: int) -> str:
    """Highest full-corpus spearman_gain_vs_seeds among discovery variants with enough bigrams."""
    v = dv_full[~dv_full["variant"].isin(["S0", "authors"])]
    v = v[v["n_discovered"] >= min_discovered]
    if v.empty:
        raise ValueError(f"no variant has >= {min_discovered} discovered bigrams")
    return str(v.sort_values("spearman_gain_vs_seeds", ascending=False, kind="stable")["variant"].iloc[0])


def new_terms(disc: pd.DataFrame, authors, min_firms: int, min_nkT: int) -> pd.DataFrame:
    """Discovered bigrams passing the firm filter, not in the authors' dictionary, >= min_nkT T sentences."""
    a = set(authors)
    keep = (disc["n_firms_T"] >= min_firms) & (disc["n_kT"] >= min_nkT) & ~disc["bigram"].isin(a)
    return (disc.loc[keep, ["bigram", "source", "n_kT", "n_kST", "n_firms_T"]]
            .sort_values(["n_kT", "bigram"], ascending=[False, True], kind="stable")
            .reset_index(drop=True))


def transcript_table(meta: pd.DataFrame, hits_a: np.ndarray, hits_n: np.ndarray,
                     isin_map: dict) -> pd.DataFrame:
    """Per transcript: hits under (a) and from NEW_TERMS, cc_expo under (a) and (b)."""
    from src.validation.full_eval import cc_expo
    t = meta[["file", "ticker", "year", "quarter", "B"]].copy()
    t["isin"] = t["ticker"].map(lambda s: isin_map.get(str(s).upper()))
    t["hits_authors"] = hits_a
    t["hits_new"] = hits_n
    t["cc_expo_authors"] = cc_expo(hits_a, t["B"].to_numpy())
    t["cc_expo_union"] = cc_expo(hits_a + hits_n, t["B"].to_numpy())
    t["sector"] = t["ticker"].map(drift_sector)
    t["period"] = np.where(t["year"] >= SPLIT_YEAR, f"{SPLIT_YEAR}+", f"pre-{SPLIT_YEAR}")
    return t


def drift_table(t: pd.DataFrame) -> pd.DataFrame:
    """Rows by year, period, sector and sector x period.

    mean_cc_expo_* = mean of FIRM-YEAR cc_expo (mean of quarters, as scores_firmyear_full.csv)
    over the firm-years of the group; share_new_hits = sum hits_new / sum (hits_authors + hits_new).
    """
    fy = (t.groupby(["ticker", "isin", "year"], dropna=False)
          .agg(cc_expo_authors=("cc_expo_authors", "mean"), cc_expo_union=("cc_expo_union", "mean"),
               hits_authors=("hits_authors", "sum"), hits_new=("hits_new", "sum"),
               n_transcripts=("file", "size"))
          .reset_index())
    fy["sector"] = fy["ticker"].map(drift_sector)
    fy["period"] = np.where(fy["year"] >= SPLIT_YEAR, f"{SPLIT_YEAR}+", f"pre-{SPLIT_YEAR}")
    fy["sector_period"] = fy["sector"] + " | " + fy["period"]

    def agg(by: str, kind: str) -> pd.DataFrame:
        g = fy.groupby(by, sort=True).agg(
            n_transcripts=("n_transcripts", "sum"), n_firm_years=("ticker", "size"),
            mean_cc_expo_authors=("cc_expo_authors", "mean"), mean_cc_expo_union=("cc_expo_union", "mean"),
            hits_authors=("hits_authors", "sum"), hits_new=("hits_new", "sum")).reset_index()
        g = g.rename(columns={by: "group"})
        g["group"] = g["group"].astype(str)
        g.insert(0, "breakdown", kind)
        return g

    out = pd.concat([agg("year", "year"), agg("period", "period"), agg("sector", "sector"),
                     agg("sector_period", "sector x period")], ignore_index=True)
    tot = out["hits_authors"] + out["hits_new"]
    out["share_new_hits"] = np.where(tot > 0, out["hits_new"] / tot.where(tot > 0, 1), np.nan)
    out["pct_increase_mean_expo"] = 100 * (out["mean_cc_expo_union"] / out["mean_cc_expo_authors"] - 1)
    return out


def drift_title(pre: float, post: float, n_terms: int, variant: str, tol_pp: float = 5.0) -> str:
    """Figure title stating the finding: a level gap (shares within tol_pp points) or a drift."""
    diff = 100 * (post - pre)
    if abs(diff) < tol_pp:
        head = (f"The fixed dictionary misses a large, roughly STABLE share of climate talk: "
                f"new terms add {pre:.0%} of hits before {SPLIT_YEAR}")
    else:
        head = (f"The fixed dictionary misses a {'growing' if diff > 0 else 'shrinking'} share of "
                f"climate talk: new terms add {pre:.0%} of hits before {SPLIT_YEAR}")
    return (f"{head}\nand {post:.0%} from {SPLIT_YEAR} on (full corpus, {n_terms} new terms "
            f"from variant {variant})")


def fig6(by_year: pd.DataFrame, pre: float, post: float, variant: str, n_terms: int,
         path: Path, min_n: int = 20) -> None:
    from src.presentation import INK, INK2, PALETTE, _save, _style

    plt = _style()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True,
                                 gridspec_kw={"height_ratios": [1.15, 1]})
    d = by_year.copy()
    d["year"] = d["group"].astype(int)
    thin = d["n_transcripts"] < min_n
    for ax in (a1, a2):
        for y in d.loc[thin, "year"]:
            ax.axvspan(y - 0.5, y + 0.5, color="#f1f0ec", zorder=0)
        ax.axvline(SPLIT_YEAR - 0.5, color=INK2, lw=1, ls=":", zorder=1)
    a1.plot(d["year"], d["mean_cc_expo_authors"] * 1000, marker="o", color=INK, lw=2,
            label="(a) authors' cc dictionary", zorder=3)
    a1.plot(d["year"], d["mean_cc_expo_union"] * 1000, marker="o", color=PALETTE[0], lw=2,
            label=f"(b) authors' cc ∪ {n_terms} new terms", zorder=3)
    a1.fill_between(d["year"], d["mean_cc_expo_authors"] * 1000, d["mean_cc_expo_union"] * 1000,
                    color=PALETTE[0], alpha=0.15, zorder=2)
    a1.set_ylabel("mean firm-year cc_expo × 1,000")
    a1.legend(frameon=False, loc="upper left")
    a2.bar(d["year"], d["share_new_hits"] * 100, width=0.7, color=PALETTE[0], zorder=3)
    for _, r in d.iterrows():
        a2.text(r["year"], r["share_new_hits"] * 100 + 0.4, f"{r['share_new_hits'] * 100:.0f}",
                ha="center", fontsize=8, color=INK2)
    a2.set_ylabel("% of climate hits from\nnew terms only")
    a2.set_xticks(d["year"], [str(y) for y in d["year"]], rotation=45)
    a2.set_xlim(d["year"].min() - 0.6, d["year"].max() + 0.6)
    fig.suptitle(drift_title(pre, post, n_terms, variant), fontsize=13, fontweight="bold", y=0.995)
    fig.text(0.01, -0.01, f"Shaded years: < {min_n} transcripts. Dotted line: {SPLIT_YEAR}. "
             "Share = new-term hits / all climate hits (pooled over the year's transcripts). "
             "Coverage, not accuracy: the official scores use the old dictionary.",
             fontsize=9, color=INK2)
    fig.tight_layout()
    _save(fig, path, plt)


def run_drift(cfg: dict, load_sents) -> pd.DataFrame:
    from src.discovery.evaluate import ranked_discovered
    from src.discovery.split import load_seeds
    from src.io_utils import load_isin_map
    from src.scoring import load_dictionaries
    from src.validation.full_eval import dict_hits, load_transcript_matrix

    out_dir = Path(cfg["paths"]["outputs"])
    dvc = cfg["discovery"]
    p = out_dir / "discovery_variants_full.csv"
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run --stage discover_variants_full first")
    variant = pick_variant(pd.read_csv(p), int(dvc.get("best_min_discovered", 100)))
    ranked = pd.read_parquet(Path(cfg["paths"]["cache"]) / "discovery" / "variants" / f"{variant}_ranked.parquet")
    disc = ranked_discovered(ranked, load_seeds(cfg))
    authors = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
    min_f, min_n = int(dvc.get("vocab_shift_min_firms", 3)), int(dvc.get("vocab_shift_min_nkT", 10))
    nt = new_terms(disc, authors, min_f, min_n)
    nt.insert(0, "variant", variant)
    print(f"[drift] variant {variant}: {len(disc):,} discovered -> {int((disc['n_firms_T'] >= min_f).sum()):,} "
          f"from >= {min_f} firms -> NEW_TERMS = {len(nt)} (not in authors' cc, >= {min_n} T sentences)")

    X, feats, meta = load_transcript_matrix(cfg, load_sents)
    hits_a = dict_hits(X, feats, authors)
    hits_n = dict_hits(X, feats, set(nt["bigram"]))
    t = transcript_table(meta, hits_a, hits_n, load_isin_map(cfg))
    # corpus-wide hits per new term
    col = {f: j for j, f in enumerate(feats)}
    nt["corpus_hits"] = [int(X[:, col[b]].sum()) if b in col else 0 for b in nt["bigram"]]
    nt.to_csv(out_dir / "new_terms.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 500):
        print(nt.drop(columns="variant").rename(index=lambda i: i + 1).to_string())
    print(f"[drift] -> {out_dir / 'new_terms.csv'}")

    tab = drift_table(t)
    tab.insert(0, "variant", variant)
    tab.to_csv(out_dir / "dictionary_drift.csv", index=False)
    fmt = {"mean_cc_expo_authors": "{:.6f}".format, "mean_cc_expo_union": "{:.6f}".format,
           "share_new_hits": "{:.1%}".format, "pct_increase_mean_expo": "{:+.1f}%".format}
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(tab.drop(columns="variant").to_string(index=False, formatters=fmt))
    print(f"[drift] -> {out_dir / 'dictionary_drift.csv'}")
    per = tab[tab["breakdown"] == "period"].set_index("group")["share_new_hits"]
    fig6(tab[tab["breakdown"] == "year"], float(per[f"pre-{SPLIT_YEAR}"]), float(per[f"{SPLIT_YEAR}+"]),
         variant, len(nt), out_dir / "presentation" / "fig6_dictionary_drift.png")
    para = drift_paragraph(tab, nt)
    print(para)
    update_summary(out_dir / "presentation" / "results_summary.md", para)
    return tab


# ---- results_summary.md paragraph --------------------------------------------------------

SUMMARY_HEAD = "**Dictionary drift (fig 6).**"


def drift_paragraph(tab: pd.DataFrame, nt: pd.DataFrame) -> str:
    """3-4 sentences for results_summary.md, all numbers from dictionary_drift.csv / new_terms.csv."""
    per = tab[tab["breakdown"] == "period"].set_index("group")
    sec = tab[tab["breakdown"] == "sector"].set_index("group")
    pre, post = per.loc[f"pre-{SPLIT_YEAR}"], per.loc[f"{SPLIT_YEAR}+"]
    top = ", ".join(nt.sort_values("corpus_hits", ascending=False)["bigram"].head(4))
    return (
        f"{SUMMARY_HEAD} {len(nt)} discovered bigrams (variant {nt['variant'].iloc[0]}, >= 3 firms, "
        f">= 10 T sentences) are not in the authors' cc dictionary. Adding them to it, new terms "
        f"supply {pre['share_new_hits']:.1%} of climate bigram hits before {SPLIT_YEAR} and "
        f"{post['share_new_hits']:.1%} from {SPLIT_YEAR} on, raising mean firm-year cc_expo by "
        f"{pre['pct_increase_mean_expo']:.0f}% and {post['pct_increase_mean_expo']:.0f}%; the gap is "
        f"mostly a stable level from 2013 on, not a post-{SPLIT_YEAR} jump. By sector the share is "
        f"{sec.loc['oil & gas', 'share_new_hits']:.0%} in oil & gas, "
        f"{sec.loc['utilities', 'share_new_hits']:.0%} in utilities and "
        f"{sec.loc['autos', 'share_new_hits']:.0%} in autos. This is coverage the fixed dictionary "
        f"misses, not a better score (the official scores use the old dictionary), and an upper "
        f"bound: the list still holds generic terms (most hits: {top}) pending a human check.\n")


def update_summary(path: Path, para: str) -> None:
    """Replace the drift paragraph in results_summary.md, or insert it before 'Deviations'."""
    if not path.exists():
        return
    txt = path.read_text(encoding="utf-8")
    lines = txt.split("\n\n")
    lines = [b for b in lines if not b.startswith(SUMMARY_HEAD)]
    idx = next((i for i, b in enumerate(lines) if b.startswith("**Deviations")), len(lines))
    lines.insert(idx, para.rstrip("\n"))
    path.write_text("\n\n".join(lines), encoding="utf-8")
    print(f"[drift] drift paragraph -> {path.name}")
