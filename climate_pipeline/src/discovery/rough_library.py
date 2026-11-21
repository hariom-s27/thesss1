"""Discovery task 3.1: the IPCC rough library and the set M (paper IA Section I, steps 1-2).

  C_R   = bigrams of the IPCC reports (data/ipcc/*.pdf), frequency >= discovery.rough_min_freq
  N     = bigrams of "normal" English text (NLTK gutenberg + reuters + brown, list in
          discovery.n_corpora), frequency >= discovery.n_min_freq
  rough = C_R \\ N                       -> cache/discovery/rough_bigrams.pkl
  M     = transcript sentences with >= 1 rough bigram (used when discovery.use_rough_library)

Both corpora go through THE shared cleaner (src.preprocess.lemmatize + make_vectorizer), so
bigrams look exactly like transcript bigrams ("global warm", "unite nation"); frequency =
total count over the corpus. The paper's N also contains IMF reports and textbooks; we only
have the NLTK corpora (a smaller N, so the rough library is somewhat larger than theirs).

Caches (all in cache/discovery/):
  ipcc_text.parquet (+ ipcc_manifest.json)   one row per PDF page; manifest = file names +
                                             sizes. Rebuilt automatically when the PDF set changes.
  ipcc_bigram_counts.parquet                 C_R counts before the threshold (keyed on the PDF manifest)
  normal_bigram_counts.parquet               N counts before the threshold (keyed on n_corpora)
  rough_bigrams.pkl                          the set C_R \\ N for the current thresholds
Thresholds can be changed without re-lemmatizing anything.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from src.preprocess import lemmatize_batch, make_vectorizer

DEFAULT_N_CORPORA = ("gutenberg", "reuters", "brown")
CHUNK_CHARS = 50_000  # normal-text documents are cut into ~50k-character pieces for the workers


def _dir(cfg: dict) -> Path:
    d = Path(cfg["paths"]["cache"]) / "discovery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _hash(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


# ---- pure core ---------------------------------------------------------------------------

def bigram_freq(sentences: list[str]) -> pd.Series:
    """Total bigram counts over cleaned sentences (shared vectorizer; never crosses sentences)."""
    if not sentences:
        return pd.Series(dtype=np.int64, name="count")
    vec = make_vectorizer()
    try:
        X = vec.fit_transform(sentences)
    except ValueError:  # only stop words
        return pd.Series(dtype=np.int64, name="count")
    return pd.Series(np.asarray(X.sum(axis=0)).ravel().astype(np.int64),
                     index=vec.get_feature_names_out(), name="count")


def build_rough(cr_counts: pd.Series, n_counts: pd.Series, rough_min_freq: int,
                n_min_freq: int) -> tuple[set[str], set[str], set[str]]:
    """(C_R, N, rough = C_R \\ N) from raw bigram counts and the two frequency floors."""
    C_R = set(cr_counts.index[cr_counts >= rough_min_freq])
    N = set(n_counts.index[n_counts >= n_min_freq])
    return C_R, N, C_R - N


def rough_mask(sentences: list[str], rough) -> np.ndarray:
    """Boolean per sentence: contains >= 1 rough bigram (same tokenization as everywhere else)."""
    if not len(sentences) or not rough:
        return np.zeros(len(sentences), dtype=bool)
    vec = make_vectorizer(vocabulary=sorted(rough))
    X = vec.transform(sentences)
    return np.diff(X.tocsr().indptr) > 0


def clean_pdf_page(text: str) -> str:
    """Undo PDF line wrapping: join hyphenated line breaks ("decarbon-\\nisation"), lines -> spaces."""
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text or "")
    return re.sub(r"\s*\n\s*", " ", text).strip()


# ---- IPCC text (cached, progress bar, rebuilt when the PDF set changes) -----------------

def ipcc_manifest(pdf_dir: Path) -> list[dict]:
    """Sorted list of {name, size} for every .pdf in pdf_dir."""
    return [{"name": p.name, "size": p.stat().st_size}
            for p in sorted(Path(pdf_dir).glob("*.pdf"), key=lambda p: p.name.lower())]


def _n_pages(path: str) -> int:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)


def _extract_range(path: str, start: int, stop: int) -> list[tuple[int, str]]:
    """Worker: raw text of pages [start, stop) of one PDF (pdfplumber)."""
    import pdfplumber
    out = []
    with pdfplumber.open(path) as pdf:
        for i in range(start, stop):
            try:
                out.append((i, pdf.pages[i].extract_text() or ""))
            except Exception:  # a broken page must not kill a 600-page extraction
                out.append((i, ""))
    return out


def extract_pdfs(paths: list[Path], n_workers: int, pages_per_job: int = 20) -> pd.DataFrame:
    """file, page, text for every page of every PDF; pages are spread over n_workers processes."""
    from tqdm import tqdm
    jobs = []
    for p in paths:
        n = _n_pages(str(p))
        jobs += [(p, s, min(s + pages_per_job, n)) for s in range(0, n, pages_per_job)]
    total = sum(b - a for _, a, b in jobs)
    rows = []
    with ProcessPoolExecutor(max_workers=n_workers) as ex, \
            tqdm(total=total, desc="IPCC pdf pages", unit="page") as bar:
        futs = {ex.submit(_extract_range, str(p), a, b): p.name for p, a, b in jobs}
        for f in as_completed(futs):
            res = f.result()
            rows += [(futs[f], i, clean_pdf_page(t)) for i, t in res]
            bar.update(len(res))
    df = pd.DataFrame(rows, columns=["file", "page", "text"])
    return df.sort_values(["file", "page"], kind="stable").reset_index(drop=True)


def load_ipcc_text(cfg: dict, force: bool = False,
                   extractor: Callable[[list[Path], int], pd.DataFrame] | None = None,
                   verbose: bool = True) -> pd.DataFrame:
    """IPCC page texts from cache/discovery/ipcc_text.parquet, (re)extracted when needed.

    Rebuild when --force, the parquet/manifest is missing, or the {name, size} list of the
    PDFs in paths.ipcc_dir differs from the stored manifest. `extractor` is injectable (tests).
    """
    pdf_dir = Path(cfg["paths"]["ipcc_dir"])
    man = ipcc_manifest(pdf_dir)
    if not man:
        raise FileNotFoundError(f"no .pdf files in {pdf_dir}")
    d = _dir(cfg)
    out, man_path = d / "ipcc_text.parquet", d / "ipcc_manifest.json"
    have = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else None
    if not force and out.exists() and have == man:
        df = pd.read_parquet(out)
        if verbose:
            print(f"[rough] reusing IPCC text cache {out}")
    else:
        why = "--force" if force else ("cache missing" if have is None or not out.exists()
                                      else "PDF set changed")
        if verbose:
            print(f"[rough] extracting IPCC text ({why}) from {len(man)} PDFs in {pdf_dir}")
        paths = [pdf_dir / m["name"] for m in man]
        df = (extractor or extract_pdfs)(paths, int(cfg["discovery"].get("n_workers", 1)))
        df.to_parquet(out, index=False)
        man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")
    if verbose:
        mb = sum(m["size"] for m in man) / 2 ** 20
        per = df.groupby("file").size()
        print(f"[rough] IPCC: {len(man)} PDFs, {len(df):,} pages, {mb:.1f} MB "
              f"({', '.join(f'{f}: {n} p' for f, n in per.items())})")
    return df


# ---- normal text N (NLTK corpora) ---------------------------------------------------------

def _chunks(text: str, size: int = CHUNK_CHARS) -> list[str]:
    """Cut a long text at paragraph breaks into pieces of about `size` characters."""
    out, buf, n = [], [], 0
    for para in re.split(r"\n\s*\n", text):
        buf.append(para)
        n += len(para)
        if n >= size:
            out.append("\n\n".join(buf))
            buf, n = [], 0
    if buf:
        out.append("\n\n".join(buf))
    return out


def normal_texts(corpora=DEFAULT_N_CORPORA) -> list[str]:
    """Raw documents of the NLTK corpora (brown is tagged, so its sentences are re-joined)."""
    import nltk
    texts = []
    for name in corpora:
        c = getattr(nltk.corpus, name)
        for fid in c.fileids():
            if name == "brown":
                txt = "\n\n".join(" ".join(s) for s in c.sents(fid))
            else:
                txt = c.raw(fid)
            texts += _chunks(txt)
    return texts


# ---- parallel lemmatization -------------------------------------------------------------------

def _lemmatize_many(texts: list[str]) -> list[str]:
    return lemmatize_batch(texts)  # == concatenated lemmatize(t), batched with nlp.pipe


def lemmatize_texts(texts: list[str], n_workers: int, desc: str, per_job: int = 4) -> list[str]:
    """lemmatize() every text in parallel; returns all cleaned sentences (order not needed)."""
    from tqdm import tqdm
    jobs = [texts[i:i + per_job] for i in range(0, len(texts), per_job)]
    sents: list[str] = []
    if n_workers <= 1:
        for j in tqdm(jobs, desc=desc, unit="job"):
            sents += _lemmatize_many(j)
        return sents
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        futs = [ex.submit(_lemmatize_many, j) for j in jobs]
        for f in tqdm(as_completed(futs), total=len(futs), desc=desc, unit="job"):
            sents += f.result()
    return sents


def _cached_counts(path: Path, key: str, build: Callable[[], pd.Series], label: str,
                   force: bool) -> pd.Series:
    key_path = path.with_suffix(".key")
    if not force and path.exists() and key_path.exists() and key_path.read_text() == key:
        print(f"[rough] reusing {label} bigram counts {path}")
        s = pd.read_parquet(path)
        return pd.Series(s["count"].to_numpy(), index=s["bigram"].to_numpy(), name="count")
    s = build()
    pd.DataFrame({"bigram": s.index, "count": s.to_numpy()}).to_parquet(path, index=False)
    key_path.write_text(key)
    return s


# ---- stage wrapper ---------------------------------------------------------------------------

def rough_params(cfg: dict) -> dict:
    d = cfg["discovery"]
    return {"rough_min_freq": int(d.get("rough_min_freq", 10)),
            "n_min_freq": int(d.get("n_min_freq", 2)),
            "n_corpora": list(d.get("n_corpora", DEFAULT_N_CORPORA))}


def load_rough_library(cfg: dict, force: bool = False, n_show: int = 40) -> dict:
    """Build/reuse C_R, N and rough; save rough_bigrams.pkl. Returns dict(C_R, N, rough, key)."""
    p = rough_params(cfg)
    d = _dir(cfg)
    nw = int(cfg["discovery"].get("rough_n_workers", cfg["discovery"].get("n_workers", 1)))
    seed = int(cfg["settings"]["sample_seed"])

    pages = load_ipcc_text(cfg, force=force)
    ipcc_key = _hash(ipcc_manifest(Path(cfg["paths"]["ipcc_dir"])))

    def _cr():
        sents = lemmatize_texts(pages["text"].tolist(), nw, "lemmatize IPCC", per_job=8)
        print(f"[rough] IPCC: {len(sents):,} cleaned sentences")
        return bigram_freq(sents)

    def _n():
        texts = normal_texts(p["n_corpora"])
        print(f"[rough] N corpora {p['n_corpora']}: {len(texts):,} text pieces")
        sents = lemmatize_texts(texts, nw, "lemmatize N", per_job=4)
        print(f"[rough] N: {len(sents):,} cleaned sentences")
        return bigram_freq(sents)

    cr = _cached_counts(d / "ipcc_bigram_counts.parquet", ipcc_key, _cr, "IPCC", force)
    nc = _cached_counts(d / "normal_bigram_counts.parquet", _hash(p["n_corpora"]), _n, "N", force)
    C_R, N, rough = build_rough(cr, nc, p["rough_min_freq"], p["n_min_freq"])
    with open(d / "rough_bigrams.pkl", "wb") as f:
        pickle.dump(rough, f)
    key = _hash({"ipcc": ipcc_key, **p, "n_rough": len(rough)})

    print(f"[rough] |C_R| = {len(C_R):,} (IPCC bigrams with frequency >= {p['rough_min_freq']}; "
          f"{len(cr):,} distinct before the floor)")
    print(f"[rough] |N|   = {len(N):,} (normal-text bigrams with frequency >= {p['n_min_freq']}; "
          f"{len(nc):,} distinct before the floor)")
    print(f"[rough] |rough| = |C_R \\ N| = {len(rough):,}  ({len(C_R) - len(rough):,} IPCC bigrams "
          f"removed as normal text) -> {d / 'rough_bigrams.pkl'}")
    if n_show and rough:
        rng = np.random.default_rng(seed)
        show = rng.choice(sorted(rough), size=min(n_show, len(rough)), replace=False)
        print(f"[rough] {len(show)} random rough bigrams: " + ", ".join(show))
    return {"C_R": C_R, "N": N, "rough": rough, "key": key}
