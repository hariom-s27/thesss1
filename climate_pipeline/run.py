"""Single entry point for the climate-exposure pipeline.

Usage:
    python run.py --stage <preprocess|score|check_xom|compare_official|isin_gap|discover|validate|all> [--sample] [--force] [--config PATH]
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


def stage_score(cfg: dict) -> None:
    """Eq. (1)-(4): cache/sentences.parquet -> cache/scores_transcript.parquet + outputs/scores_firmyear.csv."""
    import pandas as pd

    from src.io_utils import load_isin_map
    from src.scoring import firm_year, load_dictionaries, load_lexicons, score_sentences_df

    sent_path = ensure_sentences(cfg, "score")

    if cfg["settings"]["dictionary"] != "authors":
        raise NotImplementedError("dictionary: discovered is not built yet (Phase 2)")
    dicts = load_dictionaries(cfg)
    lex = load_lexicons(cfg)
    sents = pd.read_parquet(sent_path)
    scores = score_sentences_df(sents, dicts, lex)
    isin = load_isin_map(cfg)  # read fresh so newly added ISINs are picked up
    scores.insert(2, "isin", scores["ticker"].map(lambda t: isin.get(str(t).upper())))

    out_t = cfg["paths"]["cache"] / "scores_transcript.parquet"
    scores.to_parquet(out_t, index=False)
    fy = firm_year(scores)
    out_f = cfg["paths"]["outputs"] / "scores_firmyear.csv"
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
    """outputs/scores_firmyear.csv vs official csv on (isin, year) -> outputs/compare_official.csv."""
    import pandas as pd

    from src.validation.compare_official import (GAP_MEASURE, compare_table, largest_gaps,
                                                 load_official_all, merge_official)

    ours_path = cfg["paths"]["outputs"] / "scores_firmyear.csv"
    if not ours_path.exists():
        raise FileNotFoundError(f"{ours_path} missing: run --stage score first")
    ours = pd.read_csv(ours_path)
    merged = merge_official(ours, load_official_all(cfg["paths"]["official_scores"]))
    print(f"[compare_official] {len(ours)} firm-years ours, {int(ours['isin'].notna().sum())} with ISIN, "
          f"{len(merged)} matched official on (isin, year), {merged['isin'].nunique()} firms")
    tab = compare_table(merged)
    out = cfg["paths"]["outputs"] / "compare_official.csv"
    tab.to_csv(out, index=False)
    with pd.option_context("display.width", 200):
        print(tab.to_string(index=False, formatters={
            "pearson": "{:.3f}".format, "spearman": "{:.3f}".format, "median_ratio": "{:.3f}".format,
            "mean_ours": "{:.6f}".format, "mean_official": "{:.6f}".format}))
        print(f"\n[compare_official] 5 largest |ours - official| gaps on {GAP_MEASURE}:")
        print(largest_gaps(merged).to_string(index=False, float_format="{:.6f}".format))
    print(f"[compare_official] -> {out}")


def stage_isin_gap(cfg: dict) -> None:
    """Report corpus tickers missing from ticker_isin_map.json (never writes the map)."""
    from src.io_utils import isin_gap
    isin_gap(cfg)


def stage_discover(cfg: dict) -> None:
    """Tasks 2.1 -> 2.2 -> 2.3: seeds, R/S split, 3 classifiers, target set T (cache/discovery/).

    PROTOTYPE: M = all sentences in cache/sentences.parquet, no rough library (Phase 3, task 3.1).
    """
    import time

    import pandas as pd

    from src.discovery.classify import run_classify
    from src.discovery.split import run_split

    t0 = time.perf_counter()
    sents = pd.read_parquet(ensure_sentences(cfg, "discover"))
    R, S = run_split(cfg, sents)
    run_classify(cfg, R, S)
    print(f"[discover] done in {time.perf_counter() - t0:.1f}s")


def stage_validate(cfg: dict) -> None:
    print("[validate] not implemented yet (Phase 4)")


STAGES = {
    "preprocess": stage_preprocess,
    "score": stage_score,
    "check_xom": stage_check_xom,
    "compare_official": stage_compare_official,
    "isin_gap": stage_isin_gap,
    "discover": stage_discover,
    "validate": stage_validate,
}
ALL_ORDER = ["preprocess", "discover", "score", "validate"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sautner et al. (2023) climate-exposure pipeline.")
    parser.add_argument("--stage", required=True, choices=[*STAGES, "all"], help="pipeline stage to run")
    parser.add_argument("--sample", action="store_true",
                        help="run on a small sample (settings.sample_size transcripts)")
    parser.add_argument("--force", action="store_true",
                        help="rebuild cache/*.parquet even if they already exist")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to config.yaml")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    cfg = load_config(args.config)
    if args.sample:
        cfg["settings"]["sample_mode"] = True
    cfg["force"] = args.force

    s = cfg["settings"]
    print(f"sample_mode={s['sample_mode']} sample_size={s['sample_size']} "
          f"chunk_size={s['chunk_size']} dictionary={s['dictionary']}")

    for name in (ALL_ORDER if args.stage == "all" else [args.stage]):
        STAGES[name](cfg)


if __name__ == "__main__":
    main()
