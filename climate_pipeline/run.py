"""Single entry point for the climate-exposure pipeline.

Usage:
    python run.py --stage <preprocess|score|check_xom|compare_official|isin_gap|rough|discover|discover_eval|discover_variants|discover_variants_full|drift|compare_dicts|validate|presentation|all> [--sample] [--full] [--force] [--config PATH]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

PIPELINE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PIPELINE_DIR / "config.yaml"
VALID_DICTIONARIES = ("authors", "discovered")


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    """Load config.yaml, resolve relative paths against its folder, and validate settings."""
    path = Path(path).resolve()
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    base = path.parent
    cfg["paths"] = {
        key: (Path(val) if Path(val).is_absolute() else base / val)
        for key, val in cfg["paths"].items()
    }

    dictionary = cfg["settings"]["dictionary"]
    if dictionary not in VALID_DICTIONARIES:
        raise ValueError(f"settings.dictionary must be one of {VALID_DICTIONARIES}, got {dictionary!r}")
    return cfg


# ---- stages (stubs for now) -------------------------------------------------

def stage_preprocess(cfg: dict) -> None:
    """list .txt -> sample -> read -> cache/transcripts.parquet -> lemmatize -> cache/sentences.parquet.

    Rebuilds when --force is given, a cache file is missing, or cache/manifest.json does not
    match the current settings (mode, sample_size, sample_seed, n_files).
    """
    import pandas as pd

    from src.io_utils import (corpus_listing, current_manifest, load_transcripts,
                              manifest_mismatch, write_manifest)
    from src.preprocess import lemmatize

    force = cfg.get("force", False)
    tdf = load_transcripts(cfg, force=force)

    out = cfg["paths"]["cache"] / "sentences.parquet"
    want = current_manifest(cfg, len(corpus_listing(cfg, verbose=False)))
    if force:
        reason = "--force"
    elif not out.exists():
        reason = f"{out.name} missing"
    else:
        reason = manifest_mismatch(cfg, want, "sentences")
    if reason is None:
        print(f"[preprocess] reusing cached {out} (manifest matches; use --force to rebuild)")
        return
    print(f"[preprocess] rebuilding sentences cache: {reason}")

    rows = []
    for i, r in enumerate(tdf.itertuples(index=False), 1):
        sents = lemmatize(r.text)
        rows.extend((r.file, r.ticker, r.year, r.quarter, j, s) for j, s in enumerate(sents))
        if i % 25 == 0 or i == len(tdf):
            print(f"[preprocess] {i}/{len(tdf)} transcripts")

    df = pd.DataFrame(rows, columns=["file", "ticker", "year", "quarter", "sentence_id", "sentence"])
    df["year"] = df["year"].astype("Int64")
    df["quarter"] = df["quarter"].astype("Int64")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    write_manifest(cfg, want, built=["transcripts", "sentences"])
    print(f"[preprocess] processed {len(tdf)} transcripts, {len(df)} sentences -> {out}")


def ensure_sentences(cfg: dict, tag: str) -> Path:
    """Return cache/sentences.parquet, running preprocess first if it is missing or stale."""
    from src.io_utils import corpus_listing, current_manifest, manifest_mismatch

    sent_path = cfg["paths"]["cache"] / "sentences.parquet"
    want = current_manifest(cfg, len(corpus_listing(cfg, verbose=False)))
    reason = (f"{sent_path.name} missing" if not sent_path.exists()
              else manifest_mismatch(cfg, want, "sentences"))
    if reason is not None:
        print(f"[{tag}] sentence cache does not match current settings ({reason}); running preprocess")
        stage_preprocess(cfg)
    return sent_path


def score_inputs(cfg: dict):
    """(sentences, transcript-cache path, firm-year csv path, all_risk_lists) for stage score.

    --sample: the 200-transcript cache (cache/sentences.parquet) -> scores_firmyear.csv.
    full:     the discovery full-corpus cache (cache/discovery/sentences_full.parquet, reused,
              never re-lemmatized when its manifest matches) -> scores_firmyear_full.csv,
              with <m>_risk_<list> for all three risk lists (risk-list sensitivity).
    """
    import pandas as pd

    if cfg["settings"]["sample_mode"]:
        sents = pd.read_parquet(ensure_sentences(cfg, "score"))
        return sents, "scores_transcript.parquet", "scores_firmyear.csv", False
    from src.discovery.corpus import load_full_sentences
    sents = load_full_sentences(cfg, force=cfg.get("force", False))
    return sents, "scores_transcript_full.parquet", "scores_firmyear_full.csv", True


def stage_score(cfg: dict) -> None:
    """Eq. (1)-(4) -> cache/scores_transcript[_full].parquet + outputs/scores_firmyear[_full].csv."""
    from src.io_utils import load_isin_map
    from src.scoring import firm_year, load_dictionaries, load_lexicons, score_sentences_df

    sents, t_name, f_name, all_risk = score_inputs(cfg)
    print(f"[score] corpus = {'sample' if cfg['settings']['sample_mode'] else 'full'}: "
          f"{sents['file'].nunique()} transcripts, {len(sents):,} sentences")
    dicts = load_dictionaries(cfg)
    lex = load_lexicons(cfg, all_risk_lists=all_risk)
    scores = score_sentences_df(sents, dicts, lex, log_every=50 if len(sents) < 2_000_000 else 100)
    isin = load_isin_map(cfg)  # read fresh so newly added ISINs are picked up
    scores.insert(2, "isin", scores["ticker"].map(lambda t: isin.get(str(t).upper())))

    out_t = cfg["paths"]["cache"] / t_name
    scores.to_parquet(out_t, index=False)
    fy = firm_year(scores)
    out_f = cfg["paths"]["outputs"] / f_name
    out_f.parent.mkdir(parents=True, exist_ok=True)
    fy.to_csv(out_f, index=False)
    print(f"[score] {len(scores)} transcripts -> {out_t}")
    print(f"[score] {len(fy)} firm-years ({fy['ticker'].nunique()} firms, "
          f"{int(fy['isin'].notna().sum())} with ISIN) -> {out_f}")


def stage_check_xom(cfg: dict) -> None:
    """Score the ExxonMobil PDFs and compare firm-year values with the official csv."""
    import pandas as pd

    from src.scoring import EXPO_COLS, check_xom

    tab = check_xom(cfg)
    rows = []
    for r in tab.itertuples(index=False):
        for c in EXPO_COLS:
            m = c.split("_")[0]
            rows.append({"year": r.year, "measure": c, "ours": getattr(r, c),
                         "official": getattr(r, f"{c}_ew"), "pct_of_official": getattr(r, f"{m}_pct")})
    long = pd.DataFrame(rows)
    with pd.option_context("display.float_format", "{:.5f}".format):
        print(f"\n[check_xom] {cfg['settings']['pdf_ticker']} ({cfg['settings']['pdf_isin']}) "
              "firm-year exposure vs official (cc/op/rg/ph_expo_ew):")
        print(long.to_string(index=False, formatters={"pct_of_official": "{:.1f}%".format}))


def stage_compare_official(cfg: dict) -> None:
    """outputs/scores_firmyear.csv vs official csv on (isin, year) -> outputs/compare_official.csv.

    --full: outputs/scores_firmyear_full.csv -> outputs/compare_official_full.csv, plus the
    risk-list sensitivity table -> outputs/risk_list_sensitivity.csv.
    """
    import pandas as pd

    from src.validation.compare_official import (GAP_MEASURE, compare_table, largest_gaps,
                                                 load_official_all, merge_official,
                                                 risk_sensitivity)

    full = cfg.get("full", False)
    ours_path = cfg["paths"]["outputs"] / ("scores_firmyear_full.csv" if full else "scores_firmyear.csv")
    if not ours_path.exists():
        raise FileNotFoundError(f"{ours_path} missing: run --stage score "
                                f"{'(without --sample)' if full else '--sample'} first")
    print(f"[compare_official] ours = {ours_path.name}")
    ours = pd.read_csv(ours_path)
    merged = merge_official(ours, load_official_all(cfg["paths"]["official_scores"]))
    print(f"[compare_official] {len(ours)} firm-years ours, {int(ours['isin'].notna().sum())} with ISIN, "
          f"{len(merged)} matched official on (isin, year), {merged['isin'].nunique()} firms")
    tab = compare_table(merged)
    out = cfg["paths"]["outputs"] / ("compare_official_full.csv" if full else "compare_official.csv")
    tab.to_csv(out, index=False)
    with pd.option_context("display.width", 200):
        print(tab.to_string(index=False, formatters={
            "pearson": "{:.3f}".format, "spearman": "{:.3f}".format, "median_ratio": "{:.3f}".format,
            "mean_ours": "{:.6f}".format, "mean_official": "{:.6f}".format}))
        print(f"\n[compare_official] 5 largest |ours - official| gaps on {GAP_MEASURE}:")
        print(largest_gaps(merged).to_string(index=False, float_format="{:.6f}".format))
    print(f"[compare_official] -> {out}")
    rs = risk_sensitivity(merged)
    if full and len(rs):
        out_rs = cfg["paths"]["outputs"] / "risk_list_sensitivity.csv"
        rs.to_csv(out_rs, index=False)
        print(f"\n[compare_official] risk-list sensitivity (ours <m>_risk_<list> vs official "
              f"<m>_risk_ew; config default = {cfg['settings'].get('risk_list')}):")
        with pd.option_context("display.width", 200):
            print(rs.to_string(index=False, formatters={
                "pearson": "{:.3f}".format, "spearman": "{:.3f}".format,
                "median_ratio": "{:.3f}".format, "mean_ours": "{:.6f}".format,
                "mean_official": "{:.6f}".format}))
        best = rs.groupby("risk_list")[["pearson", "spearman"]].mean()
        print("[compare_official] mean over the 4 measures:")
        print(best.to_string(float_format="{:.3f}".format))
        print(f"[compare_official] best fit: Pearson -> {best['pearson'].idxmax()}, "
              f"Spearman -> {best['spearman'].idxmax()}")
        print(f"[compare_official] -> {out_rs}")


def stage_isin_gap(cfg: dict) -> None:
    """Report corpus tickers missing from ticker_isin_map.json (never writes the map)."""
    from src.io_utils import isin_gap
    isin_gap(cfg)


def _corpus_loader(cfg: dict, corpus: str):
    """Callable returning the discovery corpus sentences (full cache or the 200-sample cache)."""
    import pandas as pd

    from src.discovery.corpus import load_full_sentences

    def load():
        if corpus == "full":
            return load_full_sentences(cfg, force=cfg.get("force", False))
        cfg["settings"]["sample_mode"] = True  # the sample cache is keyed on sample settings
        return pd.read_parquet(ensure_sentences(cfg, "discover"))
    return load


def _rough_if_needed(cfg: dict) -> dict | None:
    """The rough library (C_R, N, rough) when M or filter N2 needs it, else None."""
    d = cfg["discovery"]
    if not (d.get("use_rough_library", False) or d.get("filter_candidates_by_N", False)):
        return None
    from src.discovery.rough_library import load_rough_library
    return load_rough_library(cfg, n_show=0)


def stage_discover(cfg: dict) -> None:
    """Tasks 2.1 -> 2.5 (+ 3.1 switches): seeds, M, R/S split, 3 classifiers, T, King ranking, C.

    discovery.use_rough_library: false -> PROTOTYPE, M = all sentences; true -> M = sentences
    with >= 1 IPCC rough bigram (task 3.1). 2.2-2.3 are reused from the M-specific cache
    folder when it matches (src.discovery.pipeline.cached_classify). Filters N2
    (filter_candidates_by_N) and F (apply_firm_filter, min_firms_in_T) act at ranking.
    Corpus: `--sample` -> the 200-transcript scoring cache (cache/sentences.parquet);
    otherwise discovery.corpus: full -> cache/discovery/sentences_full.parquet (own manifest),
    sample -> the 200-transcript scoring cache.
    """
    import time

    from src.discovery.build_dict import run_build_dict
    from src.discovery.pipeline import discovery_corpus, file_meta, get_classified
    from src.discovery.rank import run_rank
    from src.discovery.split import load_seeds
    from src.scoring import load_dictionaries

    t0 = time.perf_counter()
    corpus = discovery_corpus(cfg)
    print(f"[discover] corpus = {corpus}")
    print(f"[discover] task 2.1: {len(load_seeds(cfg))} seeds loaded from config")
    rough = _rough_if_needed(cfg)
    R, S, scored = get_classified(cfg, corpus, _corpus_loader(cfg, corpus), rough)
    tickers = S["file"].map(file_meta(cfg)["ticker"]).to_numpy()
    ranked = run_rank(cfg, S, scored, force=cfg.get("force", False), tickers=tickers,
                      N=rough["N"] if rough else None)
    authors = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
    run_build_dict(cfg, ranked, authors)
    print(f"[discover] done in {time.perf_counter() - t0:.1f}s")


def stage_discover_eval(cfg: dict) -> None:
    """Task 2.6 (C_discovered vs authors) + T-rule sensitivity diagnostic."""
    from src.discovery.build_dict import load_c_discovered
    from src.discovery.evaluate import run_eval
    from src.discovery.rank import load_ranked
    from src.scoring import load_dictionaries

    authors = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
    run_eval(cfg, authors, load_c_discovered(cfg), load_ranked(cfg))


def stage_discover_variants(cfg: dict) -> None:
    """Task 3.1 evaluation: run 2.2-2.6 for each config discovery_variants entry (A-D) and compare.

    -> outputs/discovery_variants.csv, outputs/vocab_shift.csv, outputs/human_check_top100.csv.
    Classifiers run once per M definition (cached); scoring uses the 200-transcript sample.
    """
    import pandas as pd

    from src.discovery.pipeline import discovery_corpus
    from src.discovery.variants import run_variants

    corpus = discovery_corpus(cfg)
    scfg = {**cfg, "settings": {**cfg["settings"], "sample_mode": True}}
    run_variants(cfg, corpus, _corpus_loader(cfg, corpus),
                 lambda: pd.read_parquet(ensure_sentences(scfg, "discover_variants")))


def stage_compare_dicts(cfg: dict) -> None:
    """Task 2.7: firm-year cc_expo with C_discovered vs the authors' cc -> outputs/compare_dicts.csv."""
    import pandas as pd

    from src.io_utils import load_isin_map
    from src.scoring import load_dictionaries
    from src.validation.compare_dicts import compare_dicts
    from src.validation.compare_official import load_official_all

    sents = pd.read_parquet(ensure_sentences(cfg, "compare_dicts"))
    auth = load_dictionaries(cfg, verbose=False, which="authors")
    disc = load_dictionaries(cfg, verbose=True, which="discovered")
    official = load_official_all(cfg["paths"]["official_scores"], verbose=False)
    print(f"[compare_dicts] scoring {sents['file'].nunique()} transcripts with both cc dictionaries "
          f"(discovered {len(disc['cc']):,} vs authors {len(auth['cc']):,} bigrams)")
    fy, corr = compare_dicts(sents, disc["cc"], auth["cc"], load_isin_map(cfg), official)
    out = cfg["paths"]["outputs"] / "compare_dicts.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    corr.to_csv(out, index=False)
    fy.to_csv(cfg["paths"]["outputs"] / "compare_dicts_firmyear.csv", index=False)
    print(f"[compare_dicts] {len(fy)} firm-years, {int(fy['cc_expo_ew'].notna().sum())} matched official")
    with pd.option_context("display.width", 200):
        print(corr.to_string(index=False, formatters={
            "pearson": "{:.3f}".format, "spearman": "{:.3f}".format,
            "mean_x": "{:.6f}".format, "mean_y": "{:.6f}".format}))
    print(f"[compare_dicts] -> {out} (+ compare_dicts_firmyear.csv)")


