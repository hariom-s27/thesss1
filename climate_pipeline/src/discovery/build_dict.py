"""Discovery task 2.5: C_discovered = seeds ∪ kept T-only ∪ kept top_pct (ROADMAP section 3, step 7).

Outputs:
  cache/discovery/C_discovered.pkl   a Python set of str (the authors' .pkl is a list of str;
                                      src.scoring loads either the same way)
  outputs/discovered_bigrams.csv     bigram, source, king_score, n_kT, in_authors
                                      (seeds first, then discovered bigrams by king_score)
"""
from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd

from src.discovery.split import discovery_dir, load_seeds

KEPT = ("t_only", "top_pct")
TABLE_COLS = ["bigram", "source", "king_score", "n_kT", "in_authors"]


def c_discovered_path(cfg: dict) -> Path:
    return Path(cfg["paths"]["cache"]) / "discovery" / "C_discovered.pkl"


def build_dictionary(ranked: pd.DataFrame, seeds) -> set[str]:
    """C = seeds ∪ bigrams whose source is t_only or top_pct."""
    kept = ranked.loc[ranked["source"].isin(KEPT), "bigram"]
    return set(map(str, seeds)) | set(map(str, kept))


def discovered_table(ranked: pd.DataFrame, seeds, authors) -> pd.DataFrame:
    """One row per bigram of C: seeds (source 'seed') then kept bigrams in ranked order."""
    authors = set(authors)
    seeds = [str(s) for s in seeds]
    kept = ranked.loc[ranked["source"].isin(KEPT) & ~ranked["bigram"].isin(set(seeds)),
                      ["bigram", "source", "king_score", "n_kT"]]
    seed_rows = pd.DataFrame({"bigram": seeds, "source": "seed", "king_score": float("nan"), "n_kT": pd.NA})
    tab = pd.concat([seed_rows, kept], ignore_index=True)
    tab["n_kT"] = tab["n_kT"].astype("Int64")
    tab["in_authors"] = tab["bigram"].isin(authors)
    return tab[TABLE_COLS]


def run_build_dict(cfg: dict, ranked: pd.DataFrame, authors) -> tuple[set[str], pd.DataFrame]:
    """Task 2.5 stage wrapper: save the .pkl and the csv, print sizes."""
    seeds = load_seeds(cfg)
    C = build_dictionary(ranked, seeds)
    tab = discovered_table(ranked, seeds, authors)
    assert len(tab) == len(C)

    pkl = c_discovered_path(cfg)
    discovery_dir(cfg)
    with open(pkl, "wb") as f:
        pickle.dump(C, f)
    csv = Path(cfg["paths"]["outputs"]) / "discovered_bigrams.csv"
    csv.parent.mkdir(parents=True, exist_ok=True)
    tab.to_csv(csv, index=False)

    by = tab["source"].value_counts()
    print(f"[discover] task 2.5: |C_discovered| = {len(C):,} = "
          + " + ".join(f"{s} {int(by.get(s, 0)):,}" for s in ("seed", "t_only", "top_pct"))
          + f"  (authors' cc dictionary: {len(set(authors)):,})")
    print(f"[discover]   -> {pkl}, {csv}")
    return C, tab


def load_c_discovered(cfg: dict) -> set[str]:
    p = c_discovered_path(cfg)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run --stage discover first")
    with open(p, "rb") as f:
        return set(pickle.load(f))
