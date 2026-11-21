import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run import load_config  # noqa: E402
from src import preprocess  # noqa: E402
from src.scoring import firm_year, load_dictionaries, score_transcript  # noqa: E402

CFG = load_config(PIPELINE_DIR / "config.yaml")


# ---- toy example: exact expected exposure ---------------------------------------

def test_toy_exposure_exact():
    # already-lemmatized sentences; stop words ("we", "the", "and") are removed by the vectorizer
    sents = ["carbon tax rise", "carbon tax hurt margin", "sea level rise"]
    # bigrams: carbon tax x2, tax rise, tax hurt, hurt margin, sea level, level rise -> B = 7
    dicts = {"cc": frozenset({"carbon tax", "sea level"}), "op": frozenset(),
             "rg": frozenset({"carbon tax"}), "ph": frozenset({"sea level", "not there"})}
    r = score_transcript(sents, dicts)
    assert r["B"] == 7
    assert r["cc_expo"] == 3 / 7
    assert r["op_expo"] == 0.0
    assert r["rg_expo"] == 2 / 7
    assert r["ph_expo"] == 1 / 7


def test_no_bigrams_gives_nan():
    r = score_transcript([], {"cc": frozenset(), "op": frozenset(), "rg": frozenset(), "ph": frozenset()})
    assert r["B"] == 0 and np.isnan(r["cc_expo"])


def test_firm_year_is_mean_of_quarters():
    df = pd.DataFrame({
        "ticker": ["A", "A", "A", "B"], "isin": ["X1", "X1", "X1", None], "year": [2020, 2020, 2021, 2020],
        "cc_expo": [0.1, 0.3, 0.5, 0.2], "op_expo": [0, 0.2, 0, 0], "rg_expo": [0] * 4, "ph_expo": [0] * 4,
    })
    fy = firm_year(df).set_index(["ticker", "year"])
    assert fy.loc[("A", 2020), "cc_expo"] == pytest.approx(0.2)
    assert fy.loc[("A", 2020), "op_expo"] == pytest.approx(0.1)
    assert fy.loc[("A", 2020), "n_transcripts"] == 2
    assert fy.loc[("B", 2020), "cc_expo"] == pytest.approx(0.2)  # missing ISIN kept, not dropped


# ---- real data ------------------------------------------------------------------

def _dicts_or_skip():
    d = CFG["paths"]["authors_dictionaries"]
    if not all((d / f).exists() for f in CFG["dictionaries"].values()):
        pytest.skip(f"authors' dictionaries missing: {d}")
    return load_dictionaries(CFG, verbose=False)


def test_dictionary_sizes():
    dicts = _dicts_or_skip()
    assert {k: len(v) for k, v in dicts.items()} == {"cc": 9641, "op": 2710, "rg": 251, "ph": 51}


def test_real_transcript_matches_old_reference():
    dicts = _dicts_or_skip()
    tdir = CFG["paths"]["transcript_dir"]
    files = sorted(tdir.glob("XOM_*.txt")) or sorted(tdir.glob("*.txt")) if tdir.is_dir() else []
    if not files:
        pytest.skip(f"transcript_dir not found or has no .txt files: {tdir}")
    import reference_old as ref

    text = files[-1].read_text(encoding="utf-8", errors="replace")
    new = score_transcript(preprocess.lemmatize(text), dicts)
    old = ref.score(ref.lemmatize(text), CC=dicts["cc"], OP=dicts["op"], RG=dicts["rg"], PH=dicts["ph"])
    assert new["B"] == old["B"]
    assert new["cc_expo"] > 0
    for k in ("cc_expo", "op_expo", "rg_expo", "ph_expo"):
        assert new[k] == old[k], k  # exact, not approx


def test_check_xom_2024_matches_old_script():
    """check_xom 2024 == the frozen old exact_reproduction.py logic on the same PDFs.

    NOTE: the documented old value 0.00451 does NOT reproduce, even with the frozen old
    code (tests/reference_old.py) on today's PDFs + environment: both give 0.0045751
    (0.00451 equals the 3Q24 single-quarter value). So we pin the reproducible value.
    """
    pdf_dir = CFG["paths"]["pdf_dir"]
    pdfs = sorted(pdf_dir.glob("*24*.pdf")) if pdf_dir.is_dir() else []
    if not pdfs:
        pytest.skip(f"PDF transcripts missing: {pdf_dir}")
    dicts = _dicts_or_skip()
    import reference_old as ref
    from src.io_utils import read_pdf
    from src.scoring import check_xom

    tab = check_xom(CFG).set_index("year")
    assert tab.loc[2024, "n_transcripts"] == 4
    old = [ref.score(ref.lemmatize(read_pdf(p)), CC=dicts["cc"], OP=dicts["op"],
                     RG=dicts["rg"], PH=dicts["ph"]) for p in pdfs]
    for k in ("cc_expo", "op_expo", "rg_expo", "ph_expo"):
        assert tab.loc[2024, k] == pytest.approx(np.mean([o[k] for o in old]), rel=1e-12), k
    assert tab.loc[2024, "cc_expo"] == pytest.approx(0.004575, abs=1e-5)
    assert tab.loc[2024, "ph_expo"] == 0.0
