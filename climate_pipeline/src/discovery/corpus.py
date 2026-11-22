"""Full-corpus sentence cache for discovery: cache/discovery/sentences_full.parquet.

Independent of the 200-transcript scoring cache (cache/sentences.parquet). It uses the same
listing (src.io_utils.corpus_listing: all .txt in transcript_dir) and the same cleaner
(src.preprocess.lemmatize), so its rows are identical to what preprocess would produce.

Resumable: lemmatized transcripts are saved in batches to cache/discovery/sentences_full_parts/;
an interrupted build picks up where it stopped. Transcripts already in a matching 200-sample
cache are copied from it instead of re-lemmatized. When everything is done the parts are
concatenated into sentences_full.parquet and recorded in cache/discovery/manifest_full.json.
"""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src.io_utils import corpus_listing, read_manifest, read_text
from src.preprocess import lemmatize

SENT_COLS = ["file", "ticker", "year", "quarter", "sentence_id", "sentence"]
BATCH = 50  # transcripts per saved part


def _paths(cfg: dict) -> tuple[Path, Path, Path]:
    d = Path(cfg["paths"]["cache"]) / "discovery"
    d.mkdir(parents=True, exist_ok=True)
    return d / "sentences_full.parquet", d / "manifest_full.json", d / "sentences_full_parts"


def full_manifest(listing: pd.DataFrame) -> dict:
    names = "\n".join(sorted(listing["file"]))
    return {"corpus": "full", "n_files": int(len(listing)),
            "files_sha1": hashlib.sha1(names.encode("utf-8")).hexdigest()}


def _lemmatize_file(file: str, path: str, ticker, year, quarter) -> list[tuple]:
    """Worker: one transcript -> sentence rows (same as stage_preprocess)."""
    sents = lemmatize(read_text(path))
    return [(file, ticker, year, quarter, j, s) for j, s in enumerate(sents)]


def _to_df(rows: list[tuple]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=SENT_COLS)
    df["year"] = df["year"].astype("Int64")
    df["quarter"] = df["quarter"].astype("Int64")
    return df


def _done_files(parts: Path) -> set[str]:
    done = set()
    for p in sorted(parts.glob("part_*.parquet")):
        done.update(pd.read_parquet(p, columns=["file"])["file"].unique())
    return done


def _seed_from_sample(cfg: dict, parts: Path, listing: pd.DataFrame) -> int:
    """Copy transcripts already lemmatized in the 200-sample cache into a part (if valid)."""
    target = parts / "part_sample.parquet"
    src = Path(cfg["paths"]["cache"]) / "sentences.parquet"
    have = read_manifest(cfg)
    if target.exists() or not src.exists() or not have or "sentences" not in have.get("built", []):
        return 0
    df = pd.read_parquet(src)
    df = df[df["file"].isin(set(listing["file"]))][SENT_COLS]
    if df.empty:
        return 0
    df.to_parquet(target, index=False)
    return int(df["file"].nunique())


def load_full_sentences(cfg: dict, force: bool = False) -> pd.DataFrame:
    """Return the full-corpus sentence table, building/resuming the cache if needed."""
    from tqdm import tqdm

    out, man_path, parts = _paths(cfg)
    listing = corpus_listing(cfg, verbose=False)
    if listing.empty:
        raise FileNotFoundError("no .txt transcripts found in transcript_dir")
    want = full_manifest(listing)

    if not force and out.exists() and man_path.exists():
        have = json.loads(man_path.read_text(encoding="utf-8"))
        if {k: have.get(k) for k in want} == want:
            print(f"[discover] reusing full-corpus sentence cache {out} ({want['n_files']} transcripts)")
            return pd.read_parquet(out)
        print("[discover] full-corpus manifest differs from current listing; rebuilding")

    if force and parts.exists():
        for p in parts.glob("part_*.parquet"):
            p.unlink()
    parts.mkdir(parents=True, exist_ok=True)
    n_seed = _seed_from_sample(cfg, parts, listing)
    if n_seed:
        print(f"[discover] reused {n_seed} transcripts from the 200-sample cache")
    done = _done_files(parts)
    todo = listing[~listing["file"].isin(done)]
    print(f"[discover] full corpus: {len(listing)} transcripts, {len(done)} already lemmatized, "
          f"{len(todo)} to do (workers={cfg['discovery']['n_workers']}, saved every {BATCH})")

    if len(todo):
        k = len(list(parts.glob("part_*.parquet")))
        buf: list[tuple] = []
        n_buf = 0

        def flush():
            nonlocal k, buf, n_buf
            if buf:
                _to_df(buf).to_parquet(parts / f"part_{k:05d}.parquet", index=False)
                k += 1
                buf, n_buf = [], 0

        with ProcessPoolExecutor(max_workers=int(cfg["discovery"]["n_workers"])) as ex:
            futs = [ex.submit(_lemmatize_file, r.file, r.path,
                              None if pd.isna(r.ticker) else r.ticker,
                              None if pd.isna(r.year) else int(r.year),
                              None if pd.isna(r.quarter) else int(r.quarter))
                    for r in todo.itertuples(index=False)]
            for f in tqdm(as_completed(futs), total=len(futs), desc="lemmatize", unit="transcript"):
                buf.extend(f.result())
                n_buf += 1
                if n_buf >= BATCH:
                    flush()
            flush()

    df = pd.concat([pd.read_parquet(p) for p in sorted(parts.glob("part_*.parquet"))], ignore_index=True)
    order = {f: i for i, f in enumerate(listing["file"])}
    df = (df[df["file"].isin(order)]
          .assign(_o=lambda d: d["file"].map(order))
          .sort_values(["_o", "sentence_id"], kind="stable").drop(columns="_o").reset_index(drop=True))
    df.to_parquet(out, index=False)
    man_path.write_text(json.dumps({**want, "built": ["sentences_full"]}, indent=2), encoding="utf-8")
    for p in parts.glob("part_*.parquet"):
        p.unlink()
    parts.rmdir()
    print(f"[discover] full corpus: {df['file'].nunique()} transcripts, {len(df):,} sentences -> {out}")
    return df