def stage_rough(cfg: dict) -> None:
    """Task 3.1 steps 1-2: IPCC rough library C_R minus normal text N -> cache/discovery/rough_bigrams.pkl."""
    from src.discovery.rough_library import load_rough_library
    load_rough_library(cfg, force=cfg.get("force", False))


def stage_presentation(cfg: dict) -> None:
    """Figures, tables and results_summary.md from existing outputs -> outputs/presentation/."""
    from src.presentation import run_presentation
    run_presentation(cfg)


def _full_loader(cfg: dict):
    from src.discovery.corpus import load_full_sentences
    return lambda: load_full_sentences(cfg, force=False)


def stage_discover_variants_full(cfg: dict) -> None:
    """Discovery variants (cached dictionaries) scored on the FULL corpus vs official, bootstrap
    CIs -> outputs/discovery_variants_full.csv, presentation/bootstrap_gains_full.csv + fig."""
    from src.validation.full_eval import run_full_eval
    run_full_eval(cfg, _full_loader(cfg))


def stage_drift(cfg: dict) -> None:
    """Dictionary drift: authors' cc vs authors' cc + NEW_TERMS by year / period / sector
    -> outputs/new_terms.csv, outputs/dictionary_drift.csv, presentation/fig6_dictionary_drift.png."""
    from src.validation.drift import run_drift
    run_drift(cfg, _full_loader(cfg))


