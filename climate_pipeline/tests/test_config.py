import sys
from pathlib import Path

import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

from run import load_config  # noqa: E402


def test_config_loads():
    cfg = load_config(PIPELINE_DIR / "config.yaml")

    for key in ("authors_dictionaries", "api_transcripts", "pdf_transcripts", "official_scores",
                "data", "cache", "outputs"):
        assert key in cfg["paths"], key
        assert isinstance(cfg["paths"][key], Path)

    s = cfg["settings"]
    assert s["sample_mode"] is False
    assert s["sample_size"] == 200
    assert isinstance(s["chunk_size"], int) and s["chunk_size"] > 0
    assert s["dictionary"] in ("authors", "discovered")


def test_bad_dictionary_rejected(tmp_path):
    text = (PIPELINE_DIR / "config.yaml").read_text(encoding="utf-8")
    bad = tmp_path / "config.yaml"
    bad.write_text(text.replace("dictionary: authors", "dictionary: nope"), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(bad)
