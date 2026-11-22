"""Presentation pack (stage `presentation`): figures, tables and a one-page summary built
from EXISTING outputs. No classifier is re-run.

Inputs (outputs/): scores_firmyear_full.csv, compare_official_full.csv,
risk_list_sensitivity.csv, discovery_variants.csv, vocab_shift.csv, human_check_top100.csv.
The only computation beyond reading files is for fig 2: Eq. 1 is re-applied to the
200-transcript sample (cache/sentences.parquet) with the CACHED variant dictionaries
(cache/discovery/variants/<v>_C.pkl, the 50 seeds, the authors' cc) so that firm-year
Spearman correlations can be bootstrapped. The point estimates are checked against
discovery_variants.csv.

Outputs (outputs/presentation/):
  fig1_replication_scatter.png, table1_replication.csv
  fig2_seeds_vs_discovery.png,  bootstrap_gains.csv
  fig3_vocab_shift.png, fig4_industry.png, fig5_risk_lists.png
  results_summary.md
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

# ---- broad sector per ticker (21 corpus firms) ---------------------------------------------
# The brief names 7 sectors; JPM and MSFT fit none of them, so they get an 8th group.
SECTORS = {
    "D": "utilities", "DUK": "utilities", "NEE": "utilities", "SO": "utilities",
    "COP": "oil & gas", "CVX": "oil & gas", "OXY": "oil & gas", "XOM": "oil & gas",
    "F": "autos", "GM": "autos",
    "DAL": "airlines",
    "BA": "industrials", "CAT": "industrials", "HON": "industrials", "MMM": "industrials",
    "KO": "consumer", "WMT": "consumer",
    "PFE": "health", "UNH": "health",
    "JPM": "financials & tech", "MSFT": "financials & tech",
}
SECTOR_ORDER = ["utilities", "oil & gas", "autos", "airlines", "industrials", "consumer",
                "health", "financials & tech"]
# Fixed categorical order (dataviz reference palette, light mode); colour follows the sector.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SECTOR_COLOR = dict(zip(SECTOR_ORDER, PALETTE))
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

FIG2_VARIANTS = ["S0", "A", "B", "B2", "D2", "authors"]
MEASURES = ["cc", "op", "rg", "ph"]
STATS = ["expo", "pos", "neg", "sent", "risk"]


def sector_of(ticker: str) -> str:
    try:
        return SECTORS[str(ticker).upper()]
    except KeyError as e:
        raise KeyError(f"ticker {ticker!r} has no sector in src/presentation.py SECTORS") from e


# ---- pure computations ---------------------------------------------------------------------

def table1(compare: pd.DataFrame) -> pd.DataFrame:
    """compare_official_full.csv -> rows measure (cc/op/rg/ph) x stat (expo..risk)."""
    rows = []
    for m in MEASURES:
        for s in STATS:
            r = compare[compare["measure"] == f"{m}_{s}"]
            if r.empty:
                continue
            r = r.iloc[0]
            rows.append({"measure": m, "stat": s, "n": int(r["n"]), "pearson": r["pearson"],
                         "spearman": r["spearman"], "median_ratio": r["median_ratio"]})
    return pd.DataFrame(rows)


def _spearman_cols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Spearman of each column of x with y (average ranks for ties)."""
    rx = pd.DataFrame(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rx = rx - rx.mean(axis=0)
    ry = ry - ry.mean()
    den = np.sqrt((rx ** 2).sum(axis=0) * (ry ** 2).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        return (rx * ry[:, None]).sum(axis=0) / den


def bootstrap_spearman(df: pd.DataFrame, variants: list[str], official: str, baseline: str,
                       n_boot: int, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    """Paired bootstrap over rows (firm-years): Spearman of each variant vs official, and
    its gain over `baseline`, with 95% percentile CIs. Returns (table, draws[n_boot, k])."""
    x = df[variants].to_numpy(dtype=float)
    y = df[official].to_numpy(dtype=float)
    point = _spearman_cols(x, y)
    rng = np.random.default_rng(seed)
    n = len(df)
    draws = np.empty((n_boot, len(variants)))
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        draws[b] = _spearman_cols(x[idx], y[idx])
    j = variants.index(baseline)
    gains = draws - draws[:, [j]]
    lo, hi = np.nanpercentile(draws, [2.5, 97.5], axis=0)
    glo, ghi = np.nanpercentile(gains, [2.5, 97.5], axis=0)
    tab = pd.DataFrame({"variant": variants, "n": n, "spearman": point,
                        "spearman_ci_lo": lo, "spearman_ci_hi": hi,
                        "gain_vs_" + baseline: point - point[j],
                        "gain_ci_lo": glo, "gain_ci_hi": ghi,
                        "p_gain_le_0": (gains <= 0).mean(axis=0)})
    return tab, draws


def human_precision(hc: pd.DataFrame) -> pd.DataFrame | None:
    """precision@100 overall and by source, or None when is_climate is not filled in."""
    lab = pd.to_numeric(hc["is_climate"], errors="coerce")
    if lab.notna().sum() == 0:
        return None
    d = hc.assign(y=lab).dropna(subset=["y"])
    rows = [{"group": "overall", "n_labelled": len(d), "precision": d["y"].mean()}]
    for s, g in d.groupby("source"):
        rows.append({"group": s, "n_labelled": len(g), "precision": g["y"].mean()})
    return pd.DataFrame(rows)


# ---- figure helpers ------------------------------------------------------------------------

def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.labelsize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
        "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.8, "axes.axisbelow": True, "savefig.dpi": 150,
        "figure.dpi": 150, "savefig.bbox": "tight",
    })
    return plt


def _save(fig, path: Path, plt) -> None:
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"[presentation] -> {path.name}")