def stage_validate(cfg: dict) -> None:
    print("[validate] not implemented yet (Phase 4)")


STAGES = {
    "preprocess": stage_preprocess,
    "score": stage_score,
    "check_xom": stage_check_xom,
    "compare_official": stage_compare_official,
    "isin_gap": stage_isin_gap,
    "rough": stage_rough,
    "discover": stage_discover,
    "discover_eval": stage_discover_eval,
    "discover_variants": stage_discover_variants,
    "compare_dicts": stage_compare_dicts,
    "discover_variants_full": stage_discover_variants_full,
    "drift": stage_drift,
    "validate": stage_validate,
    "presentation": stage_presentation,
}
ALL_ORDER = ["preprocess", "discover", "score", "validate"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sautner et al. (2023) climate-exposure pipeline.")
    parser.add_argument("--stage", required=True, choices=[*STAGES, "all"], help="pipeline stage to run")
    parser.add_argument("--sample", action="store_true",
                        help="run on a small sample (settings.sample_size transcripts)")
    parser.add_argument("--force", action="store_true",
                        help="rebuild cache/*.parquet even if they already exist")
    parser.add_argument("--full", action="store_true",
                        help="compare_official: use the full-corpus scores (scores_firmyear_full.csv)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to config.yaml")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    cfg = load_config(args.config)
    if args.sample:
        cfg["settings"]["sample_mode"] = True
    cfg["force"] = args.force
    cfg["full"] = args.full

    s = cfg["settings"]
    print(f"sample_mode={s['sample_mode']} sample_size={s['sample_size']} "
          f"chunk_size={s['chunk_size']} dictionary={s['dictionary']}")

    for name in (ALL_ORDER if args.stage == "all" else [args.stage]):
        STAGES[name](cfg)


if __name__ == "__main__":
    main()
