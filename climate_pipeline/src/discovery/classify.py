"""Discovery task 2.3: three classifiers R vs S -> P(R) for every S sentence -> target set T.

ROADMAP section 3, steps 4-5 (Internet Appendix I):
  * features: bigram counts from the shared cleaner (src.preprocess.make_vectorizer) with
    min_df = config discovery.min_df, and ALL seed bigrams removed (the label is defined by
    the seeds, so keeping them would leak the answer);
  * training set: all of R + min(s_train_size, |S|) random S sentences; label 1 = R, 0 = S;
  * classifiers: Multinomial NB, SVC, Random Forest (no grid search yet -> task 3.2;
    no class_weight, the paper does not mention one);
  * T = S sentences where max(P_nb, P_svc, P_rf) > discovery.t_threshold.

PROTOTYPE: M = all sentences, no rough library (see split.py).

Note: as in the paper, the S sentences used for training are also scored. On a small sample
(|S| < s_train_size) that is ALL of S, so P(R) is in-sample for every S sentence (RF in
particular memorises its training rows). Column `in_train` records this.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

from src.discovery.split import PROTOTYPE_NOTE, discovery_dir, load_seeds
from src.preprocess import make_vectorizer

MODELS = ("nb", "svc", "rf")


def build_vectorizer(train_sentences: list[str], seeds, min_df: int | float):
    """Fit the shared vectorizer with min_df on the training sentences, then drop every seed.

    Returns a vectorizer with a fixed vocabulary (same tokenization as scoring).
    """
    full = make_vectorizer(min_df=min_df).fit(train_sentences)
    seedset = set(seeds)
    vocab = [f for f in full.get_feature_names_out() if f not in seedset]
    if not vocab:
        raise ValueError("no features left after min_df and seed removal")
    return make_vectorizer(vocabulary=vocab).fit(train_sentences[:1])


def make_models(seed: int) -> dict:
    return {
        "nb": MultinomialNB(),
        # DEVIATION: the paper uses SVC; a kernel SVC with probability=True is far too slow on
        # sparse text with ~10^5 rows, so we use LinearSVC and get probabilities from
        # CalibratedClassifierCV(cv=3) (Platt scaling over 3 folds).
        "svc": CalibratedClassifierCV(LinearSVC(random_state=seed), cv=3),
        "rf": RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=seed),
    }


def train_test_split_rs(R: pd.DataFrame, S: pd.DataFrame, s_train_size: int, seed: int):
    """Training frame (R + random S sample) with label column y, plus a boolean in-train mask for S."""
    n = min(int(s_train_size), len(S))
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(len(S), size=n, replace=False))
    in_train = np.zeros(len(S), dtype=bool)
    in_train[idx] = True
    train = pd.concat([R.assign(y=1), S.iloc[idx].assign(y=0)], ignore_index=True)
    return train, in_train


def fit_models(X, y, seed: int, verbose: bool = True) -> dict:
    models = make_models(seed)
    for name, m in models.items():
        t0 = time.perf_counter()
        m.fit(X, y)
        if verbose:
            print(f"[discover]   fitted {name:<3s} in {time.perf_counter() - t0:6.1f}s")
    return models


def predict_s(S_sentences: list[str], vec, models: dict, chunk_size: int) -> pd.DataFrame:
    """P(R) from each model for every S sentence, transformed and predicted in chunks."""
    parts = []
    for start in range(0, len(S_sentences), chunk_size):
        X = vec.transform(S_sentences[start:start + chunk_size])
        parts.append(pd.DataFrame({f"p_{k}": m.predict_proba(X)[:, list(m.classes_).index(1)]
                                   for k, m in models.items()}))
    if not parts:
        return pd.DataFrame(columns=[f"p_{k}" for k in models])
    return pd.concat(parts, ignore_index=True)


def add_target(probs: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """p_max = row max over the p_* columns; in_T = p_max > threshold (strict, as in the paper)."""
    out = probs.copy()
    out["p_max"] = out[[f"p_{k}" for k in MODELS]].max(axis=1)
    out["in_T"] = out["p_max"] > threshold
    return out


def classify(R: pd.DataFrame, S: pd.DataFrame, seeds, min_df, s_train_size: int, threshold: float,
             seed: int, chunk_size: int, verbose: bool = True):
    """Pure core of task 2.3. Returns (S_scored, vectorizer)."""
    train, in_train = train_test_split_rs(R, S, s_train_size, seed)
    vec = build_vectorizer(train["sentence"].tolist(), seeds, min_df)
    X = vec.transform(train["sentence"].tolist())
    if verbose:
        print(f"[discover]   training set: {len(train):,} sentences ({int(train['y'].sum()):,} R + "
              f"{int((train['y'] == 0).sum()):,} S), {X.shape[1]:,} features "
              f"(min_df={min_df}, seeds removed)")
    models = fit_models(X, train["y"].to_numpy(), seed, verbose)
    probs = predict_s(S["sentence"].tolist(), vec, models, chunk_size)
    scored = add_target(probs, threshold)
    scored.insert(0, "file", S["file"].to_numpy())
    scored.insert(1, "sentence_id", S["sentence_id"].to_numpy())
    scored["in_train"] = in_train
    return scored, vec


def run_classify(cfg: dict, R: pd.DataFrame, S: pd.DataFrame) -> pd.DataFrame:
    """Task 2.3 stage wrapper: classify, save cache/discovery/S_scored.parquet, print summary."""
    d = cfg["discovery"]
    seed = cfg["settings"]["sample_seed"]
    thr = float(d["t_threshold"])
    print(f"[discover] task 2.3: NB + SVC(LinearSVC+calibration, DEVIATION) + RF ({PROTOTYPE_NOTE})")
    scored, _ = classify(R, S, load_seeds(cfg), d["min_df"], d["s_train_size"], thr, seed,
                         cfg["settings"]["chunk_size"])

    out = discovery_dir(cfg) / "S_scored.parquet"
    scored.to_parquet(out, index=False)

    T = scored[scored["in_T"]]
    print(f"[discover] |T| = {len(T):,} of |S| = {len(S):,} ({len(T) / max(len(S), 1):.2%}) "
          f"with p_max > {thr} -> {out}")
    print("[discover] |T| per classifier: " + "  ".join(
        f"{k}={int((scored[f'p_{k}'] > thr).sum()):,}" for k in MODELS))
    print(f"[discover] S sentences used in training: {int(scored['in_train'].sum()):,} "
          f"(T among them: {int(T['in_train'].sum()):,}; P(R) is in-sample for these)")
    q = scored["p_max"].quantile([0.5, 0.9, 0.99, 0.999])
    print("[discover] p_max quantiles: " + "  ".join(f"{int(round(p * 1000)) / 10:g}%={v:.4f}"
                                                   for p, v in q.items()))

    n_ex = min(15, len(T))
    if n_ex:
        ex = T.sample(n=n_ex, random_state=seed).merge(S, on=["file", "sentence_id"], how="left")
        print(f"[discover] {n_ex} random example sentences from T (lemmatized):")
        for i, r in enumerate(ex.itertuples(index=False), 1):
            txt = r.sentence if len(r.sentence) <= 220 else r.sentence[:217] + "..."
            print(f"  {i:>2}. [{r.file} | nb={r.p_nb:.2f} svc={r.p_svc:.2f} rf={r.p_rf:.2f}] {txt}")
    return scored
