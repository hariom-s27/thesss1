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


def list_transcripts(cfg: dict, sources: tuple[str, ...] = ("txt", "pdf"),
                     verbose: bool = True) -> pd.DataFrame:
    """Transcripts as a metadata DataFrame: .txt from transcript_dir, .pdf from pdf_dir.

    PDF names carry no ticker, so every PDF gets settings.pdf_ticker / settings.pdf_isin
    (ExxonMobil; the PDFs are used only for the XOM validation check).
    """
    rows = []
    for key, source in (("transcript_dir", "txt"), ("pdf_dir", "pdf")):
        if source not in sources:
            continue
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
    s = cfg["settings"]
    is_pdf = df["source"] == "pdf"
    if is_pdf.any():
        df["ticker"] = df["ticker"].astype(object)
        df.loc[is_pdf, "ticker"] = str(s["pdf_ticker"]).upper()
    isin = load_isin_map(cfg)
    if is_pdf.any() and s.get("pdf_isin"):
        isin[str(s["pdf_ticker"]).upper()] = s["pdf_isin"]
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


# ---- cache manifest -----------------------------------------------------------

def _manifest_path(cfg: dict) -> Path:
    return Path(cfg["paths"]["cache"]) / "manifest.json"


def current_manifest(cfg: dict, n_files: int) -> dict:
    """Settings that define the cached corpus. Sample size/seed only matter in sample mode."""
    s = cfg["settings"]
    sample = bool(s["sample_mode"])
    return {"mode": "sample" if sample else "full",
            "sample_size": s["sample_size"] if sample else None,
            "sample_seed": s["sample_seed"] if sample else None,
            "n_files": int(n_files)}


def read_manifest(cfg: dict) -> dict | None:
    p = _manifest_path(cfg)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_manifest(cfg: dict, want: dict, built: list[str]) -> None:
    p = _manifest_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({**want, "built": built}, f, indent=2)


def manifest_mismatch(cfg: dict, want: dict, stage: str) -> str | None:
    """Why the cache for `stage` must be rebuilt, or None if it matches `want`."""
    have = read_manifest(cfg)
    if have is None:
        return "no cache/manifest.json"
    diffs = [f"{k}: cached={have.get(k)!r} now={v!r}" for k, v in want.items() if have.get(k) != v]
    if diffs:
        return "manifest differs (" + "; ".join(diffs) + ")"
    if stage not in have.get("built", []):
        return f"{stage} not built for these settings"
    return None


def corpus_listing(cfg: dict, verbose: bool = True) -> pd.DataFrame:
    """The scoring corpus = .txt transcripts only (PDFs are kept for check_xom)."""
    return list_transcripts(cfg, sources=("txt",), verbose=verbose)


def load_transcripts(cfg: dict, force: bool = False) -> pd.DataFrame:
    """list .txt -> sample (if sample_mode) -> read; cached in cache/transcripts.parquet.

    The cache is rebuilt when --force is given, when it is missing, or when
    cache/manifest.json does not match the current settings (the reason is printed).
    """
    out = Path(cfg["paths"]["cache"]) / "transcripts.parquet"
    s = cfg["settings"]
    listing = corpus_listing(cfg)
    if listing.empty:
        raise FileNotFoundError("no .txt transcripts found in transcript_dir")
    want = current_manifest(cfg, len(listing))

    if force:
        reason = "--force"
    elif not out.exists():
        reason = f"{out.name} missing"
    else:
        reason = manifest_mismatch(cfg, want, "transcripts")
    if reason is None:
        print(f"[io] reusing cached {out} (manifest matches; use --force to rebuild)")
        df = pd.read_parquet(out)
        print_summary(df, len(listing))
        return df

    print(f"[io] rebuilding transcripts cache: {reason}")
    df = listing
    if s["sample_mode"]:
        df = sample_transcripts(df, s["sample_size"], s["sample_seed"])
    df = df.copy()
    df["text"] = [read_text(p) for p in df["path"]]
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    write_manifest(cfg, want, built=["transcripts"])  # sentences must now be rebuilt too
    print_summary(df, len(listing))
    print(f"[io] cached {len(df)} transcripts -> {out}")
    return df


# ---- ISIN coverage ----------------------------------------------------------

_ID_HINTS = ("ticker", "tic", "symbol", "conm", "company", "name", "comnam")


def isin_gap(cfg: dict) -> pd.DataFrame:
    """Tickers in the .txt corpus with no ISIN in ticker_isin_map.json.

    Proposes matches only if official_scores has a ticker/company-name column that
    can be joined reliably. It never writes to ticker_isin_map.json and never guesses.
    """
    listing = corpus_listing(cfg, verbose=False)
    counts = listing.groupby("ticker").size()
    missing = listing.loc[listing["isin"].isna(), "ticker"].dropna()
    gap = (pd.DataFrame({"ticker": sorted(missing.unique())})
           .assign(n_transcripts=lambda d: d["ticker"].map(counts).astype(int)))
    print(f"[isin] {listing['ticker'].nunique()} tickers in corpus, "
          f"{len(gap)} without ISIN in ticker_isin_map.json:")
    print(gap.to_string(index=False) if len(gap) else "  (none)")

    off_path = Path(cfg["paths"]["official_scores"])
    if not off_path.exists():
        print(f"[isin] official_scores not found: {off_path}")
        return gap
    cols = list(pd.read_csv(off_path, nrows=0).columns)
    id_cols = [c for c in cols if c.lower() in _ID_HINTS]
    print(f"[isin] official_scores columns: {cols}")
    if not id_cols:
        print("[isin] official_scores has no ticker or company-name column (only isin/gvkey/cusip), "
              "so tickers cannot be matched to ISINs reliably from it. No matches proposed.")
        gap["proposed_isin"] = np.nan
        return gap
    # A ticker column exists: propose exact, unique matches only.
    off = pd.read_csv(off_path, usecols=["isin", *id_cols], low_memory=False).drop_duplicates()
    prop = {}
    for c in id_cols:
        u = off.assign(key=off[c].astype(str).str.upper().str.strip()).groupby("key")["isin"].unique()
        for t in gap["ticker"]:
            if t in u.index and len(u[t]) == 1 and t not in prop:
                prop[t] = f"{u[t][0]} (via {c})"
    gap["proposed_isin"] = gap["ticker"].map(prop)
    print("[isin] proposed matches (NOT written; check and add by hand):")
    print(gap.to_string(index=False))
    return gap


def print_summary(df: pd.DataFrame, n_total: int) -> None:
    yrs = df["year"].dropna()
    yr = f"{int(yrs.min())}-{int(yrs.max())}" if len(yrs) else "n/a"
    print("[io] summary: "
          f"found={n_total} | sampled={len(df)} | firms={df['ticker'].nunique()} | "
          f"years={yr} | with_isin={int(df['isin'].notna().sum())}/{len(df)}")
