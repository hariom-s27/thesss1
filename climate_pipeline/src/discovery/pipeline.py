"""Shared driver for discovery 2.2-2.3 under one M definition, with caching.

Used by `--stage discover` (the config's own settings) and `--stage discover_variants`
(one run per variant). The classifier output (R, S, S_scored) lives in discovery_dir(cfg):
  cache/discovery/          M = all sentences (prototype, variant A)
  cache/discovery/m_rough/  M = sentences with >= 1 rough-library bigram (variants B, C, D)
and is reused while classify_manifest.json there matches (corpus, M definition, |S|).
The candidate filters N2 / F act at ranking, so they never trigger a classifier re-run.
"""
from __future__ import annotations

import json
from typing import Callable

import pandas as pd

from src.discovery.split import discovery_dir, uses_rough


def discovery_corpus(cfg: dict) -> str:
    corpus = "sample" if cfg["settings"]["sample_mode"] else cfg["discovery"]["corpus"]
    if corpus not in ("full", "sample"):
        raise ValueError(f"discovery.corpus must be full or sample, got {corpus!r}")
    return corpus


def m_definition(cfg: dict, rough_key: str | None) -> str:
    """'all' (prototype) or 'rough:<key>' (key changes with the PDF set and the thresholds)."""
    if not uses_rough(cfg):
        return "all"
    if rough_key is None:
        raise ValueError("use_rough_library needs the rough library")
    return f"rough:{rough_key}"


def _expected_n_files(cfg: dict, corpus: str) -> int | None:
    if corpus == "sample":
        return int(cfg["settings"]["sample_size"])
    p = cfg["paths"]["cache"] / "discovery" / "manifest_full.json"
    return json.loads(p.read_text(encoding="utf-8"))["n_files"] if p.exists() else None


def cached_classify(cfg: dict, corpus: str, m_def: str = "all", verbose: bool = True):
    """(R, S, S_scored) from discovery_dir(cfg) if built on (corpus, m_def), else None.

    A cache from before the manifest existed is accepted for m_def 'all' when its transcript
    count matches the corpus (the manifest is then written). A manifest without 'm_def' is
    from before task 3.1, i.e. 'all'. in_T is recomputed from the stored p_max with the current
    discovery.t_threshold (cheap; no classifier is re-run).
    """
    d = discovery_dir(cfg)
    paths = [d / f for f in ("R.parquet", "S.parquet", "S_scored.parquet")]
    if cfg.get("force", False) or not all(p.exists() for p in paths):
        return None
    R, S, scored = (pd.read_parquet(p) for p in paths)
    n_files = int(pd.concat([R["file"], S["file"]]).nunique())
    man = d / "classify_manifest.json"
    if man.exists():
        have = json.loads(man.read_text(encoding="utf-8"))
        ok = (have.get("corpus") == corpus and have.get("n_S") == len(S)
              and have.get("m_def", "all") == m_def)
    else:
        ok = m_def == "all" and n_files == _expected_n_files(cfg, corpus)
        if ok:
            write_manifest(cfg, corpus, m_def, n_files, R, S)
    if not ok or len(scored) != len(S):
        if verbose:
            print(f"[discover] cached 2.2-2.3 output in {d} does not match corpus={corpus}, "
                  f"M={m_def.split(':')[0]}; re-running 2.2-2.3")
        return None
    thr = float(cfg["discovery"]["t_threshold"])
    scored["in_T"] = scored["p_max"] > thr
    if verbose:
        print(f"[discover] reusing cached 2.2-2.3 output ({corpus} corpus, M={m_def.split(':')[0]}, "
              f"{n_files} transcripts) from {d}: |M| = {len(R) + len(S):,}  |R| = {len(R):,}  "
              f"|S| = {len(S):,}  |T| = {int(scored['in_T'].sum()):,} (p_max > {thr})")
    return R, S, scored


def write_manifest(cfg: dict, corpus: str, m_def: str, n_files: int, R, S, **extra) -> None:
    (discovery_dir(cfg) / "classify_manifest.json").write_text(json.dumps(
        {"corpus": corpus, "m_def": m_def, "n_files": int(n_files), "n_R": len(R), "n_S": len(S),
         **extra}, indent=2), encoding="utf-8")


def get_classified(cfg: dict, corpus: str, load_sents: Callable[[], pd.DataFrame],
                   rough: dict | None = None):
    """Tasks 2.2-2.3 for the M of cfg: cached, or split + classify (M filtered by the rough library).

    load_sents() returns the corpus sentence table (only called when the cache cannot be used);
    rough = output of rough_library.load_rough_library (needed when use_rough_library).
    """
    from src.discovery.classify import run_classify
    from src.discovery.rough_library import rough_mask
    from src.discovery.split import run_split

    m_def = m_definition(cfg, rough["key"] if rough else None)
    cached = cached_classify(cfg, corpus, m_def)
    if cached is not None:
        return cached
    sents = load_sents()
    n_all = len(sents)
    if uses_rough(cfg):
        mask = rough_mask(sents["sentence"].tolist(), rough["rough"])
        sents = sents.loc[mask].reset_index(drop=True)
        print(f"[discover] task 3.1: M = {len(sents):,} of {n_all:,} sentences "
              f"({len(sents) / max(n_all, 1):.1%}) contain >= 1 of {len(rough['rough']):,} rough bigrams")
    R, S = run_split(cfg, sents)
    scored = run_classify(cfg, R, S)
    write_manifest(cfg, corpus, m_def, sents["file"].nunique(), R, S, n_corpus_sentences=n_all)
    return R, S, scored


def file_meta(cfg: dict) -> pd.DataFrame:
    """file -> ticker, year for every corpus transcript (parsed from file names, cheap)."""
    from src.io_utils import corpus_listing
    return corpus_listing(cfg, verbose=False).set_index("file")[["ticker", "year"]]
