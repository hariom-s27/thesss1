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
TEXT_SCHEMA = 2      # ipcc_text.parquet layout (2 = has the raw-lines column)

# Citation / reference lines (task 3.1b cleaning): keyword hits, "Name, A., 2014"-style
# author-year entries, and "(2017)"-style year citations.
CITE_RE = re.compile(
    r"(?i:\bet\s+al\b|\bdoi\b|https?:|www\.|\bisbn\b)"
    r"|[A-Z][A-Za-z'\-]+,\s+(?:[A-Z]\.\s?-?)+.*?\b(?:19|20)\d{2}\b"
    r"|\((?:19|20)\d{2}[a-z]?\)")
DIGIT_RE = re.compile(r"\b\d+\b")


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


def drop_citation_lines(raw: str) -> tuple[str, int]:
    """Remove citation/reference lines from raw page text, then join lines. -> (text, n dropped)."""
    lines = (raw or "").split("\n")
    keep = [ln for ln in lines if not CITE_RE.search(ln)]
    return clean_pdf_page("\n".join(keep)), len(lines) - len(keep)


def strip_digits(sentence: str) -> str:
    """Remove digit-only tokens from a cleaned sentence ("co2" stays, "2030" goes)."""
    return " ".join(DIGIT_RE.sub(" ", sentence).split())


def unigram_freq(sentences: list[str]) -> pd.Series:
    """Unigram counts with the shared tokenizer / stop words (make_vectorizer, ngram (1,1))."""
    if not sentences:
        return pd.Series(dtype=np.int64, name="count")
    vec = make_vectorizer().set_params(ngram_range=(1, 1))
    try:
        X = vec.fit_transform(sentences)
    except ValueError:
        return pd.Series(dtype=np.int64, name="count")
    return pd.Series(np.asarray(X.sum(axis=0)).ravel().astype(np.int64),
                     index=vec.get_feature_names_out(), name="count")


def valid_words(n_unigrams: pd.Series, transcript_unigrams: pd.Series, min_transcript: int) -> set[str]:
    """Words in N's unigram vocabulary OR seen >= min_transcript times in the transcripts."""
    return set(n_unigrams.index) | set(transcript_unigrams.index[transcript_unigrams >= min_transcript])


def token_valid(bigrams, words: set[str]) -> set[str]:
    """Keep a bigram only if BOTH of its words are valid."""
    return {b for b in bigrams if all(w in words for w in b.split(" "))}


# ---- IPCC text (cached, progress bar, rebuilt when the PDF set changes) -----------------

def ipcc_manifest(pdf_dir: Path) -> list[dict]:
    """Sorted list of {name, size} for every .pdf in pdf_dir."""
    return [{"name": p.name, "size": p.stat().st_size}
            for p in sorted(Path(pdf_dir).glob("*.pdf"), key=lambda p: p.name.lower())]


def _n_pages(path: str) -> int:
    try:  # PyMuPDF counts pages without parsing them (pdfplumber opens the whole tree)
        import pymupdf
        with pymupdf.open(path) as doc:
            return doc.page_count
    except ImportError:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return len(pdf.pages)


def _extract_range(path: str, start: int, stop: int) -> list[tuple[int, str]]:
    """Worker: raw text of pages [start, stop) of one PDF (pdfplumber).

    Each page is closed after use (pdfplumber caches layout objects per page; WG1 pages can
    hold ~1 GB otherwise)."""
    import pdfplumber
    out = []
    with pdfplumber.open(path) as pdf:
        for i in range(start, stop):
            page = pdf.pages[i]
            try:
                out.append((i, page.extract_text() or ""))
            except Exception:  # a broken page must not kill a 600-page extraction
                out.append((i, ""))
            finally:
                page.close()
    return out


def _extract_range_pymupdf(path: str, start: int, stop: int) -> list[tuple[int, str]]:
    """Worker: raw text of pages [start, stop) with PyMuPDF (fast, low memory; used for the
    pages pdfplumber could not finish, see extract_pdfs)."""
    import pymupdf
    out = []
    with pymupdf.open(path) as doc:
        for i in range(start, stop):
            try:
                out.append((i, doc[i].get_text("text") or ""))
            except Exception:
                out.append((i, ""))
    return out


EXTRACTORS = {"pdfplumber": _extract_range, "pymupdf": _extract_range_pymupdf}
TEXT_COLS = ["file", "page", "text", "raw", "extractor"]


def _part_name(pdf: str, size: int, start: int, stop: int) -> str:
    return f"{Path(pdf).stem}__{size}__{start:05d}_{stop:05d}.parquet"


