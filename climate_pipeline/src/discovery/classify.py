"""Discovery task 2.3: three classifiers R vs S -> P(R) for every S sentence -> target set T.

ROADMAP section 3, steps 4-5 (Internet Appendix I):
  * features: bigram counts from the shared cleaner (src.preprocess.make_vectorizer) with
    min_df = config discovery.min_df, and ALL seed bigrams removed (the label is defined by
    the seeds, so keeping them would leak the answer);
  * training set: all of R + S_train, a random S sample of size
    min(round(s_train_ratio * |R|), |S|, s_train_max). The paper trains on R (~60k) + 100k
    of S, i.e. R ~ 37.5% of the training set; the 100k is a corpus-size artefact, so we keep
    the RATIO (1 : 1.667), not the absolute number. Label 1 = R, 0 = S;
  * classifiers: Multinomial NB, SVC, Random Forest (no grid search yet -> task 3.2;
    no class_weight, the paper does not mention one);
  * scoring without in-sample bias: S sentences NOT in S_train are scored by the models fitted
    on the whole training set; S sentences IN S_train are scored out-of-fold
    (cross_val_predict, k = discovery.oof_folds), so no sentence is scored by a model that saw it;
  * T = S sentences where max(P_nb, P_svc, P_rf) > discovery.t_threshold.

M = all sentences (prototype) or the rough-library sentences (task 3.1), see split.py.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

from src.discovery.split import discovery_dir, load_seeds, m_note
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


def make_model(name: str, seed: int):
    if name == "nb":
        return MultinomialNB()
    if name == "svc":
        # DEVIATION: the paper uses SVC; a kernel SVC with probability=True is far too slow on
        # sparse text, so we use LinearSVC and get probabilities from
        # CalibratedClassifierCV(cv=3) (Platt scaling over 3 folds).
        return CalibratedClassifierCV(LinearSVC(random_state=seed), cv=3)
    if name == "rf":
        return RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=seed)
    raise ValueError(name)


def s_train_size(n_r: int, n_s: int, ratio: float, max_n: int) -> int:
    """|S_train| = min(round(ratio * |R|), |S|, max_n)."""
    return int(min(round(ratio * n_r), n_s, max_n))


def train_test_split_rs(R: pd.DataFrame, S: pd.DataFrame, n_s_train: int, seed: int):
    """Training frame (all R, then S_train in S order) with label y, plus boolean in-train mask for S."""
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(len(S), size=n_s_train, replace=False))
    in_train = np.zeros(len(S), dtype=bool)
    in_train[idx] = True
    train = pd.concat([R.assign(y=1), S.iloc[idx].assign(y=0)], ignore_index=True)
    return train, in_train


def _p_r(model, X) -> np.ndarray:
    return model.predict_proba(X)[:, list(model.classes_).index(1)]


def score_s(S_sentences: list[str], in_train: np.ndarray, X_train, y_train: np.ndarray, vec,
            seed: int, folds: int, chunk_size: int, verbose: bool = True):
    """P(R) from each model for every S sentence.

    Rows of X_train are R first, then the S_train sentences in S order (as built by
    train_test_split_rs). In-train S rows get out-of-fold probabilities; the rest are scored
    in chunks by the model fitted on the whole training set. Returns (probs DataFrame, seconds per model).
    """
    n_r = int(y_train.sum())
    min_class = int(min(n_r, len(y_train) - n_r))
    if min_class < folds:
        raise ValueError(f"need >= {folds} sentences per class for {folds}-fold OOF, have {min_class}")
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    out_idx = np.flatnonzero(~in_train)
    probs, secs = {}, {}
    for name in MODELS:
        t0 = time.perf_counter()
        p = np.empty(len(S_sentences))
        oof = cross_val_predict(make_model(name, seed), X_train, y_train, cv=cv, method="predict_proba")
        p[in_train] = oof[n_r:, 1]          # classes sorted [0, 1] -> column 1 = P(R)
        model = make_model(name, seed).fit(X_train, y_train)
        for start in range(0, len(out_idx), chunk_size):
            rows = out_idx[start:start + chunk_size]
            p[rows] = _p_r(model, vec.transform([S_sentences[i] for i in rows]))
        probs[f"p_{name}"] = p
        secs[name] = time.perf_counter() - t0
        if verbose:
            print(f"[discover]   {name:<3s} fit + {folds}-fold OOF + predict {len(out_idx):,} "
                  f"out-of-train S: {secs[name]:7.1f}s")
    return pd.DataFrame(probs), secs


def add_target(probs: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """p_max = row max over the p_* columns; in_T = p_max > threshold (strict, as in the paper)."""
    out = probs.copy()
    out["p_max"] = out[[f"p_{k}" for k in MODELS]].max(axis=1)
    out["in_T"] = out["p_max"] > threshold
    return out


def classify(R: pd.DataFrame, S: pd.DataFrame, seeds, min_df, ratio: float, s_max: int,
             threshold: float, seed: int, chunk_size: int, folds: int, verbose: bool = True):
    """Pure core of task 2.3. Returns (S_scored, vectorizer, info)."""
    n_st = s_train_size(len(R), len(S), ratio, s_max)
    train, in_train = train_test_split_rs(R, S, n_st, seed)
    vec = build_vectorizer(train["sentence"].tolist(), seeds, min_df)
    X = vec.transform(train["sentence"].tolist())
    y = train["y"].to_numpy()
    info = {"n_train": len(train), "n_r": len(R), "n_s_train": n_st,
            "r_share_train": len(R) / max(len(train), 1), "n_features": X.shape[1]}
    if verbose:
        print(f"[discover]   training set: {len(train):,} sentences = {len(R):,} R + {n_st:,} S_train "
              f"(R share {info['r_share_train']:.1%}; ratio {ratio} x |R|, max {s_max:,}), "
              f"{X.shape[1]:,} features (min_df={min_df}, seeds removed)")
    probs, info["secs"] = score_s(S["sentence"].tolist(), in_train, X, y, vec, seed, folds,
                                  chunk_size, verbose)
    scored = add_target(probs, threshold)
    scored.insert(0, "file", S["file"].to_numpy())
    scored.insert(1, "sentence_id", S["sentence_id"].to_numpy())
    scored["in_train"] = in_train
    return scored, vec, info


def run_classify(cfg: dict, R: pd.DataFrame, S: pd.DataFrame, n_examples: int = 20) -> pd.DataFrame:
    """Task 2.3 stage wrapper: classify, save cache/discovery/S_scored.parquet, print summary."""
    d = cfg["discovery"]
    seed = cfg["settings"]["sample_seed"]
    thr = float(d["t_threshold"])
    print(f"[discover] task 2.3: NB + SVC(LinearSVC+calibration, DEVIATION) + RF ({m_note(cfg)})")
    scored, _, info = classify(R, S, load_seeds(cfg), d["min_df"], float(d["s_train_ratio"]),
                               int(d["s_train_max"]), thr, seed, cfg["settings"]["chunk_size"],
                               int(d["oof_folds"]))

    out = discovery_dir(cfg) / "S_scored.parquet"
    scored.to_parquet(out, index=False)

    T = scored[scored["in_T"]]
    tr = scored["in_train"]
    print(f"[discover] |T| = {len(T):,} of |S| = {len(S):,} (T share of S {len(T) / max(len(S), 1):.2%}) "
          f"with p_max > {thr} -> {out}")
    print("[discover] |T| per classifier: " + "  ".join(
        f"{k}={int((scored[f'p_{k}'] > thr).sum()):,}" for k in MODELS))
    print(f"[discover] |T| in_train (out-of-fold) = {int(T['in_train'].sum()):,} of {int(tr.sum()):,}  |  "
          f"not in_train = {int((~T['in_train']).sum()):,} of {int((~tr).sum()):,}")
    q = scored["p_max"].quantile([0.5, 0.9, 0.99, 0.999])
    print("[discover] p_max quantiles: " + "  ".join(f"{p * 100:g}%={v:.4f}" for p, v in q.items()))
    print("[discover] run time per classifier: " + "  ".join(f"{k}={v:.1f}s" for k, v in info["secs"].items()))

    n_ex = min(n_examples, len(T))
    if n_ex:
        ex = T.sample(n=n_ex, random_state=seed).merge(S, on=["file", "sentence_id"], how="left")
        print(f"[discover] {n_ex} random example sentences from T (lemmatized):")
        for i, r in enumerate(ex.itertuples(index=False), 1):
            txt = r.sentence if len(r.sentence) <= 220 else r.sentence[:217] + "..."
            print(f"  {i:>2}. [{r.file} | nb={r.p_nb:.2f} svc={r.p_svc:.2f} rf={r.p_rf:.2f}"
                  f"{' | oof' if r.in_train else ''}] {txt}")
    return scored
