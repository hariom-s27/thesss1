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