def extract_pdfs(paths: list[Path], n_workers: int, pages_per_job: int = 10,
                 parts_dir: Path | None = None, jobs_per_pool: int = 40,
                 engine: str = "pdfplumber") -> pd.DataFrame:
    """file, page, text (lines joined), raw (pdfplumber lines) for every page of every PDF.

    Pages go to n_workers processes in jobs of pages_per_job. Memory: a FRESH process pool is
    started for every jobs_per_pool jobs (pdfplumber memory grows per process). Not
    max_tasks_per_child: on Windows / Python 3.14 that deadlocked once all workers hit the limit. RESUMABLE: with parts_dir,
    every finished job is saved as one part file (named by PDF, size and page range) and
    skipped on the next run, so an interrupted extraction continues where it stopped.
    engine: extractor for the jobs still TO DO (saved parts keep whatever produced them).
    Column `extractor` records the engine per page (parts from before it existed = pdfplumber).
    MIXED EXTRACTION (task 3.1b, user decision): pdfplumber needed > 5 GB per worker and ~10 s
    per page on the figure-heavy AR5 WG1 pages, so the last ~2,100 pages use PyMuPDF while
    the ~2,800 pages already extracted keep their pdfplumber text.
    """
    fn = EXTRACTORS[engine]
    from tqdm import tqdm
    if parts_dir is not None:
        parts_dir.mkdir(parents=True, exist_ok=True)
    jobs, done_rows = [], []
    for p in paths:
        size = p.stat().st_size
        n = _n_pages(str(p))
        for a in range(0, n, pages_per_job):
            b = min(a + pages_per_job, n)
            part = parts_dir / _part_name(p.name, size, a, b) if parts_dir is not None else None
            if part is not None and part.exists():
                df0 = pd.read_parquet(part)
                if "extractor" not in df0:
                    df0["extractor"] = "pdfplumber"
                done_rows.append(df0)
            else:
                jobs.append((p, a, b, part))
    total = sum(b - a for _, a, b, _ in jobs)
    n_done = sum(len(x) for x in done_rows)
    print(f"[rough] PDF extraction: {n_done:,} pages already extracted (resumed), "
          f"{total:,} to do in {len(jobs):,} jobs of {pages_per_job} pages, {n_workers} workers, "
          f"engine = {engine}")
    new = []
    if jobs:
        with tqdm(total=total, desc="IPCC pdf pages", unit="page") as bar:
            for r in range(0, len(jobs), jobs_per_pool):
                with ProcessPoolExecutor(max_workers=n_workers) as ex:
                    futs = {ex.submit(fn, str(p), a, b): (p.name, part)
                            for p, a, b, part in jobs[r:r + jobs_per_pool]}
                    for f in as_completed(futs):
                        name, part = futs[f]
                        res = f.result()
                        df = pd.DataFrame([(name, i, clean_pdf_page(t), t, engine) for i, t in res],
                                          columns=TEXT_COLS)
                        if part is not None:
                            df.to_parquet(part, index=False)
                        new.append(df)
                        bar.update(len(res))
    df = pd.concat(done_rows + new, ignore_index=True) if (done_rows or new) else \
        pd.DataFrame(columns=TEXT_COLS)
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
    want = {"schema": TEXT_SCHEMA, "files": man}
    if have is not None and not (isinstance(have, dict) and have.get("schema") == TEXT_SCHEMA):
        have = {"old": True}  # cache from before the raw column existed -> rebuild
    if not force and out.exists() and have == want:
        df = pd.read_parquet(out)
        if verbose:
            print(f"[rough] reusing IPCC text cache {out}")
    else:
        why = "--force" if force else ("cache missing" if have is None or not out.exists()
                                      else "old cache format" if "old" in have
                                      else "PDF set changed")
        if verbose:
            print(f"[rough] extracting IPCC text ({why}) from {len(man)} PDFs in {pdf_dir}")
        paths = [pdf_dir / m["name"] for m in man]
        d_cfg = cfg["discovery"]
        nw = int(d_cfg.get("ipcc_extract_workers", d_cfg.get("n_workers", 1)))
        parts = d / "ipcc_text_parts"
        if force and parts.exists():
            for f in parts.glob("*.parquet"):
                f.unlink()
        if extractor is None:
            df = extract_pdfs(paths, nw, parts_dir=parts,
                              engine=str(d_cfg.get("ipcc_extractor", "pdfplumber")))
        else:
            df = extractor(paths, nw)
        df.to_parquet(out, index=False)
        man_path.write_text(json.dumps(want, indent=2), encoding="utf-8")
        if parts.exists():  # parts are only needed until the full cache is written
            for f in parts.glob("*.parquet"):
                f.unlink()
            parts.rmdir()
    if verbose:
        mb = sum(m["size"] for m in man) / 2 ** 20
        per = df.groupby("file").size()
        print(f"[rough] IPCC: {len(man)} PDFs, {len(df):,} pages, {mb:.1f} MB "
              f"({', '.join(f'{f}: {n} p' for f, n in per.items())})")
        if "extractor" in df:
            ex = df.groupby(["file", "extractor"]).size().unstack(fill_value=0)
            print("[rough] pages per extractor:\n" + ex.to_string())
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


