import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

from run import load_config  # noqa: E402
from src.io_utils import parse_name, read_text, sample_transcripts  # noqa: E402


# ---- file-name parsing ------------------------------------------------------

def test_parse_normal_name():
    assert parse_name("BA_2007Q2.txt") == {"ticker": "BA", "year": 2007, "quarter": 2}


def test_parse_odd_name_is_nan():
    r = parse_name("notes_final_v2.txt")
    assert all(pd.isna(r[k]) for k in ("ticker", "year", "quarter"))


def test_parse_old_pdf_name_keeps_year_quarter():
    r = parse_name("1Q24 Earnings Call Transcript_Final.pdf")
    assert pd.isna(r["ticker"]) and r["year"] == 2024 and r["quarter"] == 1


# ---- sampling ---------------------------------------------------------------

def _fake_listing():
    # 10 firms with very unequal coverage: AAA..JJJ, firm k has 5*(10-k) transcripts
    rows = []
    for k, t in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ"]):
        for i in range(5 * (10 - k)):
            yr, q = 2000 + i // 4, i % 4 + 1
            rows.append({"file": f"{t}_{yr}Q{q}.txt", "ticker": t, "year": yr, "quarter": q})
    rows.append({"file": "odd.txt", "ticker": np.nan, "year": np.nan, "quarter": np.nan})
    return pd.DataFrame(rows).sort_values("file").reset_index(drop=True)


def test_sample_same_seed_same_sample():
    df = _fake_listing()
    a = sample_transcripts(df, 20, seed=42)
    b = sample_transcripts(df, 20, seed=42)
    c = sample_transcripts(df, 20, seed=7)
    assert len(a) == 20
    assert a["file"].tolist() == b["file"].tolist()
    assert a["file"].tolist() != c["file"].tolist()


def test_sample_spreads_across_firms():
    df = _fake_listing()
    n = 20
    s = sample_transcripts(df, n, seed=42)
    first_n = df.head(n)
    assert s["ticker"].nunique() > first_n["ticker"].nunique()
    assert s["ticker"].nunique() == 10              # every firm before any repeats twice
    assert s["file"].is_unique


def test_sample_n_larger_than_df_returns_all():
    df = _fake_listing()
    assert len(sample_transcripts(df, 10_000, seed=42)) == len(df)


# ---- reading ----------------------------------------------------------------

def test_read_text_real_txt():
    tdir = load_config(PIPELINE_DIR / "config.yaml")["paths"]["transcript_dir"]
    files = sorted(tdir.glob("*.txt")) if tdir.is_dir() else []
    if not files:
        pytest.skip(f"transcript folder missing: {tdir}")
    text = read_text(files[0])
    assert isinstance(text, str) and len(text) > 1000


# ---- PDFs = XOM only, excluded from the corpus ---------------------------------

def _tmp_cfg(tmp_path, n_txt=6, sample=True):
    import copy
    cfg = copy.deepcopy(load_config(PIPELINE_DIR / "config.yaml"))
    tdir, pdir = tmp_path / "txt", tmp_path / "pdf"
    tdir.mkdir(), pdir.mkdir()
    for i in range(n_txt):
        (tdir / f"{'AB'[i % 2]}FIRM_{2010 + i}Q1.txt").write_text(f"Text number {i}. " * 50, encoding="utf-8")
    (pdir / "1Q24 Earnings Call Transcript.pdf").write_bytes(b"%PDF-fake")
    cfg["paths"].update(transcript_dir=tdir, pdf_dir=pdir, cache=tmp_path / "cache",
                        ticker_isin_map=tmp_path / "no_map.json")
    cfg["settings"].update(sample_mode=sample, sample_size=3, sample_seed=42)
    return cfg


def test_pdfs_get_pdf_ticker_and_isin(tmp_path):
    from src.io_utils import list_transcripts
    cfg = _tmp_cfg(tmp_path)
    pdfs = list_transcripts(cfg, sources=("pdf",), verbose=False)
    assert len(pdfs) == 1
    r = pdfs.iloc[0]
    assert (r["ticker"], r["isin"], r["year"], r["quarter"]) == ("XOM", "US30231G1022", 2024, 1)


def test_corpus_and_sample_exclude_pdfs(tmp_path, capsys):
    from src.io_utils import load_transcripts
    cfg = _tmp_cfg(tmp_path)
    df = load_transcripts(cfg)
    assert len(df) == 3 and (df["source"] == "txt").all()
    cfg["settings"]["sample_mode"] = False
    assert (load_transcripts(cfg)["source"] == "txt").all()


def test_manifest_triggers_rebuild(tmp_path, capsys):
    import json
    from src.io_utils import load_transcripts
    cfg = _tmp_cfg(tmp_path)
    load_transcripts(cfg)
    man = json.loads((tmp_path / "cache" / "manifest.json").read_text())
    assert man["mode"] == "sample" and man["sample_size"] == 3 and man["sample_seed"] == 42
    assert man["n_files"] == 6
    capsys.readouterr()

    load_transcripts(cfg)                                   # same settings -> reuse
    assert "reusing cached" in capsys.readouterr().out

    cfg["settings"]["sample_size"] = 4                      # changed setting -> rebuild + reason
    assert len(load_transcripts(cfg)) == 4
    out = capsys.readouterr().out
    assert "manifest differs" in out and "sample_size" in out

    (cfg["paths"]["transcript_dir"] / "AFIRM_2030Q1.txt").write_text("New. " * 50, encoding="utf-8")
    load_transcripts(cfg)                                   # new file -> n_files changed
    assert "n_files" in capsys.readouterr().out

    load_transcripts(cfg, force=True)                       # --force still forces
    assert "--force" in capsys.readouterr().out
