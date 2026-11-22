"""Full-corpus discovery evaluation + dictionary drift (src/validation/full_eval.py, drift.py)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.presentation import bootstrap_spearman
from src.scoring import score_transcript
from src.validation.drift import drift_table, new_terms, pick_variant, transcript_table
from src.validation.full_eval import (FULL_VARIANTS, bootstrap_corrs, cc_expo, dict_hits,
                                      transcript_matrix)

OUT = Path(__file__).resolve().parents[1] / "outputs"

SENTS = pd.DataFrame({
    "file": ["a.txt"] * 3 + ["b.txt"] * 2,
    "ticker": ["XOM"] * 3 + ["NEE"] * 2,
    "year": [2019] * 3 + [2022] * 2,
    "quarter": [1] * 5,
    "sentence_id": [0, 1, 2, 0, 1],
    "sentence": ["we cut greenhouse gas emission", "climate change matter",
                 "net zero by 2050 net zero", "energy transition and net zero target",
                 "renewable energy grow fast"],
})


def test_transcript_matrix_matches_score_transcript():
    X, feats, meta = transcript_matrix(SENTS)
    d = frozenset({"greenhouse gas", "climate change", "net zero", "renewable energy"})
    ours = cc_expo(dict_hits(X, feats, d), meta["B"].to_numpy())
    for i, (f, g) in enumerate(SENTS.groupby("file", sort=True)):
        r = score_transcript(g["sentence"].tolist(), {"cc": d})
        assert meta["file"].iloc[i] == f
        assert meta["B"].iloc[i] == r["B"]
        assert ours[i] == pytest.approx(r["cc_expo"])
    assert dict_hits(X, feats, {"not there"}).sum() == 0


def test_new_terms_exclude_authors_and_apply_filters():
    disc = pd.DataFrame({"bigram": ["net zero", "climate change", "energy transition", "john smith",
                                    "rare term"],
                         "source": ["t_only"] * 5, "n_kT": [50, 80, 30, 40, 5],
                         "n_kST": [0] * 5, "n_firms_T": [10, 12, 8, 1, 6]})
    authors = {"climate change", "greenhouse gas"}
    nt = new_terms(disc, authors, min_firms=3, min_nkT=10)
    assert list(nt["bigram"]) == ["net zero", "energy transition"]
    assert not set(nt["bigram"]) & authors


def test_new_terms_on_real_output_exclude_authors():
    p = OUT / "new_terms.csv"
    if not p.exists():
        pytest.skip("run --stage drift first")
    from run import load_config
    from src.scoring import load_dictionaries
    cfg = load_config(Path(__file__).resolve().parents[1] / "config.yaml")
    authors = load_dictionaries(cfg, verbose=False, which="authors")["cc"]
    nt = pd.read_csv(p)
    assert len(nt) > 0
    assert not set(nt["bigram"]) & set(authors)
    assert (nt["n_kT"] >= 10).all() and (nt["n_firms_T"] >= 3).all()


def test_union_scoring_ge_authors_for_every_transcript():
    X, feats, meta = transcript_matrix(SENTS)
    authors = {"greenhouse gas", "climate change"}
    new = {"net zero", "energy transition"}
    ha, hn = dict_hits(X, feats, authors), dict_hits(X, feats, new)
    t = transcript_table(meta, ha, hn, {"XOM": "X1", "NEE": "N1"})
    assert (t["cc_expo_union"] >= t["cc_expo_authors"]).all()
    # union = authors + new (disjoint), checked against a direct union scoring
    hu = dict_hits(X, feats, authors | new)
    assert np.array_equal(hu, ha + hn)
    assert t.loc[t["file"] == "b.txt", "hits_new"].iloc[0] == 2
    tab = drift_table(t)
    per = tab[tab["breakdown"] == "period"].set_index("group")
    assert per.loc["2021+", "share_new_hits"] == 1.0          # b.txt: only new-term hits
    assert per.loc["pre-2021", "share_new_hits"] == pytest.approx(2 / 4)
    assert set(tab.loc[tab["breakdown"] == "sector", "group"]) == {"oil & gas", "utilities"}


def test_union_ge_authors_on_real_drift_output():
    p = OUT / "dictionary_drift.csv"
    if not p.exists():
        pytest.skip("run --stage drift first")
    d = pd.read_csv(p)
    assert (d["mean_cc_expo_union"] >= d["mean_cc_expo_authors"] - 1e-15).all()
    assert (d["hits_new"] >= 0).all()
    years = d.loc[d["breakdown"] == "year", "group"].astype(int)
    assert years.min() >= 2005 and years.max() <= 2026


def test_bootstrap_corrs_spearman_equals_bootstrap_spearman():
    rng = np.random.default_rng(0)
    y = rng.normal(size=60)
    df = pd.DataFrame({"off": y, "S0": y + rng.normal(scale=2, size=60),
                       "A": y + rng.normal(scale=0.3, size=60)})
    t = bootstrap_corrs(df, ["S0", "A"], "off", "S0", n_boot=200, seed=3)
    ref, _ = bootstrap_spearman(df, ["S0", "A"], "off", "S0", n_boot=200, seed=3)
    np.testing.assert_allclose(t["spearman_ci_lo"], ref["spearman_ci_lo"])
    np.testing.assert_allclose(t["spearman_gain_ci_lo"], ref["gain_ci_lo"])
    assert t.set_index("variant").loc["A", "pearson"] == pytest.approx(df["A"].corr(df["off"]))
    assert (t["pearson_ci_lo"] <= t["pearson"]).all() and (t["pearson"] <= t["pearson_ci_hi"]).all()


def test_full_bootstrap_table_one_row_per_variant():
    p = OUT / "presentation" / "bootstrap_gains_full.csv"
    if not p.exists():
        pytest.skip("run --stage discover_variants_full first")
    b = pd.read_csv(p)
    assert list(b["variant"]) == FULL_VARIANTS
    assert b["variant"].is_unique
    assert (b["n"] == b["n"].iloc[0]).all()
    # authors on the full corpus = compare_official_full.csv cc_expo
    c = pd.read_csv(OUT / "compare_official_full.csv").set_index("measure").loc["cc_expo"]
    a = b.set_index("variant").loc["authors"]
    assert int(a["n"]) == int(c["n"])
    assert a["spearman"] == pytest.approx(c["spearman"], abs=1e-9)
    assert a["pearson"] == pytest.approx(c["pearson"], abs=1e-9)


def test_pick_variant_respects_min_discovered():
    dv = pd.DataFrame({"variant": ["S0", "A", "C2", "D2", "authors"],
                       "n_discovered": [0, 3358, 667, 56, np.nan],
                       "spearman_gain_vs_seeds": [0, 0.01, 0.05, 0.10, 0.2]})
    assert pick_variant(dv, 100) == "C2"
    assert pick_variant(dv, 0) == "D2"


def test_drift_title_follows_data():
    from src.validation.drift import drift_title
    assert "STABLE" in drift_title(0.444, 0.472, 103, "C2")
    assert "growing" in drift_title(0.20, 0.40, 103, "C2")
    assert "shrinking" in drift_title(0.40, 0.20, 103, "C2")


def test_update_summary_inserts_once_before_deviations(tmp_path):
    from src.validation.drift import SUMMARY_HEAD, update_summary
    p = tmp_path / "results_summary.md"
    p.write_text("# T\n\n**Vocabulary shift.** x\n\n**Deviations from the paper.**\n- a\n", encoding="utf-8")
    update_summary(p, f"{SUMMARY_HEAD} first.\n")
    update_summary(p, f"{SUMMARY_HEAD} second.\n")
    txt = p.read_text(encoding="utf-8")
    assert txt.count(SUMMARY_HEAD) == 1 and "second" in txt and "first" not in txt
    assert txt.index(SUMMARY_HEAD) < txt.index("**Deviations")
