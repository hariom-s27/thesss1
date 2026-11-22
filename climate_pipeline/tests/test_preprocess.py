import sys
from pathlib import Path

import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run import load_config  # noqa: E402
from src import preprocess  # noqa: E402
import reference_old as ref  # noqa: E402

TEXT = (
    "Good morning, everyone. We are investing heavily in carbon capture and storage. "
    "Climate change regulation, including a carbon tax, could affect our refining margins! "
    "Renewable energy projects - wind and solar power - grew 20% this quarter.\n\n"
    "Questions? Greenhouse gas emissions fell. Carbon capture remains our priority."
)


def test_short_text_matches_old():
    sents = preprocess.lemmatize(TEXT)
    assert sents == ref.lemmatize(TEXT)
    new = preprocess.bigram_counts(sents)
    old = ref.ref_bigram_counts(ref.lemmatize(TEXT))
    assert new and new == old
    assert preprocess.total_bigrams(sents) == ref.score(ref.lemmatize(TEXT))["B"]
    # bigrams never cross sentences: "emission fall" ends a sentence, "fall carbon" must not appear
    assert "fall carbon" not in new


def test_real_transcript_matches_old():
    tdir = load_config(PIPELINE_DIR / "config.yaml")["paths"]["transcript_dir"]
    files = sorted(tdir.glob("*.txt")) if tdir.is_dir() else []
    if not files:
        pytest.skip(f"transcript_dir not found or has no .txt files: {tdir}")
    text = files[0].read_text(encoding="utf-8")

    sents = preprocess.lemmatize(text)
    old_sents = ref.lemmatize(text)
    assert preprocess.bigram_counts(sents) == ref.ref_bigram_counts(old_sents)
    assert preprocess.total_bigrams(sents) == ref.score(old_sents)["B"]
