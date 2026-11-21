import sys
from pathlib import Path

import numpy as np
import pandas as pd

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

from run import load_config  # noqa: E402
from src.discovery.classify import add_target, build_vectorizer, classify  # noqa: E402
from src.discovery.split import load_seeds, split_rs  # noqa: E402

CFG = load_config(PIPELINE_DIR / "config.yaml")


def _df(sentences):
    return pd.DataFrame({"file": "toy.txt", "sentence_id": range(len(sentences)), "sentence": sentences})


# ---- task 2.1: config ---------------------------------------------------------------

def test_seeds_in_config():
    seeds = load_seeds(CFG)
    assert len(seeds) == 50 and len(set(seeds)) == 50
    for typo in ("exterme weather", "costal region", "global warm"):  # published typos kept
        assert typo in seeds
    ts = CFG["topic_seeds"]
    assert (len(ts["opp"]), len(ts["reg"]), len(ts["phy"])) == (18, 19, 14)
    d = CFG["discovery"]
    assert d["min_df"] == 3 and d["s_train_size"] == 100000 and d["t_threshold"] == 0.8


# ---- task 2.2: split ----------------------------------------------------------------

def test_toy_split():
    seeds = ["carbon tax", "sea level"]
    sents = ["the carbon tax will rise next year",   # R
             "revenue grow in the quarter",           # S
             "sea level rise threaten plant",         # R
             "carbon emission fall",                  # S: "carbon emission" is not a seed here
             "tax carbon",                            # S: wrong order, not the bigram
             "we see a carbon and tax issue"]         # R: stop words removed -> "carbon tax"
    R, S, counts = split_rs(_df(sents), seeds)
    assert R["sentence_id"].tolist() == [0, 2, 5]
    assert S["sentence_id"].tolist() == [1, 3, 4]
    assert len(R) + len(S) == len(sents)
    assert counts["carbon tax"] == 2 and counts["sea level"] == 1
    assert list(R.columns) == ["file", "sentence_id", "sentence"]


def test_bigrams_never_cross_sentences():
    R, S, _ = split_rs(_df(["we pay carbon", "tax be high"]), ["carbon tax"])
    assert len(R) == 0 and len(S) == 2


# ---- task 2.3: features and classifier ----------------------------------------------

def test_seeds_absent_from_features():
    seeds = load_seeds(CFG)
    train = ["climate change risk grow", "climate change risk grow", "climate change risk grow",
             "renewable energy project expand", "renewable energy project expand",
             "renewable energy project expand", "strong quarter sale"]
    vec = build_vectorizer(train, seeds, min_df=1)
    vocab = set(vec.get_feature_names_out())
    assert not vocab & set(seeds)
    assert {"change risk", "energy project", "quarter sale"} <= vocab
    # min_df prunes rare bigrams
    vocab3 = set(build_vectorizer(train, seeds, min_df=3).get_feature_names_out())
    assert "quarter sale" not in vocab3 and "change risk" in vocab3


def test_threshold_logic():
    p = pd.DataFrame({"p_nb": [0.1, 0.85, 0.8, 0.2], "p_svc": [0.2, 0.1, 0.5, 0.9],
                      "p_rf": [0.3, 0.1, 0.79, 0.1]})
    out = add_target(p, 0.8)
    assert np.allclose(out["p_max"], [0.3, 0.85, 0.8, 0.9])
    assert out["in_T"].tolist() == [False, True, False, True]  # strict ">": 0.8 is out


def test_toy_classifier_run():
    seeds = ["climate change", "carbon emission", "renewable energy"]
    climate_r = ["climate change pose physical risk to our coastal facility",
                 "we cut carbon emission at every refinery site",
                 "renewable energy capacity drive carbon emission reduction target",
                 "climate change policy affect our emission reduction target",
                 "carbon emission reduction target support decarbonization plan",
                 "renewable energy and decarbonization plan lower physical risk",
                 "climate change raise physical risk for coastal facility",
                 "carbon emission from refinery site fall under reduction target",
                 "renewable energy investment support decarbonization plan",
                 "climate change and decarbonization plan shape capital allocation",
                 "carbon emission disclosure cover physical risk and reduction target",
                 "renewable energy contract cut emission at refinery site"]
    climate_s = ["our decarbonization plan set a new emission reduction target",
                 "physical risk to coastal facility remain a key concern",
                 "emission reduction target and decarbonization plan be on track",
                 "the refinery site emission reduction target be ambitious"]
    other_s = ["revenue grow strongly in the quarter thanks to pricing",
               "free cash flow improve and we return capital to shareholder",
               "operating margin expand on cost discipline in the quarter",
               "we raise full year guidance for earning per share",
               "inventory level normalize and working capital improve",
               "the board approve a new share repurchase program",
               "same store sale grow mid single digit in the quarter",
               "we expect interest expense to decline next year",
               "customer demand remain healthy across every region",
               "gross margin benefit from favorable product mix",
               "we close the acquisition earlier than expect",
               "headcount stay flat while revenue grow",
               "pricing action offset cost inflation in the quarter",
               "our balance sheet remain strong with low leverage",
               "we see solid order backlog entering next year",
               "capital expenditure guidance remain unchanged for the year",
               "earning per share beat consensus in the quarter",
               "we repay debt and return capital to shareholder",
               "demand for our product stay strong in every region",
               "operating cash flow reach a record level this quarter",
               "foreign exchange be a headwind to revenue growth",
               "we expect margin to expand next year on pricing",
               "the dividend increase reflect confidence in cash flow",
               "subscription revenue grow faster than expect"]
    sents = _df(climate_r + climate_s + other_s)
    R, S, _ = split_rs(sents, seeds)
    assert len(R) == len(climate_r) and len(S) == len(climate_s) + len(other_s)

    thr = 0.5
    scored, vec = classify(R, S, seeds, min_df=1, s_train_size=1000, threshold=thr, seed=0,
                           chunk_size=7, verbose=False)
    assert not set(vec.get_feature_names_out()) & set(seeds)
    assert len(scored) == len(S)
    assert scored["sentence_id"].tolist() == S["sentence_id"].tolist()   # chunks keep order
    assert scored["in_train"].all()                                      # |S| < s_train_size
    for c in ("p_nb", "p_svc", "p_rf", "p_max"):
        assert scored[c].between(0, 1).all()
    assert (scored["p_max"] == scored[["p_nb", "p_svc", "p_rf"]].max(axis=1)).all()
    assert (scored["in_T"] == (scored["p_max"] > thr)).all()
    # T subset of S
    T_ids = set(scored.loc[scored["in_T"], "sentence_id"])
    assert T_ids <= set(S["sentence_id"]) and not T_ids & set(R["sentence_id"])
    # climate-flavoured S sentences score higher than generic finance talk
    p = scored.set_index("sentence_id")["p_max"]
    clim_ids = S.loc[S["sentence"].isin(climate_s), "sentence_id"]
    other_ids = S.loc[S["sentence"].isin(other_s), "sentence_id"]
    assert p[clim_ids].mean() > p[other_ids].mean()


def test_train_sample_size_respected():
    R = _df(["climate change risk"] * 5)
    S = _df([f"revenue grow {i}" for i in range(20)])
    from src.discovery.classify import train_test_split_rs
    train, in_train = train_test_split_rs(R, S, s_train_size=8, seed=1)
    assert len(train) == 13 and int(train["y"].sum()) == 5 and in_train.sum() == 8
