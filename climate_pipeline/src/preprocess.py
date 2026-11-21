"""ONE shared text cleaner: sentences -> lemmas -> bigrams.

Logic copied exactly from week1_thesis/exact_reproduction_api.py (the SvLVZ recipe):
  nltk sent_tokenize -> spaCy en_core_web_sm (ner+parser disabled, sentencizer added)
  per sentence -> lowercase lemmas, drop space/punct tokens -> one string per sentence.
Bigrams come from CountVectorizer fitted on the sentence list, so bigrams never cross
sentence boundaries.
"""
from __future__ import annotations

import nltk
import numpy as np
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer

_NLP = None
_NLTK_READY = False


def _ensure_nltk() -> None:
    global _NLTK_READY
    if _NLTK_READY:
        return
    for res in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{res}")
        except LookupError:
            nltk.download(res, quiet=True)
    _NLTK_READY = True


def get_nlp():
    """Load spaCy once (lazy, module-level)."""
    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm", disable=["ner", "parser"])
        _NLP.add_pipe("sentencizer")
    return _NLP


def make_vectorizer() -> CountVectorizer:
    """The exact vectorizer from the SvLVZ do-file."""
    return CountVectorizer(analyzer="word", strip_accents="unicode",
                           ngram_range=(2, 2), lowercase=True, stop_words="english")


def lemmatize(text: str) -> list[str]:
    """Return one cleaned (lowercase lemma) string per sentence; empty sentences dropped."""
    _ensure_nltk()
    nlp = get_nlp()
    out = []
    for s in sent_tokenize(text):
        doc = nlp(s)
        lemmas = [t.lemma_.lower() for t in doc if not t.is_space and not t.is_punct]
        if lemmas:
            out.append(" ".join(lemmas))
    return out


def sentence_bigram_matrix(sentences: list[str]):
    """(M, feats): sparse CSR sentence x bigram count matrix and its bigram names.

    One row per sentence, so bigrams never cross sentences. Returns (None, []) when there
    are no sentences or no bigrams (e.g. only stop words).
    """
    if not sentences:
        return None, []
    vec = make_vectorizer()
    try:
        m = vec.fit_transform(sentences)
    except ValueError:  # empty vocabulary (e.g. only stop words)
        return None, []
    return m.tocsr(), [str(f) for f in vec.get_feature_names_out()]


def bigram_counts(sentences: list[str]) -> dict[str, int]:
    """Bigram -> count over the whole transcript (bigrams never cross sentences)."""
    m, feats = sentence_bigram_matrix(sentences)
    if m is None:
        return {}
    counts = np.asarray(m.sum(axis=0)).ravel()
    return {f: int(c) for f, c in zip(feats, counts)}


def total_bigrams(sentences: list[str]) -> int:
    """Total bigram count B for the transcript (denominator of Eq. 1)."""
    return sum(bigram_counts(sentences).values())
