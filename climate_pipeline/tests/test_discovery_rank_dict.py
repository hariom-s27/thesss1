"""Tasks 2.4-2.7: King ranking, discovered dictionary, evaluation, compare_dicts."""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

from run import load_config  # noqa: E402
from src.discovery.build_dict import build_dictionary, discovered_table  # noqa: E402
from src.discovery.evaluate import (precision_at_k, ranked_discovered, reachable_recall,  # noqa: E402
                                    t_quality, t_rules)
from src.discovery.rank import king_score, rank_counts, rank_from_matrix, s_bigram_matrix  # noqa: E402
from src.discovery.split import load_seeds  # noqa: E402
from src.scoring import load_dictionaries  # noqa: E402
from src.validation.compare_dicts import compare_dicts  # noqa: E402

CFG = load_config(PIPELINE_DIR / "config.yaml")


# ---- 2.4: King score -------------------------------------------------------------------

def test_king_concentrated_beats_even():
    N_T, N_ST = 1_000, 50_000
    # same total (100 sentences): concentrated in T vs spread in proportion to set sizes
    conc = king_score(80, 20, N_T, N_ST)
    even = king_score(2, 98, N_T, N_ST)  # 2/1000 ~ 98/50000
    assert conc > even


def test_king_finite_for_large_counts():
    s = king_score(np.array([5_000_000, 0, 10_000_000]), np.array([40_000_000, 1, 0]),
                   10_000_000, 90_000_000)
    assert np.all(np.isfinite(s))


def test_king_t_only_increasing_in_n_kT():
    s = king_score(np.arange(1, 200), np.zeros(199), 10_000, 600_000)
    assert np.all(np.diff(s) > 0)


# ---- 2.4: rules ------------------------------------------------------------------------

def test_t_only_threshold_and_proportion_rule():
    N_T, N_ST = 100, 10_000
    ranked = rank_counts(
        ["t only many", "t only few", "shared prop wins", "shared raw wins prop loses", "st only",
         "carbon tax"],
        n_kT=[5, 2, 10, 50, 0, 9], n_kST=[0, 0, 20, 6_000, 30, 0],
        N_T=N_T, N_ST=N_ST, min_t_only_df=3, top_pct=1.0, exclude=["carbon tax"])
    src = dict(zip(ranked["bigram"], ranked["source"]))
    assert "carbon tax" not in src                      # seeds excluded
    assert src["t only many"] == "t_only"               # n_kT 5 >= 3
    assert src["t only few"] == "dropped"               # n_kT 2 < 3
    assert src["shared prop wins"] == "top_pct"         # 10% > 0.2% (raw 10 < 20)
    assert src["shared raw wins prop loses"] == "dropped"  # raw 50 < 6000; 50% < 60%
    assert src["st only"] == "dropped"
    assert list(ranked.columns) == ["bigram", "n_kT", "n_kST", "prop_T", "prop_ST", "king_score", "source"]


def test_top_pct_keeps_best_king():
    names = [f"b{i}" for i in range(20)]
    n_kT = np.arange(1, 21)                              # all pass prop rule (n_kST = 1)
    ranked = rank_counts(names, n_kT, np.ones(20), 1_000, 100_000, 3, 0.10)
    top = ranked.loc[ranked["source"] == "top_pct", "bigram"].tolist()
    assert sorted(top) == ["b18", "b19"]                 # ceil(10% of 20) = 2, highest n_kT


def test_rank_from_matrix_counts_sentences():
    sents = ["solar panel install", "solar panel cost", "revenue grow strong", "revenue grow solar panel"]
    X, feats = s_bigram_matrix(sents)
    ranked, info = rank_from_matrix(X, feats, np.array([True, True, False, False]), 1, 1.0)
    row = ranked.set_index("bigram").loc["solar panel"]
    assert (row["n_kT"], row["n_kST"]) == (2, 1)
    assert (info["N_T"], info["N_ST"]) == (2, 2)
    assert X.max() == 1                                  # binary: df, not counts


# ---- 2.5: dictionary -------------------------------------------------------------------

def _toy_ranked():
    return pd.DataFrame({"bigram": ["solar farm", "wind turbine", "revenue grow", "nextera energy"],
                         "n_kT": [10, 8, 3, 5], "n_kST": [0, 2, 300, 0],
                         "prop_T": 0.0, "prop_ST": 0.0, "king_score": [-1.0, -2.0, -50.0, -3.0],
                         "source": ["t_only", "top_pct", "dropped", "t_only"]})


def test_build_dict_is_set_with_all_seeds(tmp_path):
    seeds = load_seeds(CFG)
    C = build_dictionary(_toy_ranked(), seeds)
    assert isinstance(C, set) and set(seeds) <= C
    assert {"solar farm", "wind turbine", "nextera energy"} <= C and "revenue grow" not in C
    assert len(C) == len(seeds) + 3
    tab = discovered_table(_toy_ranked(), seeds, {"solar farm", "climate change"})
    assert len(tab) == len(C) and (tab["source"] == "seed").sum() == 50
    assert tab.set_index("bigram").loc["solar farm", "in_authors"]
    p = tmp_path / "C.pkl"
    p.write_bytes(pickle.dumps(C))
    assert pickle.loads(p.read_bytes()) == C


