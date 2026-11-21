"""Task 1.2-1.3: Eq. 2 sentiment, Eq. 3 risk, Eq. 4 TF-IDF."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run import load_config  # noqa: E402
from src import preprocess  # noqa: E402
from src.scoring import (MEASURES, RISK_CURATED, RISK_NARROW, add_tfidf, load_dictionaries,  # noqa: E402
                         load_lexicons, load_lm_words, score_transcript, transcript_parts)

CFG = load_config(PIPELINE_DIR / "config.yaml")
EMPTY = {m: frozenset() for m in MEASURES}


# ---- Eq. 2-3 toy ------------------------------------------------------------------

def test_toy_sentiment_risk_exact():
    sents = ["good carbon tax", "bad carbon tax risk", "sea level rise", "good bad weather"]
    # bigrams: good carbon, carbon tax | bad carbon, carbon tax, tax risk | sea level, level rise
    #          | good bad, bad weather -> B = 9
    dicts = {**EMPTY, "cc": frozenset({"carbon tax", "sea level"})}
    lex = {"pos": frozenset({"good"}), "neg": frozenset({"bad"}), "risk": frozenset({"risk"})}
    r = score_transcript(sents, dicts, lex)
    assert r["B"] == 9
    assert r["cc_expo"] == 3 / 9
    assert r["cc_pos"] == 1 / 9
    assert r["cc_neg"] == -1 / 9          # stored negative
    assert r["cc_sent"] == 0.0
    assert r["cc_risk"] == 1 / 9
    assert r["op_pos"] == 0.0 and r["op_neg"] == 0.0


def test_no_lex_keeps_eq1_only():
    r = score_transcript(["carbon tax rise"], {**EMPTY, "cc": frozenset({"carbon tax"})})
    assert set(r) == {"B", "cc_expo", "op_expo", "rg_expo", "ph_expo"}


def test_risk_list_choice():
    for choice, expect in (("narrow", RISK_NARROW), ("curated", RISK_CURATED)):
        assert load_lexicons({"settings": {"risk_list": choice}}, verbose=False)["risk"] == expect
    lm_unc = load_lexicons({"settings": {"risk_list": "lm_unc"}}, verbose=False)["risk"]
    assert lm_unc == RISK_NARROW | load_lm_words()["unc"]
    with pytest.raises(ValueError):
        load_lexicons({"settings": {"risk_list": "huge"}}, verbose=False)


# ---- Eq. 4 toy --------------------------------------------------------------------

def _tfidf(docs, dicts):
    parts = [transcript_parts(d, dicts) for d in docs]
    return add_tfidf([p[0] for p in parts], [p[1] for p in parts], verbose=False)


def test_toy_tfidf_hand_computed():
    docs = [["carbon tax rise"],                     # carbon tax, tax rise                          B=2
            ["carbon tax hurt", "sea level rise"],   # carbon tax, tax hurt, sea level, level rise   B=4
            ["sea level rise", "sea level"]]         # sea level x2, level rise                      B=3
    dicts = {**EMPTY, "cc": frozenset({"carbon tax", "sea level", "tax rise"})}
    # N=3; f(carbon tax)=2, f(sea level)=2, f(tax rise)=1
    l32, l3 = math.log(3 / 2), math.log(3)
    recs = _tfidf(docs, dicts)
    assert [r["B"] for r in recs] == [2, 4, 3]
    assert recs[0]["cc_expo_tfidf"] == pytest.approx((l32 + l3) / 2, rel=1e-12)
    assert recs[1]["cc_expo_tfidf"] == pytest.approx((l32 + l32) / 4, rel=1e-12)
    assert recs[2]["cc_expo_tfidf"] == pytest.approx(2 * l32 / 3, rel=1e-12)
    assert all(r["op_expo_tfidf"] == 0.0 for r in recs)


def test_bigram_in_every_transcript_has_zero_weight():
    docs = [["carbon tax rise"], ["carbon tax hurt margin"], ["new carbon tax"]]
    recs = _tfidf(docs, {**EMPTY, "cc": frozenset({"carbon tax"})})
    assert all(r["cc_expo"] > 0 for r in recs)
    assert all(r["cc_expo_tfidf"] == 0.0 for r in recs)


def test_tfidf_matches_old_phase3_logic():
    import reference_old as ref
    docs = [["carbon tax rise", "sea level rise fast"], ["carbon tax hurt margin"],
            ["sea level rise", "sea level", "clean energy grow"], ["clean energy carbon tax"]]
    D = frozenset({"carbon tax", "sea level", "clean energy", "level rise"})
    new = _tfidf(docs, {**EMPTY, "cc": D})
    old = ref.tfidf(docs, D)
    for n, o in zip(new, old):
        assert n["B"] == o["B"]
        assert n["cc_expo"] == o["cc_expo"]
        assert n["cc_expo_tfidf"] == pytest.approx(o["cc_tfidf"], rel=1e-12)


def test_empty_transcript_gives_nan():
    recs = _tfidf([[], ["carbon tax rise"]], {**EMPTY, "cc": frozenset({"carbon tax"})})
    assert np.isnan(recs[0]["cc_expo_tfidf"])
    assert recs[1]["cc_expo_tfidf"] == pytest.approx(math.log(2) / 2)  # N=2, f=1, B=2


# ---- Eq. 2-3 on a real transcript vs frozen old phase2 measures() ------------------

def test_real_transcript_matches_old_phase2():
    d = CFG["paths"]["authors_dictionaries"]
    if not all((d / f).exists() for f in CFG["dictionaries"].values()):
        pytest.skip(f"authors' dictionaries missing: {d}")
    tdir = CFG["paths"]["transcript_dir"]
    files = (sorted(tdir.glob("XOM_*.txt")) or sorted(tdir.glob("*.txt"))) if tdir.is_dir() else []
    if not files:
        pytest.skip(f"transcript_dir not found or has no .txt files: {tdir}")
    import reference_old as ref

    dicts = load_dictionaries(CFG, verbose=False)
    text = files[-1].read_text(encoding="utf-8", errors="replace")
    new_sents, old_sents = preprocess.lemmatize(text), ref.lemmatize(text)
    assert new_sents == old_sents
    for risk_list in ("curated", "lm_unc"):
        lex = load_lexicons({"settings": {"risk_list": risk_list}}, verbose=False)
        new = score_transcript(new_sents, dicts, lex)
        assert new["cc_pos"] > 0 and new["cc_neg"] < 0
        for m in MEASURES:
            old = ref.measures(old_sents, CC=dicts[m], POS=lex["pos"], NEG=lex["neg"], RISKW=lex["risk"])
            assert new["B"] == old["B"]
            for s in ("expo", "pos", "neg", "sent", "risk"):
                assert new[f"{m}_{s}"] == old[f"cc_{s}"], (risk_list, m, s)  # exact
