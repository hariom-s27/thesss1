"""Single entry point for the climate-exposure pipeline.

Usage:
    python run.py --stage <preprocess|score|discover|validate|all> [--sample] [--config PATH]
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
    """Lemmatize .txt transcripts into cache/sentences.parquet (file, sentence_id, sentence)."""
    import pandas as pd

    from src.preprocess import lemmatize

    tdir = cfg["paths"]["transcript_dir"]
    files = sorted(tdir.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"no .txt transcripts in transcript_dir: {tdir}")
    if cfg["settings"]["sample_mode"]:
        files = files[: cfg["settings"]["sample_size"]]

    rows = []
    for i, p in enumerate(files, 1):
        sents = lemmatize(p.read_text(encoding="utf-8"))
        rows.extend((p.name, j, s) for j, s in enumerate(sents))
        if i % 25 == 0 or i == len(files):
            print(f"[preprocess] {i}/{len(files)} transcripts")

    df = pd.DataFrame(rows, columns=["file", "sentence_id", "sentence"])
    out = cfg["paths"]["cache"] / "sentences.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"[preprocess] processed {len(files)} transcripts, {len(df)} sentences -> {out}")


def stage_score(cfg: dict) -> None:
    print("[score] not implemented yet (Phase 1)")


def stage_discover(cfg: dict) -> None:
    print("[discover] not implemented yet (Phase 2)")


def stage_validate(cfg: dict) -> None:
    print("[validate] not implemented yet (Phase 4)")


STAGES = {
    "preprocess": stage_preprocess,
    "score": stage_score,
    "discover": stage_discover,
    "validate": stage_validate,
}
ALL_ORDER = ["preprocess", "discover", "score", "validate"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sautner et al. (2023) climate-exposure pipeline.")
    parser.add_argument("--stage", required=True, choices=[*STAGES, "all"], help="pipeline stage to run")
    parser.add_argument("--sample", action="store_true",
                        help="run on a small sample (settings.sample_size transcripts)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to config.yaml")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    cfg = load_config(args.config)
    if args.sample:
        cfg["settings"]["sample_mode"] = True

    s = cfg["settings"]
    print(f"sample_mode={s['sample_mode']} sample_size={s['sample_size']} "
          f"chunk_size={s['chunk_size']} dictionary={s['dictionary']}")

    for name in (ALL_ORDER if args.stage == "all" else [args.stage]):
        STAGES[name](cfg)


if __name__ == "__main__":
    main()
