"""Task 3.1: rough library (C_R \\ N), set M, filters N2 and F, IPCC cache, variants."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

from run import load_config  # noqa: E402
from src.discovery.build_dict import build_dictionary  # noqa: E402
from src.discovery.rank import (candidate_exclusions, filter_params, firms_per_bigram,  # noqa: E402
                                rank_counts, rank_from_matrix, s_bigram_matrix)
from src.discovery.rough_library import (bigram_freq, build_rough, clean_pdf_page,  # noqa: E402
                                         load_ipcc_text, rough_mask)
from src.discovery.variants import pick_best, top_shift, variant_cfg, vocab_shift  # noqa: E402
from src.preprocess import lemmatize, lemmatize_batch  # noqa: E402

CFG = load_config(PIPELINE_DIR / "config.yaml")


# ---- C_R \ N on toy text ---------------------------------------------------------------

def test_rough_is_cr_minus_n_on_toy_text():
    ipcc = lemmatize("Global warming raises the sea level. Global warming is caused by greenhouse gases. "
                     "Global warming harms coral reefs. The long term outlook is uncertain. "
                     "The long term trend of greenhouse gases rises.")
    normal = lemmatize("In the long term we are all dead. The long term plan worked. "
                       "Coral reefs are pretty.")
    cr, nc = bigram_freq(ipcc), bigram_freq(normal)
    assert cr["global warming"] == 3                   # same lemmas as transcripts (spaCy keeps "warming")
    C_R, N, rough = build_rough(cr, nc, rough_min_freq=2, n_min_freq=2)
    assert C_R == {"global warming", "long term", "greenhouse gas"}
    assert "long term" in N and "coral reef" not in N  # coral reef: freq 1 < n_min_freq
    assert rough == {"global warming", "greenhouse gas"}
    # floors are inclusive (>=)
    _, _, rough1 = build_rough(cr, nc, rough_min_freq=1, n_min_freq=1)
    assert "coral reef" not in rough1 and "sea level" in rough1


def test_rough_mask_selects_m():
    sents = ["global warm be real", "revenue grow", "warm global", "we cut greenhouse gas"]
    assert rough_mask(sents, {"global warm", "greenhouse gas"}).tolist() == [True, False, False, True]
    assert not rough_mask(sents, set()).any()


def test_clean_pdf_page_joins_lines():
    assert clean_pdf_page("decarbon-\nisation of the\n energy system") == "decarbonisation of the energy system"


def test_lemmatize_batch_equals_lemmatize():
    texts = ["The sea levels are rising. Firms reduced emissions!", "", "Wind farms were built in 2020."]
    assert lemmatize_batch(texts) == [s for t in texts for s in lemmatize(t)]


# ---- N2 filter ---------------------------------------------------------------------------

def test_n2_filter_drops_bigrams_in_n():
    args = dict(bigrams=["solar farm", "long term", "carbon tax"], n_kT=[5, 9, 4], n_kST=[0, 0, 0],
                N_T=10, N_ST=100, min_t_only_df=3, top_pct=1.0)
    N = {"long term", "next year"}
    off = rank_counts(**args, exclude=candidate_exclusions(["carbon tax"], N, use_N=False))
    on = rank_counts(**args, exclude=candidate_exclusions(["carbon tax"], N, use_N=True))
    assert set(off["bigram"]) == {"solar farm", "long term"}
    assert set(on["bigram"]) == {"solar farm"}
    with pytest.raises(ValueError):
        candidate_exclusions([], None, use_N=True)


# ---- firm filter F -------------------------------------------------------------------------

def test_firm_filter():
    sents = ["solar farm one", "solar farm two", "solar farm three",      # T, 3 firms
             "boiler plate a", "boiler plate b", "boiler plate c",        # T, 1 firm
             "revenue grow"]                                              # S\T
    tickers = np.array(["AAA", "BBB", "CCC", "XOM", "XOM", "XOM", "AAA"], dtype=object)
    in_T = np.array([1, 1, 1, 1, 1, 1, 0], dtype=bool)
    X, feats = s_bigram_matrix(sents)
    nf = dict(zip(feats, firms_per_bigram(X, in_T, tickers)))
    assert nf["solar farm"] == 3 and nf["boiler plate"] == 1 and nf["revenue grow"] == 0
    ranked, _ = rank_from_matrix(X, feats, in_T, 3, 1.0, tickers=tickers, min_firms=3)
    kept = set(ranked.loc[ranked["source"] != "dropped", "bigram"])
    assert kept == {"solar farm"}
    off, _ = rank_from_matrix(X, feats, in_T, 3, 1.0, tickers=tickers, min_firms=0)
    assert {"solar farm", "boiler plate"} <= set(off.loc[off["source"] != "dropped", "bigram"])
    assert "n_firms_T" in off.columns
    with pytest.raises(ValueError):
        rank_counts(["a b"], [1], [0], 1, 1, 1, 1.0, min_firms=3)   # F needs firm counts


def test_filter_params_from_config():
    d = CFG["discovery"]
    assert d["rough_min_freq"] == 10 and d["n_min_freq"] == 2 and d["min_firms_in_T"] == 3
    assert filter_params(variant_cfg(CFG, CFG["discovery_variants"]["A"])) == (False, 0)
    assert filter_params(variant_cfg(CFG, CFG["discovery_variants"]["D"])) == (True, 3)
    assert set(CFG["discovery_variants"]) == {"S0", "A", "B", "C", "D", "B2", "C2", "D2"}


# ---- IPCC text cache -----------------------------------------------------------------------

def test_ipcc_cache_rebuilds_when_pdf_set_changes(tmp_path):
    pdf_dir = tmp_path / "ipcc"
    pdf_dir.mkdir()
    (pdf_dir / "a.pdf").write_bytes(b"x" * 10)
    cfg = {"paths": {"ipcc_dir": pdf_dir, "cache": tmp_path / "cache"}, "discovery": {"n_workers": 1}}
    calls = []

    def fake(paths, n_workers):
        calls.append(sorted(p.name for p in paths))
        return pd.DataFrame({"file": [p.name for p in paths], "page": 0, "text": "global warming"})

    load_ipcc_text(cfg, extractor=fake, verbose=False)
    load_ipcc_text(cfg, extractor=fake, verbose=False)            # reused
    assert len(calls) == 1
    (pdf_dir / "b.pdf").write_bytes(b"y" * 5)                      # file added
    df = load_ipcc_text(cfg, extractor=fake, verbose=False)
    assert calls[-1] == ["a.pdf", "b.pdf"] and len(df) == 2
    (pdf_dir / "a.pdf").write_bytes(b"x" * 11)                     # size changed
    load_ipcc_text(cfg, extractor=fake, verbose=False)
    (pdf_dir / "b.pdf").unlink()                                   # file removed
    load_ipcc_text(cfg, extractor=fake, verbose=False)
    assert len(calls) == 4
    man = json.loads((tmp_path / "cache" / "discovery" / "ipcc_manifest.json").read_text())
    assert man == {"schema": 2, "files": [{"name": "a.pdf", "size": 11}]}
    load_ipcc_text(cfg, extractor=fake, verbose=False, force=True)  # --force
    assert len(calls) == 5


# ---- evaluation helpers ------------------------------------------------------------------

def test_vocab_shift_and_best():
    sents = ["net zero goal", "net zero plan", "solar farm a", "solar farm b", "revenue grow"]
    X, feats = s_bigram_matrix(sents)
    in_T = np.array([1, 1, 1, 1, 0], dtype=bool)
    years = np.array([2022, 2023, 2015, 2022, 2010])
    shift, base = vocab_shift(X, feats, in_T, years, ["net zero", "solar farm"], 2021)
    s = shift.set_index("bigram")
    assert base == 0.75
    assert s.loc["net zero", "share_2021plus"] == 1.0 and s.loc["solar farm", "share_2021plus"] == 0.5
    assert top_shift(shift, 2021, 2)["bigram"].tolist() == ["net zero", "solar farm"]
    tab = pd.DataFrame({"variant": ["A", "B", "authors"], "pearson_official": [0.9, 0.8, 0.99],
                        "spearman_official": [0.5, 0.7, 0.99]})
    assert pick_best(tab) == "B" and pick_best(tab, "A") == "A"
    tab["n_discovered"] = [3000, 14, None]
    assert pick_best(tab, min_discovered=100) == "A"      # B too small for the human check
    assert pick_best(tab, min_discovered=10**6) == "B"    # nobody qualifies -> plain rule


# ---- variant A = the 2.4-2.5 prototype ------------------------------------------------------

def test_variant_a_reproduces_c_3408():
    from src.discovery.pipeline import cached_classify
    from src.discovery.rank import load_s_bigrams, rank_params
    from src.discovery.split import load_seeds
    vcfg = variant_cfg(CFG, CFG["discovery_variants"]["A"])
    vcfg["force"] = False
    cached = cached_classify(vcfg, "full", "all", verbose=False)
    if cached is None:
        pytest.skip("full-corpus variant A cache not built")
    R, S, scored = cached
    X, feats = load_s_bigrams(vcfg, S, verbose=False)
    min_t, top_pct = rank_params(vcfg)
    ranked, _ = rank_from_matrix(X, feats, scored["in_T"].to_numpy(), min_t, top_pct,
                                 exclude=candidate_exclusions(load_seeds(vcfg)))
    assert len(build_dictionary(ranked, load_seeds(vcfg))) == 3408


# ---- task 3.1b: cleaned rough library ---------------------------------------------------------

from src.discovery.rough_library import (_cached_sentences, drop_citation_lines,  # noqa: E402
                                         rough_cache_key, strip_digits, token_valid, unigram_freq,
                                         valid_words)
from src.discovery.variants import SEEDS_ONLY, add_seed_gain  # noqa: E402


def test_citation_and_digit_removal_on_toy_text():
    raw = ("Global warming of 1.5 degrees by 2030 harms coral reefs.\n"
           "Rogelj, J., D. Shindell, 2018: Mitigation pathways compatible with warming.\n"
           "See Smith et al. for carbon budgets\n"
           "doi:10.1038/nclimate3352 carbon budgets\n"
           "Carbon budgets shrink fast (2017)\n"
           "Global warming of 2 degrees by 2050 harms coral reefs.")
    text, n = drop_citation_lines(raw)
    assert n == 4
    assert "Rogelj" not in text and "doi" not in text and "carbon budget" not in text.lower()
    sents = lemmatize(text)
    assert strip_digits("co2 emission 2030 target") == "co2 emission target"   # "co2" stays
    from src.discovery.rough_library import bigram_freq
    raw_bi = bigram_freq(sents)
    clean_bi = bigram_freq([strip_digits(s) for s in sents])
    assert "1.5 degree" not in clean_bi and not any(any(t.isdigit() for t in b.split()) for b in clean_bi.index)
    assert any(any(t.isdigit() for t in b.split()) for b in raw_bi.index)       # digits were there
    assert clean_bi["degree harm"] == 2 and "degree harm" not in raw_bi  # removed BEFORE forming bigrams


def test_token_validity_filter_on_toy_text():
    n_uni = unigram_freq(lemmatize("Global warming is a problem. Coral reefs die. Energy prices rise."))
    t_uni = pd.Series({"rogelj": 1, "decarbonization": 7, "esaercni": 0})
    words = valid_words(n_uni, t_uni, min_transcript=5)
    assert {"global", "coral", "energy", "decarbonization"} <= words
    assert "rogelj" not in words and "esaercni" not in words
    cr = {"global warming", "rogelj austria", "esaercni egral", "energy decarbonization", "coral reef"}
    assert token_valid(cr, words) == {"global warming", "energy decarbonization", "coral reef"}


def test_clean_cache_key_changes_with_cleaning_settings(tmp_path):
    p = {"rough_min_freq": 10, "n_min_freq": 2, "n_corpora": ["brown"]}
    base = {"drop_citation_lines": True, "drop_digits": True, "token_validity": True,
            "min_transcript_count": 5}
    keys = {rough_cache_key("ipcc", p, base, "corpus")}
    for k, v in [("drop_citation_lines", False), ("drop_digits", False), ("token_validity", False),
                 ("min_transcript_count", 3)]:
        keys.add(rough_cache_key("ipcc", p, {**base, k: v}, "corpus"))
    keys.add(rough_cache_key("ipcc", {**p, "rough_min_freq": 5}, base, "corpus"))
    keys.add(rough_cache_key("ipcc", p, base, "other corpus"))
    assert len(keys) == 7
    assert rough_cache_key("ipcc", p, base, "x") == rough_cache_key("ipcc", p, dict(base), "x")
    # the M definition (and so the classify cache) follows the key
    from src.discovery.pipeline import m_definition
    on = variant_cfg(CFG, {"use_rough_library": True})
    assert m_definition(on, "k1") != m_definition(on, "k2")
    # the sentence cache rebuilds when its key changes
    calls = []

    def build():
        calls.append(1)
        return ["global warming"]
    path = tmp_path / "s.parquet"
    _cached_sentences(path, "k1", build, "toy", False)
    _cached_sentences(path, "k1", build, "toy", False)
    _cached_sentences(path, "k2", build, "toy", False)
    assert len(calls) == 2


def test_clean_library_has_own_m_cache_dir():
    from src.discovery.split import discovery_dir
    b = variant_cfg(CFG, CFG["discovery_variants"]["B"])
    b2 = variant_cfg(CFG, CFG["discovery_variants"]["B2"])
    a = variant_cfg(CFG, CFG["discovery_variants"]["A"])
    assert discovery_dir(b).name == "m_rough" and discovery_dir(b2).name == "m_rough_clean"
    assert discovery_dir(a).name == "discovery"


def test_seeds_only_row_and_gain():
    v = CFG["discovery_variants"]
    assert v[SEEDS_ONLY] == {"seeds_only": True}
    assert {"S0", "A", "B", "C", "D", "B2", "C2", "D2"} <= set(v)
    tab = pd.DataFrame({"variant": ["S0", "A", "B2", "authors"], "spearman_official": [0.6, 0.65, 0.7, 0.86],
                        "pearson_official": [0.9] * 4, "n_discovered": [0, 3000, 50, None]})
    t = add_seed_gain(tab).set_index("variant")
    assert t.loc["S0", "spearman_gain_vs_seeds"] == 0
    assert abs(t.loc["A", "spearman_gain_vs_seeds"] - 0.05) < 1e-12
    assert pick_best(add_seed_gain(tab), min_discovered=100) == "A"    # B2 too small, S0 never
    out = PIPELINE_DIR / "outputs" / "discovery_variants.csv"
    if out.exists():
        res = pd.read_csv(out)
        if "spearman_gain_vs_seeds" in res:
            assert "S0" in set(res["variant"])
            assert res.loc[res["variant"] == "S0", "C"].iloc[0] == 50


def test_pdf_extraction_resumes_from_parts(tmp_path, monkeypatch):
    import src.discovery.rough_library as rl
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"z" * 7)
    monkeypatch.setattr(rl, "_n_pages", lambda path: 25)
    calls = []

    def fake_range(path, a, b):
        calls.append((a, b))
        return [(i, f"page {i}") for i in range(a, b)]
    monkeypatch.setitem(rl.EXTRACTORS, "pdfplumber", fake_range)

    class InlinePool:  # run jobs in-process so the monkeypatch applies
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def submit(self, fn, *args):
            from concurrent.futures import Future
            f = Future(); f.set_result(fn(*args)); return f
    monkeypatch.setattr(rl, "ProcessPoolExecutor", InlinePool)
    parts = tmp_path / "parts"
    df = rl.extract_pdfs([pdf], 2, pages_per_job=10, parts_dir=parts)
    assert len(df) == 25 and calls == [(0, 10), (10, 20), (20, 25)]
    next(parts.glob("*00010_00020.parquet")).unlink()        # simulate an interrupted job
    calls.clear()
    df2 = rl.extract_pdfs([pdf], 2, pages_per_job=10, parts_dir=parts)
    assert calls == [(10, 20)]                                 # only the missing job re-runs
    assert df2["page"].tolist() == list(range(25))