def _cached_sentences(path: Path, key: str, build: Callable[[], list[str]], label: str,
                      force: bool) -> list[str]:
    key_path = path.with_suffix(".key")
    if not force and path.exists() and key_path.exists() and key_path.read_text() == key:
        print(f"[rough] reusing {label} sentences {path}")
        return pd.read_parquet(path)["sentence"].tolist()
    sents = build()
    pd.DataFrame({"sentence": sents}).to_parquet(path, index=False)
    key_path.write_text(key)
    return sents


# ---- stage wrapper ---------------------------------------------------------------------------

def rough_params(cfg: dict) -> dict:
    d = cfg["discovery"]
    return {"rough_min_freq": int(d.get("rough_min_freq", 10)),
            "n_min_freq": int(d.get("n_min_freq", 2)),
            "n_corpora": list(d.get("n_corpora", DEFAULT_N_CORPORA))}


def cleaning_params(cfg: dict) -> dict | None:
    """Task 3.1b cleaning settings, or None when discovery.rough_clean is false (old library)."""
    d = cfg["discovery"]
    if not d.get("rough_clean", False):
        return None
    c = d.get("rough_cleaning", {}) or {}
    return {"drop_citation_lines": bool(c.get("drop_citation_lines", True)),
            "drop_digits": bool(c.get("drop_digits", True)),
            "token_validity": bool(c.get("token_validity", True)),
            "min_transcript_count": int(c.get("min_transcript_count", 5))}


def rough_cache_key(ipcc_key: str, p: dict, cl: dict | None, corpus_key: str | None = None) -> str:
    """Identity of a cleaned rough library: PDF set + thresholds + cleaning settings (+ the
    transcript corpus used by the token-validity filter). Part of the M definition, so any
    change re-runs 2.2-2.3 for the variants that use the library."""
    base = {"ipcc": ipcc_key, **p}
    if cl is not None:
        base = {**base, "cleaning": cl, "corpus": corpus_key if cl["token_validity"] else None}
    return _hash(base)


def _transcript_unigrams(cfg: dict, force: bool) -> tuple[pd.Series, str]:
    """Unigram counts over the full transcript corpus (cached on the corpus manifest)."""
    from src.discovery.corpus import full_manifest, load_full_sentences
    from src.io_utils import corpus_listing
    ck = full_manifest(corpus_listing(cfg, verbose=False))["files_sha1"]

    def build():
        sents = load_full_sentences(cfg)
        print(f"[rough] counting unigrams in {len(sents):,} transcript sentences")
        return unigram_freq(sents["sentence"].tolist())
    return _cached_counts(_dir(cfg) / "transcript_unigram_counts.parquet", ck, build,
                          "transcript unigram", force), ck


def load_rough_library(cfg: dict, force: bool = False, n_show: int = 40) -> dict:
    """Build/reuse C_R, N and rough. Returns dict(C_R, N, rough, key).

    discovery.rough_clean false -> the task-3.1 library (rough_bigrams.pkl, variants B/C/D);
    true -> the cleaned task-3.1b library (rough_bigrams_clean.pkl, variants B2/C2/D2).
    """
    if cleaning_params(cfg) is not None:
        return load_clean_rough_library(cfg, force=force, n_show=n_show)
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
    key = _hash({"ipcc": ipcc_key, **p, "n_rough": len(rough)})  # unchanged since task 3.1

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


