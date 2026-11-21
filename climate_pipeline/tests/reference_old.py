"""FROZEN reference: lemmatize + score logic copied verbatim from
week1_thesis/exact_reproduction_api.py (lines 34-59). Do not modify.

The old script runs its whole pipeline at import time, so it is not imported;
only the functions are copied here. score() is adapted only so the dictionaries
are passed in (the old one read module-level CC/OP/RG/PH loaded from .pkl files),
and ref_bigram_counts() exposes the freq dict that score() builds internally.
"""
import numpy as np
import spacy
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

# ---- 2. spaCy + the EXACT vectorizer from the SvLVZ do-file ------------------
nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
nlp.add_pipe("sentencizer")
vec = CountVectorizer(analyzer="word", strip_accents="unicode",
                      ngram_range=(2, 2), lowercase=True, stop_words="english")

def lemmatize(text):
    """Return a list of lemmatized sentences (bigrams do not cross sentences)."""
    out = []
    for s in sent_tokenize(text):
        doc = nlp(s)
        lemmas = [t.lemma_.lower() for t in doc if not t.is_space and not t.is_punct]
        if lemmas:
            out.append(" ".join(lemmas))
    return out

def score(sent_list, CC=frozenset(), OP=frozenset(), RG=frozenset(), PH=frozenset()):
    m = vec.fit_transform(sent_list)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(m.sum(axis=0)).ravel()
    total = counts.sum()
    freq = dict(zip(feats, counts))
    hit = lambda D: sum(freq[b] for b in (set(feats) & D))
    return dict(B=int(total),
                cc_expo=hit(CC)/total, op_expo=hit(OP)/total,
                rg_expo=hit(RG)/total, ph_expo=hit(PH)/total)


def ref_bigram_counts(sent_list):
    """The `freq` dict built inside score(), with plain Python types."""
    m = vec.fit_transform(sent_list)
    feats = np.array(vec.get_feature_names_out())
    counts = np.asarray(m.sum(axis=0)).ravel()
    return {str(f): int(c) for f, c in zip(feats, counts)}


# =============================================================================
# FROZEN: measures() from week1_thesis/phase2_sentiment_risk.py (Eq. 2-3). Do not modify.
# Adapted only so CC / POS / NEG / RISKW are passed in instead of module globals
# (call with CC=<any of the 4 dictionaries>; output keys stay "cc_*" as in the old code).
# =============================================================================
def measures(sents, CC, POS, NEG, RISKW):
    M = vec.fit_transform(sents)
    feats = np.array(vec.get_feature_names_out())
    B = int(np.asarray(M.sum(axis=0)).ravel().sum())   # denominator = whole transcript
    cc = pos = neg = risk = 0
    for i, s in enumerate(sents):
        row = M[i]
        hits = sum(int(c) for j, c in zip(row.indices, row.data) if feats[j] in CC)
        if hits == 0:
            continue
        cc += hits
        w = set(s.split())                  # words of THIS sentence
        if w & POS:   pos  += hits          # Eq. 2 positive
        if w & NEG:   neg  += hits          # Eq. 2 negative
        if w & RISKW: risk += hits          # Eq. 3
    return dict(B=B,
                cc_expo=cc / B,
                cc_pos=pos / B,
                cc_neg=-neg / B,            # stored NEGATIVE, matching the authors
                cc_sent=(pos - neg) / B,    # net = pos + (negative-signed neg)
                cc_risk=risk / B)


# =============================================================================
# FROZEN: pass 1 + pass 2 of week1_thesis/phase3_tfidf.py (Eq. 4). Do not modify.
# Adapted only to take a list of lemmatized-sentence lists instead of reading PDFs.
# =============================================================================
def tfidf(docs_sents, CC):
    from collections import Counter
    docs, doc_freq = [], Counter()
    for sents in docs_sents:
        M = vec.fit_transform(sents)
        feats = np.array(vec.get_feature_names_out())
        counts = np.asarray(M.sum(axis=0)).ravel()
        B = int(counts.sum())
        cc_counts = {f: int(c) for f, c in zip(feats, counts) if f in CC and c > 0}
        docs.append(dict(B=B, cc_counts=cc_counts))
        for bg in cc_counts:
            doc_freq[bg] += 1
    N = len(docs)
    rows = []
    for d in docs:
        plain = sum(d["cc_counts"].values())
        weighted = 0.0
        for bg, c in d["cc_counts"].items():
            f = doc_freq[bg]
            if f > 0:
                weighted += c * np.log(N / f)
        rows.append(dict(B=d["B"], cc_expo=plain / d["B"], cc_tfidf=weighted / d["B"]))
    return rows