MARKERS = ["o", "s", "^", "D", "v"]


def fig1(merged: pd.DataFrame, r: float, rho: float, path: Path) -> None:
    """Firm-year cc_expo ours vs official; colour = sector, marker = firm within sector."""
    plt = _style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    d = merged.assign(sector=merged["ticker"].map(sector_of))
    firms = sorted(d["ticker"].unique(), key=lambda t: (SECTOR_ORDER.index(sector_of(t)), t))
    mk = {}
    for s in SECTOR_ORDER:
        for i, t in enumerate([f for f in firms if sector_of(f) == s]):
            mk[t] = MARKERS[i % len(MARKERS)]
    for ax, log in zip(axes, (False, True)):
        dd = d[(d["cc_expo"] > 0) & (d["cc_expo_ew"] > 0)] if log else d
        for t in firms:
            g = dd[dd["ticker"] == t]
            ax.scatter(g["cc_expo_ew"], g["cc_expo"], s=34, marker=mk[t],
                       color=SECTOR_COLOR[sector_of(t)], edgecolor="white", linewidth=0.6,
                       alpha=0.9, label=f"{t} ({sector_of(t)})", zorder=3)
        lim = [dd[["cc_expo", "cc_expo_ew"]].min().min(), dd[["cc_expo", "cc_expo_ew"]].max().max()]
        if log:
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"log scale ({len(dd)} firm-years with both > 0)", fontsize=11,
                         fontweight="normal", color=INK2)
        else:
            lim = [0, lim[1] * 1.03]
            ax.set_title(f"linear scale (all {len(dd)} firm-years)", fontsize=11,
                         fontweight="normal", color=INK2)
        ax.plot(lim, lim, color=INK2, lw=1.2, ls="--", zorder=2, label="45° line")
        ax.set_xlabel("official cc_expo_ew (Sautner et al. 2025 release)")
        ax.set_ylabel("our cc_expo (authors' dictionary)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, ncol=1)
    fig.suptitle(f"Our firm-year CCExposure tracks the official scores: Pearson r = {r:.3f}, "
                 f"Spearman ρ = {rho:.3f}\n({len(d)} matched firm-years, {d['ticker'].nunique()} "
                 "firms, full corpus)", fontsize=13, fontweight="bold", x=0.5, y=1.02)
    fig.tight_layout()
    _save(fig, path, plt)


LABELS = {"S0": "S0\nseeds only", "A": "A\nM = all", "B": "B\nrough lib.",
          "B2": "B2\nclean rough", "D2": "D2\nclean + N + F", "authors": "authors'\ndictionary"}


def fig2(tab: pd.DataFrame, path: Path, n_boot: int) -> None:
    plt = _style()
    fig, ax = plt.subplots(figsize=(10, 5.8))
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
    ax.set_xticks(x, [LABELS.get(v, v) for v in tab["variant"]])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Spearman ρ with official cc_expo_ew")
    n = int(tab["n"].iloc[0])
    ax.set_title("200-TRANSCRIPT SAMPLE: discovery variants barely beat seeds only;\n"
                 "the authors' full-corpus dictionary is far ahead")
    ax.text(0.0, -0.2, f"Bars: Spearman ρ on {n} matched firm-years of the 200-transcript sample. "
            f"Whiskers: 95% bootstrap CI ({n_boot:,} resamples of firm-years). Dashed: S0.",
            transform=ax.transAxes, fontsize=9, color=INK2)
    _save(fig, path, plt)


def fig3(top: pd.DataFrame, base: float, variant: str, path: Path) -> None:
    plt = _style()
    fig, ax = plt.subplots(figsize=(10, 6.5))
    t = top.iloc[::-1]
    y = np.arange(len(t))
    ax.barh(y, t["share_2021plus"] * 100, height=0.62, color=PALETTE[0], zorder=3)
    for yi, (_, r) in zip(y, t.iterrows()):
        ax.text(r["share_2021plus"] * 100 + 1, yi, f"n_kT = {int(r['n_kT'])}", va="center",
                fontsize=9, color=INK2)
    ax.axvline(base * 100, color=INK2, ls="--", lw=1.2, zorder=4)
    ax.text(base * 100 - 0.8, -0.9, f"all climate (T) sentences:\n{base:.1%} from 2021+",
            fontsize=9, color=INK2, va="top", ha="right")
    ax.set_ylim(-1.9, len(t) - 0.4)
    ax.set_yticks(y, t["bigram"])
    ax.set_xlim(0, 115)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("% of the bigram's climate-sentence (T) occurrences from 2021 on")
    ax.grid(axis="y", visible=False)
    ax.set_title("New climate vocabulary is concentrated after 2021\n"
                 f"(top 15 discovered bigrams by 2021+ share; variant {variant}, ≥ 10 T sentences "
                 "from ≥ 3 firms)", fontsize=12)
    _save(fig, path, plt)


def fig4(by_firm: pd.DataFrame, path: Path) -> None:
    plt = _style()
    fig, ax = plt.subplots(figsize=(10, 7))
    d = by_firm.sort_values("cc_expo")
    y = np.arange(len(d))
    ax.barh(y, d["cc_expo"] * 1000, height=0.66, color=[SECTOR_COLOR[s] for s in d["sector"]],
            zorder=3)
    for yi, (_, r) in zip(y, d.iterrows()):
        ax.text(r["cc_expo"] * 1000 + 0.05, yi, f"{r['cc_expo'] * 1000:.2f}", va="center",
                fontsize=9, color=INK2)
    ax.set_yticks(y, [f"{t}  ({s})" for t, s in zip(d["ticker"], d["sector"])])
    ax.set_xlabel("mean firm-year cc_expo × 1,000 (authors' dictionary, full corpus)")
    ax.grid(axis="y", visible=False)
    from matplotlib.patches import Patch
    present = [s for s in SECTOR_ORDER if s in set(d["sector"])]
    ax.legend([Patch(color=SECTOR_COLOR[s]) for s in present], present, loc="lower right",
              frameon=False, title="sector")
    top = d.iloc[-1]
    sec = d.groupby("sector")["cc_expo"].mean().sort_values(ascending=False)
    ax.set_title(f"Climate talk is a sector story: {sec.index[0]} lead, then {sec.index[1]} and "
                 f"{sec.index[2]};\n{top['ticker']} is {top['cc_expo'] / d['cc_expo'].iloc[0]:.0f}× "
                 f"the lowest firm ({d['ticker'].iloc[0]})")
    _save(fig, path, plt)


def fig5(rs: pd.DataFrame, path: Path) -> None:
    plt = _style()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    lists = ["narrow", "curated", "lm_unc"]
    ms = ["cc_risk", "op_risk", "rg_risk"]
    w = 0.26
    x = np.arange(len(ms))
    for i, l in enumerate(lists):
        v = [float(rs[(rs["measure"] == m) & (rs["risk_list"] == l)]["pearson"].iloc[0]) for m in ms]
        b = ax.bar(x + (i - 1) * (w + 0.01), v, width=w, color=PALETTE[i], label=l, zorder=3)
        for rect, val in zip(b, v):
            ax.text(rect.get_x() + rect.get_width() / 2, val + 0.012, f"{val:.2f}", ha="center",
                    fontsize=9, color=INK)
    ax.set_xticks(x, ms)
    ax.set_ylim(0, 0.8)
    ax.set_ylabel("Pearson r with official <m>_risk_ew")
    ax.legend(title="risk word list", frameon=False)
    ax.set_title("The curated risk list fits best for cc and op risk;\n"
                 "no list recovers regulatory risk (paper never publishes its list)")
    _save(fig, path, plt)


# ---- fig 2 data: rescore the sample with cached dictionaries --------------------------------

def variant_firmyears(cfg: dict, variants: list[str]) -> pd.DataFrame:
    """Firm-year cc_expo on the 200-transcript sample for each variant dictionary, merged with
    official cc_expo_ew (inner, as in src.discovery.variants._sample_scores)."""
    from src.discovery.split import load_seeds
    from src.io_utils import load_isin_map
    from src.scoring import load_dictionaries
    from src.validation.compare_dicts import KEYS, cc_expo_by_transcript
    from src.validation.compare_official import load_official_all

    sent_path = Path(cfg["paths"]["cache"]) / "sentences.parquet"
    if not sent_path.exists():
        raise FileNotFoundError(f"{sent_path} missing: run --stage preprocess --sample first")
    sample = pd.read_parquet(sent_path)
    vdir = Path(cfg["paths"]["cache"]) / "discovery" / "variants"
    isin = load_isin_map(cfg)
    fy = None
    for v in variants:
        if v == "S0":
            cc = load_seeds(cfg)
        elif v == "authors":
            cc = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
        else:
            p = vdir / f"{v}_C.pkl"
            if not p.exists():
                raise FileNotFoundError(f"{p} missing: run --stage discover_variants first")
            with open(p, "rb") as f:
                cc = pickle.load(f)
        t = cc_expo_by_transcript(sample, frozenset(cc))
        t["isin"] = t["ticker"].map(lambda s: isin.get(str(s).upper()))
        g = t.groupby(KEYS, dropna=False, sort=True)["cc_expo"].mean().rename(v).reset_index()
        fy = g if fy is None else fy.merge(g, on=KEYS, how="outer")
        print(f"[presentation] fig 2: scored sample with {v} ({len(cc):,} bigrams)")
    fy["year"] = fy["year"].astype("Int64")
    off = load_official_all(cfg["paths"]["official_scores"], verbose=False)
    off = off[["isin", "year", "cc_expo_ew"]].drop_duplicates(["isin", "year"]).copy()
    off["year"] = off["year"].astype("Int64")
    return fy.merge(off, on=["isin", "year"], how="inner").dropna(subset=["cc_expo_ew"])


# ---- summary -------------------------------------------------------------------------------

def _f(x, d=3):
    return f"{x:.{d}f}"


def write_summary(path: Path, ctx: dict) -> None:
    t1, boot, dv, rs = ctx["t1"], ctx["boot"], ctx["dv"], ctx["rs"]

    def t1v(m, s, c):
        return float(t1[(t1["measure"] == m) & (t1["stat"] == s)][c].iloc[0])

    def bv(v, c):
        return float(boot.loc[boot["variant"] == v, c].iloc[0])

    disc = [v for v in boot["variant"] if v not in ("S0", "authors")]
    best = max(disc, key=lambda v: bv(v, "spearman"))
    rs_rows = "\n".join(
        f"| {m} | " + " | ".join(_f(float(rs[(rs['measure'] == m) & (rs['risk_list'] == l)]['pearson'].iloc[0]))
                                 for l in ("narrow", "curated", "lm_unc")) + " |"
        for m in ("cc_risk", "op_risk", "rg_risk"))
    boot_rows = "\n".join(
        f"| {v} | {_f(bv(v, 'spearman'))} [{_f(bv(v, 'spearman_ci_lo'))}, {_f(bv(v, 'spearman_ci_hi'))}] "
        f"| {bv(v, 'gain_vs_S0'):+.3f} [{bv(v, 'gain_ci_lo'):+.3f}, {bv(v, 'gain_ci_hi'):+.3f}] |"
        for v in boot["variant"])
    tq = float(dv.loc[dv["variant"] == "A", "T_quality_ratio"].iloc[0])
    n_fy, n_firms = ctx["n_matched"], ctx["n_matched_firms"]
    ba = ctx["boot_all"]

    def ba_v(v, c):
        return float(ba.loc[ba["variant"] == v, c].iloc[0])

    if ba is None:
        ctx["robust"] = ""
    else:
        ctx["robust"] = (f"\nRobustness: with all {ctx['n_firms_all_isin']} firms mapped to ISINs "
                         f"({int(ba['n'].iloc[0])} sample firm-years) rho is S0 {_f(ba_v('S0','spearman'))}, "
                         f"{best} {_f(ba_v(best,'spearman'))} (gain {ba_v(best,'gain_vs_S0'):+.3f} "
                         f"[{ba_v(best,'gain_ci_lo'):+.3f}, {ba_v(best,'gain_ci_hi'):+.3f}]), authors "
                         f"{_f(ba_v('authors','spearman'))}.\n")
    sig = [v for v in disc if bv(v, "gain_ci_lo") > 0]
    if sig:
        names = ", ".join(sig)
        interp = (f"Interpretation: besides the authors' dictionary, {names} beat"
                  f"{'s' if len(sig) == 1 else ''} seeds only with a CI that excludes zero, but "
                  f"stay{'s' if len(sig) == 1 else ''} below the authors'.")
    else:
        interp = ("Interpretation: only the authors' dictionary beats seeds only with a CI that "
                  "excludes zero.")
    txt = f"""# Climate-exposure replication: results summary

Rebuild of Sautner, van Lent, Vilkov & Zhang (2023, JF) as one pipeline (seeds -> discovery
-> dictionary -> scores Eq. 1-4 -> validation). Figures and tables: this folder.

**Corpus.** {ctx['n_transcripts']:,} earnings-call transcripts, {ctx['n_firms']} US firms,
{ctx['y0']}-{ctx['y1']}; {n_fy} firm-years ({n_firms} firms) match the official scores on (ISIN, year).

**Replication (authors' dictionary, full corpus; fig 1, table 1).**
- ExxonMobil 2024 CCExposure = 0.004575, 79.6% of the official 0.00575 (mean of 4 quarterly
  PDFs; our transcript excerpts are shorter than the authors').
- Firm-year correlation with the official scores (Pearson r / Spearman rho):
  cc_expo {_f(t1v('cc','expo','pearson'))} / {_f(t1v('cc','expo','spearman'))};
  op {_f(t1v('op','expo','pearson'))} / {_f(t1v('op','expo','spearman'))};
  rg {_f(t1v('rg','expo','pearson'))} / {_f(t1v('rg','expo','spearman'))};
  ph {_f(t1v('ph','expo','pearson'))} / {_f(t1v('ph','expo','spearman'))}.
  Physical exposure is rare (few non-zero firm-years), so it is the noisiest.
- Sentiment tracks (cc_pos r = {_f(t1v('cc','pos','pearson'))}) but runs lower (median ratio
  {_f(t1v('cc','pos','median_ratio'), 2)}): the Loughran-McDonald words are not lemmatized,
  so lemmatized transcript words miss some of them.

**Risk (fig 5).** The paper never publishes its risk word list. Of three candidates the
curated list fits best (cc_risk r = {_f(t1v('cc','risk','pearson'))}); regulatory and physical
risk are not recovered by any list.

| Pearson vs official | narrow | curated | lm_unc |
|---|---|---|---|
{rs_rows}

**Discovery (fig 2; 200-transcript sample, {int(boot['n'].iloc[0])} matched firm-years, {ctx['n_fig2_firms']} firms).**
The classifiers find genuinely climate-heavy sentences (T holds {tq:.0f}x more authors'
bigrams per sentence than the rest of S), but on the sample most discovered dictionaries
barely beat the 50 seeds: seeds only rho = {_f(bv('S0','spearman'))}, authors' dictionary
{_f(bv('authors','spearman'))}, our best variant ({best}) {_f(bv(best,'spearman'))}.
Spearman rho with 95% bootstrap CIs ({ctx['n_boot']:,} resamples of firm-years) and gain vs S0:

| variant | rho [95% CI] | gain vs S0 [95% CI] |
|---|---|---|
{boot_rows}
{ctx['robust']}
{interp} Discovery needs corpus scale (the authors trained on ~60k climate
sentences from the full call universe; we have ~2k in R from {ctx['n_firms']} firms).

**Vocabulary shift (fig 3).** {ctx['base']:.1%} of climate (T) sentences are from 2021 or later.
Bigrams such as net zero, carbon capture, energy transition and scope emission are central to
recent calls but absent from the authors' pre-2021 dictionary.

**Deviations from the paper.**
- LinearSVC + probability calibration instead of kernel SVC.
- Ratio-matched training sample (S sample = 1.667 x |R|, the paper's 100k/60k ratio).
- No stemming (spaCy lemmas only).
- IPCC rough library = AR5 (SYR, WG1, WG2 Part A, WG3) + SR1.5.
- Normal text N = NLTK Gutenberg, Reuters and Brown corpora.
- Rough-library cleaning: citation lines, digit tokens and token validity filters.
- Firm filter (candidate bigram must appear in T sentences of >= 3 firms) for a 21-firm corpus.

**Data note.** HON is matched on its old ISIN US4385161066; exchanges now list US4385162056.

**Next steps.** Topic dictionaries (opportunity / regulatory / physical); validation suite
(paper Table VI); Indian MD&A text via arpipe.
"""
    path.write_text(txt, encoding="utf-8")
    print(f"[presentation] -> {path.name}")


# ---- stage ---------------------------------------------------------------------------------

def run_presentation(cfg: dict) -> dict:
    from src.discovery.variants import top_shift
    from src.validation.compare_official import load_official_all, merge_official

    out_dir = Path(cfg["paths"]["outputs"])
    pres = out_dir / "presentation"
    pres.mkdir(parents=True, exist_ok=True)
    pc = cfg.get("presentation", {})
    n_boot, seed = int(pc.get("n_boot", 1000)), int(pc.get("seed", cfg["settings"]["sample_seed"]))

    def need(name):
        p = out_dir / name
        if not p.exists():
            raise FileNotFoundError(f"{p} missing: run the stage that writes it first")
        return p

    # 1. replication
    scores = pd.read_csv(need("scores_firmyear_full.csv"))
    off = load_official_all(cfg["paths"]["official_scores"], verbose=False)
    merged = merge_official(scores, off[["isin", "year", "cc_expo_ew"]])
    merged = merged.dropna(subset=["cc_expo", "cc_expo_ew"])
    cmp_ = pd.read_csv(need("compare_official_full.csv"))
    t1 = table1(cmp_)
    t1.to_csv(pres / "table1_replication.csv", index=False)
    print(f"[presentation] -> table1_replication.csv")
    cc = cmp_[cmp_["measure"] == "cc_expo"].iloc[0]
    if len(merged) != int(cc["n"]):
        raise ValueError(f"matched firm-years {len(merged)} != compare_official_full n {int(cc['n'])}")
    fig1(merged, cc["pearson"], cc["spearman"], pres / "fig1_replication_scatter.png")

    # 2. seeds vs discovery (bootstrap)
    dv = pd.read_csv(need("discovery_variants.csv"))
    fyv_all = variant_firmyears(cfg, FIG2_VARIANTS)
    keep = {str(t).upper() for t in pc.get("fig2_tickers", [])}
    fyv = fyv_all[fyv_all["ticker"].str.upper().isin(keep)] if keep else fyv_all
    boot, _ = bootstrap_spearman(fyv, FIG2_VARIANTS, "cc_expo_ew", "S0", n_boot, seed)
    ref = dv.set_index("variant")["spearman_official"]
    for v, s in zip(boot["variant"], boot["spearman"]):
        if abs(s - ref[v]) > 1e-6:
            raise ValueError(f"variant {v}: rescored Spearman {s:.6f} != discovery_variants.csv "
                             f"{ref[v]:.6f} (check presentation.fig2_tickers)")
    print(f"[presentation] fig 2: rescored Spearman matches discovery_variants.csv for all "
          f"{len(boot)} variants (n = {len(fyv)} firm-years, {fyv['ticker'].nunique()} firms)")
    parts = [boot.assign(firm_set=f"as_discovery_variants_{fyv['ticker'].nunique()}_firms")]
    boot_all = None
    if keep:  # a pinned subset: also report all firms with an ISIN
        boot_all, _ = bootstrap_spearman(fyv_all, FIG2_VARIANTS, "cc_expo_ew", "S0", n_boot, seed)
        parts.append(boot_all.assign(firm_set=f"all_isins_{fyv_all['ticker'].nunique()}_firms"))
    both = pd.concat(parts)
    both = both[["firm_set", *boot.columns]]
    both.to_csv(pres / "bootstrap_gains.csv", index=False)
    print(f"[presentation] -> bootstrap_gains.csv")
    fig2(boot, pres / "fig2_seeds_vs_discovery.png", n_boot)

    # 3. vocabulary shift (firm-filtered)
    vs = pd.read_csv(need("vocab_shift.csv"))
    dvc = cfg["discovery"]
    top = top_shift(vs, int(dvc.get("vocab_shift_year", 2021)), int(dvc.get("vocab_shift_min_nkT", 10)),
                    k=15, min_firms=int(dvc.get("vocab_shift_min_firms", 3)))
    base = float((vs["share_2021plus"] / vs["lift_vs_base"]).dropna().iloc[0])
    fig3(top, base, str(vs["variant"].iloc[0]), pres / "fig3_vocab_shift.png")

    # 4. industry
    by_firm = scores.groupby("ticker", as_index=False)["cc_expo"].mean()
    by_firm["sector"] = by_firm["ticker"].map(sector_of)
    fig4(by_firm, pres / "fig4_industry.png")

    # 5. risk lists
    rs = pd.read_csv(need("risk_list_sensitivity.csv"))
    fig5(rs, pres / "fig5_risk_lists.png")

    # 6. human check
    hc = pd.read_csv(need("human_check_top100.csv"), encoding="utf-8-sig")
    prec = human_precision(hc)
    if prec is None:
        print("human check not filled yet")
    else:
        prec.to_csv(pres / "human_check_precision.csv", index=False)
        print(prec.to_string(index=False))

    # 7. summary
    write_summary(pres / "results_summary.md", {
        "t1": t1, "boot": boot, "boot_all": boot_all, "dv": dv, "rs": rs, "prec": prec, "base": base, "n_boot": n_boot,
        "n_transcripts": int(scores["n_transcripts"].sum()), "n_firms": scores["ticker"].nunique(),
        "y0": int(scores["year"].min()), "y1": int(scores["year"].max()),
        "n_matched": len(merged), "n_firms_all_isin": fyv_all["ticker"].nunique(),
        "n_fig2_firms": fyv["ticker"].nunique(), "n_matched_firms": merged["ticker"].nunique(),
    })
    with pd.option_context("display.width", 200):
        print("\n[presentation] bootstrap (Spearman vs official, 200-transcript sample):")
        print(both.to_string(index=False, float_format="{:.3f}".format))
    return {"boot": both, "prec": prec, "t1": t1}