# ---- 2.6: evaluation -------------------------------------------------------------------

def test_precision_recall_tquality():
    disc = ranked_discovered(_toy_ranked(), ["climate change"])["bigram"].tolist()
    assert disc == ["solar farm", "wind turbine", "nextera energy"]
    p = precision_at_k(disc, {"solar farm", "wind turbine"}, ks=(1, 2, None))
    assert p[1] == 1.0 and p[2] == 1.0 and abs(p["all"] - 2 / 3) < 1e-12

    rr = reachable_recall(authors={"solar farm", "sea level", "never seen", "climate change"},
                          corpus_vocab={"solar farm", "sea level", "climate change", "revenue grow"},
                          s_vocab={"solar farm", "sea level"},
                          C={"solar farm", "climate change"}, seeds={"climate change"})
    assert rr["n_reachable"] == 3 and rr["n_found"] == 2
    assert abs(rr["recall"] - 2 / 3) < 1e-12 and rr["recall_ex_seeds"] == 0.5 and rr["recall_S"] == 0.5

    X, feats = s_bigram_matrix(["solar farm big", "solar farm grow", "revenue grow", "cost fall", "margin up"])
    tq = t_quality(X, feats, np.array([True, True, False, False, False]), {"solar farm"})
    assert tq["rate_T"] == 1.0 and tq["rate_ST"] == 0.0


def test_t_rules():
    scored = pd.DataFrame({"p_nb": [0.85, 0.95, 0.85, 0.1], "p_svc": [0.1, 0.1, 0.81, 0.1],
                           "p_rf": [0.1, 0.1, 0.1, 0.1]})
    r = list(t_rules(scored).values())
    assert r[0].tolist() == [True, True, True, False]    # any > 0.8 (default)
    assert r[1].tolist() == [False, True, False, False]  # any > 0.9
    assert r[2].tolist() == [False, False, True, False]  # >= 2 of 3 > 0.8


# ---- 2.7: scoring with the discovered dictionary + compare_dicts -----------------------

def test_compare_dicts_tiny_fake():
    rows = []
    texts = {("AAA", 2020): ["solar farm grow", "revenue grow strong"],
             ("AAA", 2021): ["climate change risk", "solar farm wind turbine"],
             ("BBB", 2020): ["revenue grow strong", "cost fall fast"],
             ("BBB", 2021): ["wind turbine order", "climate change matter"]}
    for (tk, yr), sents in texts.items():
        for q in (1, 2):
            for j, s in enumerate(sents):
                rows.append({"file": f"{tk}_{yr}_Q{q}.txt", "ticker": tk, "year": yr, "quarter": q,
                             "sentence_id": j, "sentence": s})
    sent_df = pd.DataFrame(rows)
    isin = {"AAA": "US0000000001", "BBB": "US0000000002"}
    official = pd.DataFrame({"isin": ["US0000000001"] * 2 + ["US0000000002"] * 2,
                             "year": [2020, 2021, 2020, 2021], "cc_expo_ew": [0.1, 0.3, 0.0, 0.2]})
    fy, corr = compare_dicts(sent_df, {"solar farm", "wind turbine", "climate change"},
                             {"climate change", "solar farm"}, isin, official)
    assert len(fy) == 4 and fy["cc_expo_ew"].notna().all()
    a = fy.set_index(["ticker", "year"])
    assert a.loc[("AAA", 2020), "cc_expo_disc"] == 1 / 4   # 1 of 4 bigrams
    assert a.loc[("BBB", 2021), "cc_expo_disc"] == 2 / 4
    assert a.loc[("BBB", 2021), "cc_expo_auth"] == 1 / 4
    assert list(corr["pair"]) == ["discovered vs authors (all firm-years)",
                                  "discovered vs authors (matched official)",
                                  "discovered vs official", "authors vs official"]
    assert (corr["n"] == 4).all() and corr["pearson"].notna().all()


def test_load_dictionaries_discovered(tmp_path):
    cfg = {**CFG, "paths": {**CFG["paths"], "cache": tmp_path},
           "settings": {**CFG["settings"], "dictionary": "discovered"}}
    (tmp_path / "discovery").mkdir()
    (tmp_path / "discovery" / "C_discovered.pkl").write_bytes(pickle.dumps({"Solar Farm", "climate change"}))
    d = load_dictionaries(cfg, verbose=False)
    auth = load_dictionaries(cfg, verbose=False, which="authors")
    assert d["cc"] == frozenset({"solar farm", "climate change"})
    assert d["op"] == auth["op"] and d["rg"] == auth["rg"] and d["ph"] == auth["ph"]
