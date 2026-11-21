"""Transcript loading: list (txt/pdf) -> sample -> read -> parquet cache.

All paths come from config.yaml (`paths.transcript_dir`, `paths.pdf_dir`, `paths.cache`,
`paths.ticker_isin_map`).
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd

META_COLS = ["file", "path", "ticker", "year", "quarter", "source", "isin"]

# "BA_2007Q2.txt", "BRK.B_2019Q4.txt"
_NAME_RE = re.compile(r"^(?P<ticker>[A-Za-z][A-Za-z0-9.\-]*)_(?P<year>\d{4})Q(?P<quarter>[1-4])$")
# old PDF names: "1Q24 Earnings Call Transcript.pdf" / "Q1 2024 ..." (no ticker in the name)
_PDF_RE = re.compile(r"([1-4])Q(\d{2,4})|Q([1-4])\s?(\d{2,4})")


def parse_name(file: str) -> dict:
    """Parse ticker/year/quarter from a transcript file name; unparseable parts are NaN.

    "BA_2007Q2.txt" -> {"ticker": "BA", "year": 2007, "quarter": 2}.
    Old PDF names like "1Q24 Earnings Call Transcript.pdf" give year/quarter, ticker NaN.
    """
    stem = Path(file).stem
    m = _NAME_RE.match(stem)
    if m:
        return {"ticker": m["ticker"].upper(), "year": int(m["year"]), "quarter": int(m["quarter"])}
    out = {"ticker": np.nan, "year": np.nan, "quarter": np.nan}
    if Path(file).suffix.lower() == ".pdf":
        m = _PDF_RE.search(stem)
        if m:
            q, yr = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            out["year"] = int(yr) + 2000 if len(yr) == 2 else int(yr)
            out["quarter"] = int(q)
    return out


def load_isin_map(cfg: dict) -> dict:
    p = cfg["paths"].get("ticker_isin_map")
    if p is None or not Path(p).exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return {k.upper(): v for k, v in json.load(f).items()}


def list_transcripts(cfg: dict, verbose: bool = True) -> pd.DataFrame:
    """All .txt (transcript_dir) and .pdf (pdf_dir) transcripts as a metadata DataFrame."""
    rows = []
    for key, source in (("transcript_dir", "txt"), ("pdf_dir", "pdf")):
        d = cfg["paths"].get(key)
        if d is None or not Path(d).is_dir():
            if verbose:
                print(f"[io] {key} not found, skipped: {d}")
            continue
        for p in sorted(Path(d).glob(f"*.{source}")):
            rows.append({"file": p.name, "path": str(p), **parse_name(p.name), "source": source})

    df = pd.DataFrame(rows, columns=META_COLS[:-1])
    df["year"] = df["year"].astype("Int64")
    df["quarter"] = df["quarter"].astype("Int64")
    isin = load_isin_map(cfg)
    df["isin"] = df["ticker"].map(lambda t: isin.get(t, np.nan) if isinstance(t, str) else np.nan)

    n_bad = int(df[["ticker", "year", "quarter"]].isna().any(axis=1).sum())
    if verbose and n_bad:
        print(f"[io] {n_bad} file name(s) could not be fully parsed (kept with NaN fields)")
    return df[META_COLS]


def sample_transcripts(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Random, firm-spread sample: shuffle each firm's transcripts (fixed seed), shuffle
    the firm order, then take one transcript per firm round-robin until n are taken.
    Rows without a ticker are pooled into one group.
    """
    if n >= len(df):
        return df.reset_index(drop=True)
    rng = random.Random(seed)
    key = df["ticker"].fillna("<no-ticker>")
    groups = {t: list(idx) for t, idx in df.groupby(key, sort=True).groups.items()}
    for idx in groups.values():
        rng.shuffle(idx)
    order = sorted(groups)
    rng.shuffle(order)

    picked, rnd = [], 0
    while len(picked) < n:
        for t in order:
            if rnd < len(groups[t]):
                picked.append(groups[t][rnd])
                if len(picked) == n:
                    break
        rnd += 1
    return df.loc[picked].reset_index(drop=True)


def read_pdf(path: str | Path) -> str:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def read_text(path: str | Path) -> str:
    """.txt read directly (utf-8, errors replaced); .pdf via pdfplumber."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return path.read_text(encoding="utf-8", errors="replace")


def load_transcripts(cfg: dict, force: bool = False) -> pd.DataFrame:
    """list -> sample (if sample_mode) -> read; cached in cache/transcripts.parquet."""
    out = Path(cfg["paths"]["cache"]) / "transcripts.parquet"
    if out.exists() and not force:
        print(f"[io] reusing cached {out} (use --force to rebuild)")
        df = pd.read_parquet(out)
        print_summary(df, len(list_transcripts(cfg, verbose=False)))
        return df

    s = cfg["settings"]
    df = list_transcripts(cfg)
    if df.empty:
        raise FileNotFoundError("no transcripts found in transcript_dir / pdf_dir")
    n_total = len(df)
    if s["sample_mode"]:
        df = sample_transcripts(df, s["sample_size"], s["sample_seed"])

    df["text"] = [read_text(p) for p in df["path"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print_summary(df, n_total)
    print(f"[io] cached {len(df)} transcripts -> {out}")
    return df


def print_summary(df: pd.DataFrame, n_total: int) -> None:
    yrs = df["year"].dropna()
    yr = f"{int(yrs.min())}-{int(yrs.max())}" if len(yrs) else "n/a"
    print("[io] summary: "
          f"found={n_total} | sampled={len(df)} | firms={df['ticker'].nunique()} | "
          f"years={yr} | with_isin={int(df['isin'].notna().sum())}/{len(df)}")
