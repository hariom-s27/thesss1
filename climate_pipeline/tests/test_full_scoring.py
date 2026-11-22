"""Full-corpus scoring: reuse of the discovery sentence cache + risk-list sensitivity."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

import run  # noqa: E402
from src.discovery import corpus  # noqa: E402
from src.scoring import RISK_LISTS, RISK_VARIANT_COLS, firm_year, score_transcript  # noqa: E402
from src.validation.compare_official import merge_official, risk_sensitivity  # noqa: E402

CFG = run.load_config(PIPELINE_DIR / "config.yaml")


def _lex():
    variants = {"narrow": frozenset({"risk"}), "curated": frozenset({"risk", "threat"}),
                "lm_unc": frozenset({"risk", "uncertain", "may"})}
    return {"pos": frozenset({"good"}), "neg": frozenset({"bad"}), "risk": variants["curated"],
            "risk_variants": variants}


def test_risk_variant_columns_exact():
    sents = ["carbon tax risk", "carbon tax threat", "sea level may rise"]
    # bigrams: carbon tax x2, tax risk, tax threat, sea level, level rise ("may" is a stop word) -> B=6
    d = {"cc": frozenset({"carbon tax", "sea level"}), "op": frozenset(), "rg": frozenset(), "ph": frozenset()}
    r = score_transcript(sents, d, _lex())
    assert r["B"] == 6
    assert r["cc_risk_narrow"] == 1 / 6
    assert r["cc_risk_curated"] == 2 / 6 == r["cc_risk"]      # default list == curated variant
    assert r["cc_risk_lm_unc"] == 2 / 6                       # sentences 1 and 3
    assert all(c in r for c in RISK_VARIANT_COLS)


def test_risk_sensitivity_three_rows_per_measure():
    rng = np.random.default_rng(0)
    n = 12
    ours = pd.DataFrame({"ticker": ["A"] * n, "isin": [f"I{i}" for i in range(n)], "year": [2020] * n})
    off = ours[["isin", "year"]].copy()
    for m in ("cc", "op", "rg", "ph"):
        off[f"{m}_risk_ew"] = rng.random(n)
        for k, r in enumerate(RISK_LISTS):
            ours[f"{m}_risk_{r}"] = off[f"{m}_risk_ew"] * (k + 1) + rng.random(n) * 0.01 * k
    fy = firm_year(ours.assign(cc_expo=0.0))
    assert all(c in fy for c in RISK_VARIANT_COLS)            # firm_year keeps the variant columns
    tab = risk_sensitivity(merge_official(fy, off))
    assert len(tab) == 12
    assert (tab.groupby("measure")["risk_list"].apply(sorted) == [sorted(RISK_LISTS)] * 4).all()
    narrow = tab[tab["risk_list"] == "narrow"]
    assert np.allclose(narrow["pearson"], 1.0) and np.allclose(narrow["median_ratio"], 1.0)
    assert np.allclose(tab[tab["risk_list"] == "curated"]["median_ratio"], 2.0, atol=0.05)


def test_full_scoring_reuses_full_cache(tmp_path, monkeypatch):
    """Without --sample, stage score reads cache/discovery/sentences_full.parquet and never lemmatizes."""
    d = CFG["paths"]["authors_dictionaries"]
    if not all((d / f).exists() for f in CFG["dictionaries"].values()):
        pytest.skip(f"authors' dictionaries missing: {d}")
    tdir = tmp_path / "txt"
    tdir.mkdir()
    for name in ("XOM_2020Q1", "XOM_2020Q2", "CVX_2021Q1"):
        (tdir / f"{name}.txt").write_text("unused: must not be read", encoding="utf-8")
    cfg = {**CFG, "paths": {**CFG["paths"], "transcript_dir": tdir, "cache": tmp_path / "cache",
                            "outputs": tmp_path / "out", "pdf_dir": tmp_path / "nopdf"},
           "settings": {**CFG["settings"], "sample_mode": False}, "force": False}
    from src.io_utils import corpus_listing
    lst = corpus_listing(cfg, verbose=False)
    sent = "we face carbon tax risk and climate change uncertainty"
    rows = [(r.file, r.ticker, int(r.year), int(r.quarter), j, s)
            for r in lst.itertuples() for j, s in enumerate([sent, "revenue grow strong"])]
    out, man, _ = corpus._paths(cfg)
    corpus._to_df(rows).to_parquet(out, index=False)
    man.write_text(json.dumps({**corpus.full_manifest(lst), "built": ["sentences_full"]}), encoding="utf-8")

    def boom(*a, **k):
        raise AssertionError("full scoring must reuse the cache, not lemmatize")
    monkeypatch.setattr(corpus, "lemmatize", boom)
    monkeypatch.setattr(corpus, "read_text", boom)
    monkeypatch.setattr(run, "ensure_sentences", boom)        # never touches the 200-sample cache

    run.stage_score(cfg)
    fy = pd.read_csv(tmp_path / "out" / "scores_firmyear_full.csv")
    assert not (tmp_path / "out" / "scores_firmyear.csv").exists()
    assert (tmp_path / "cache" / "scores_transcript_full.parquet").exists()
    assert len(fy) == 2 and fy["n_transcripts"].sum() == 3
    assert all(c in fy for c in RISK_VARIANT_COLS)
    assert fy["cc_expo"].gt(0).all()