def load_clean_rough_library(cfg: dict, force: bool = False, n_show: int = 40) -> dict:
    """Task 3.1b: the rough library with the paper's cleaning ("digits, punctuation, and stop
    words removed", IA Section I) plus our token-validity filter.

    Steps (each printed as |C_R| before -> after):
      0. raw C_R: the task-3.1 counts (frequency >= rough_min_freq)
      1. drop citation / reference lines (CITE_RE) before tokenizing
      2. remove digit-only tokens before forming bigrams (strip_digits)
      3. token validity (OUR ADDITION, a cleaning step): keep a bigram only if BOTH words are
         in N's unigram vocabulary or occur >= min_transcript_count times in the transcripts
         (removes author names such as "rogelj" and garbled text such as "esaercni egral")
    then rough = C_R minus N. Punctuation and stop words are already removed by the shared cleaner.
    DEVIATION: no stemming. The paper stems IPCC text, but transcripts are lemmatized, not
    stemmed, and the rule is ONE cleaner, so stemmed rough bigrams would never match them.
    """
    p, cl = rough_params(cfg), cleaning_params(cfg)
    d = _dir(cfg)
    nw = int(cfg["discovery"].get("rough_n_workers", cfg["discovery"].get("n_workers", 1)))
    seed = int(cfg["settings"]["sample_seed"])
    mf = p["rough_min_freq"]

    pages = load_ipcc_text(cfg, force=force)
    ipcc_key = _hash(ipcc_manifest(Path(cfg["paths"]["ipcc_dir"])))
    raw_col = pages["raw"] if "raw" in pages else pages["text"]

    def _lem_pages(texts):
        def build():
            sents = lemmatize_texts(texts, nw, "lemmatize IPCC", per_job=8)
            print(f"[rough] IPCC: {len(sents):,} cleaned sentences")
            return sents
        return build

    cr0 = _cached_counts(d / "ipcc_bigram_counts.parquet", ipcc_key,
                         lambda: bigram_freq(_lem_pages(pages["text"].tolist())()), "IPCC", force)
    steps = [("raw (task 3.1)", set(cr0.index[cr0 >= mf]))]

    if cl["drop_citation_lines"]:
        res = [drop_citation_lines(t) for t in raw_col]
        n_lines = sum(r[1] for r in res)
        n_total = sum(len((t or "").split("\n")) for t in raw_col)
        print(f"[rough] citation filter: dropped {n_lines:,} of {n_total:,} PDF lines "
              f"({n_lines / max(n_total, 1):.1%})")
        sents = _cached_sentences(d / "ipcc_sentences_nocite.parquet",
                                  _hash([ipcc_key, CITE_RE.pattern]),
                                  _lem_pages([r[0] for r in res]), "IPCC (citations dropped)", force)
        cr = bigram_freq(sents)
        steps.append(("- citation lines", set(cr.index[cr >= mf])))
    else:
        sents = _cached_sentences(d / "ipcc_sentences.parquet", ipcc_key,
                                  _lem_pages(pages["text"].tolist()), "IPCC", force)
    if cl["drop_digits"]:
        cr = bigram_freq([x for x in (strip_digits(s) for s in sents) if x])
        steps.append(("- digit tokens", set(cr.index[cr >= mf])))
    C_R = steps[-1][1]

    def _n_sents():
        texts = normal_texts(p["n_corpora"])
        print(f"[rough] N corpora {p['n_corpora']}: {len(texts):,} text pieces")
        out = lemmatize_texts(texts, nw, "lemmatize N", per_job=4)
        print(f"[rough] N: {len(out):,} cleaned sentences")
        return out
    nkey = _hash(p["n_corpora"])
    memo = {}

    def n_sentences():
        if "s" not in memo:
            memo["s"] = _cached_sentences(d / "normal_sentences.parquet", nkey, _n_sents, "N", force)
        return memo["s"]
    nc = _cached_counts(d / "normal_bigram_counts.parquet", nkey, lambda: bigram_freq(n_sentences()),
                        "N", force)
    N = set(nc.index[nc >= p["n_min_freq"]])

    corpus_key = None
    if cl["token_validity"]:
        n_uni = _cached_counts(d / "normal_unigram_counts.parquet", nkey,
                               lambda: unigram_freq(n_sentences()), "N unigram", force)
        t_uni, corpus_key = _transcript_unigrams(cfg, force)
        words = valid_words(n_uni, t_uni, cl["min_transcript_count"])
        C_R = token_valid(C_R, words)
        steps.append((f"- invalid tokens (N vocab or >= {cl['min_transcript_count']}x in transcripts)", C_R))

    rough = C_R - N
    with open(d / "rough_bigrams_clean.pkl", "wb") as f:
        pickle.dump(rough, f)
    key = rough_cache_key(ipcc_key, p, cl, corpus_key)

    print(f"[rough] CLEANED rough library (rough_clean = true; settings {cl}):")
    prev = None
    for name, st in steps:
        delta = "" if prev is None else f"  ({len(st) - prev:+,})"
        print(f"[rough]   |C_R| {name:<62s} {len(st):>7,}{delta}")
        prev = len(st)
    print(f"[rough] |N| = {len(N):,} (frequency >= {p['n_min_freq']})")
    print(f"[rough] |rough| = |C_R \\ N| = {len(rough):,}  ({len(C_R) - len(rough):,} removed as "
          f"normal text) -> {d / 'rough_bigrams_clean.pkl'}")
    if n_show and rough:
        rng = np.random.default_rng(seed)
        show = rng.choice(sorted(rough), size=min(n_show, len(rough)), replace=False)
        print(f"[rough] {len(show)} random rough bigrams: " + ", ".join(show))
    return {"C_R": C_R, "N": N, "rough": rough, "key": key, "steps": [(n, len(x)) for n, x in steps]}
