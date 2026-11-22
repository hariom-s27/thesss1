# Roadmap: Climate Exposure Pipeline (Sautner et al. 2023 → your thesis)

**Goal:** first build a small **prototype** that runs from start to finish on a few hundred transcripts. Then grow the *same code* to thousands of transcripts and to Indian MD&A text (arpipe), without rewriting anything.

---

## 1. Why one codebase can go from prototype to full scale

The paper's core algorithm is mostly small-data work. Only one step is big.

| Step | Paper size | Heavy? |
|---|---|---|
| Train classifiers | R (~60k sentences) + 100k random sentences from S | **No.** It fits on a laptop |
| Predict on the search set S | ~70 million sentences | **Yes.** But it's easy to do in batches (chunks) |
| Count bigrams in T vs S\T | Counting only | Batches |
| Score transcripts (Eq. 1–4) | One transcript at a time | Batches |

So the prototype and the full version use **the same code**. Only two settings change: `SAMPLE_MODE` and `CHUNK_SIZE`.

---

## 2. Target folder layout (build in VS Code)

```
climate_pipeline/
├── config.yaml              # ALL paths + settings (no more hard-coded D:\ paths)
├── run.py                   # one entry point:  python run.py --stage all --sample
├── src/
│   ├── io_utils.py          # load transcripts (txt/pdf), save/load parquet
│   ├── preprocess.py        # ONE shared cleaner: sentences, lemmas, bigrams
│   ├── discovery/
│   │   ├── rough_library.py # Step 1-2: IPCC minus non-climate text → set M
│   │   ├── split.py         # Step 3: R (has seed) vs S (no seed)
│   │   ├── classify.py      # Step 4-5: NB + SVC + RF → target set T (p > 0.8)
│   │   ├── rank.py          # Step 6: T-only bigrams + King likelihood + top 5%
│   │   └── build_dict.py    # Step 7: C = seeds ∪ discovered
│   ├── scoring.py           # Eq. 1-4 (exposure, sentiment, risk, TF-IDF)
│   ├── validation/          # paper tests (Table II, III, V, VI, IA.V, Fig 2 ...)
│   ├── extras/              # your tests (placebo, split-half, bootstrap ...)
│   └── applications/        # Table IV, VII-X (only when data exists)
├── data/                    # raw inputs (gitignored)
├── cache/                   # parquet intermediate files (gitignored)
├── outputs/                 # csv results + report
└── tests/                   # small checks so nothing silently breaks
```

**Rules:**
1. Each stage reads files from `cache/` and writes files back to `cache/`. So you can re-run any stage on its own.
2. `--sample` mode uses about 200 transcripts. Full mode uses everything.
3. A dictionary switch: `dictionary: authors` (the authors' `.pkl` files, to match their numbers) or `dictionary: discovered` (your own discovery output).

---

## 3. The core algorithm (what to build in `src/discovery/`)

The steps below come from the paper's Internet Appendix, Section I:

1. **Rough library:** bigrams from IPCC reports (lemmatized, stemmed, digits/punctuation/stop words removed, frequency below 10 dropped), *minus* bigrams from normal text (novels, news, IMF reports, textbooks).
2. **Set M:** transcript sentences that contain at least one rough bigram.
3. **Split M using the 50 seeds (Table IA.III):** R = sentences with a seed, S = sentences without one.
4. **Train** Multinomial Naive Bayes, SVC and Random Forest on R + 100k random sentences from S. Tune each with grid-search cross-validation.
5. **Target set T:** sentences in S where *any* classifier gives probability > 0.8.
6. **Rank bigrams:**
   - bigrams found only in T → keep all of them (paper: ~3,800)
   - bigrams in both → keep only if their document frequency is higher in T than in S\T
   - rank with King, Lam & Roberts' likelihood (Beta-binomial, α = 1, computed with log-gamma). Keep the top 5% (paper: ~5,000)
7. **C = seeds ∪ discovered.** The paper ends with about 8,850 bigrams. The authors' `.pkl` file has 9,641.

**King likelihood (for `rank.py`):** for bigram k, count
`n_kT` = sentences in T that contain k, `n_kS` = sentences in S\T that contain k, `N_T` = total sentences in T, `N_S` = total sentences in S\T.

```
score(k) = betaln(n_kT + 1, n_kS + 1) + betaln(N_T - n_kT + 1, N_S - n_kS + 1)
```

Use `scipy.special.betaln`. It's the log-gamma version, so it won't overflow on big numbers. Check it against King's replication code on Harvard Dataverse (doi:10.7910/DVN/FMJDCD).

**Prototype simplification (allowed at first, but flag it):** skip Steps 1–2 and use all sentences as M. Add the IPCC rough library in Phase 3.

---

## 4. Phases

### Phase 0: Setup and clean-up (no new science)
| # | Task | Done when |
|---|---|---|
| 0.1 | Create the folder layout, `config.yaml` and `run.py` with a `--stage` flag | `python run.py --help` works |
| 0.2 | Write one `preprocess.py` (copy the logic from `exact_reproduction.py`: spaCy lemmas + `CountVectorizer(ngram_range=(2,2), stop_words="english")`) | Gives the same bigrams as the old script on 1 transcript |
| 0.3 | `io_utils.py`: load txt/pdf transcripts and cache sentences to parquet | 200 transcripts cached |
| 0.4 | Add `tests/` with 3 small tests (preprocess, scoring, loading) | `pytest` passes |

### Phase 1: Scoring module (copy what already works)
| # | Task | Done when |
|---|---|---|
| 1.1 | `scoring.py` with Eq. 1 (+ opportunity, regulatory, physical) using the authors' `.pkl` files | ExxonMobil 2024 CCExposure = **0.004575** (79.6% of official 0.00575), mean of 4 quarterly PDFs |
| 1.2 | Add Eq. 2 sentiment and Eq. 3 risk | Same numbers as `phase2_sentiment_risk.py` |
| 1.3 | Add Eq. 4 TF-IDF | Same numbers as `phase3_tfidf.py` |
| 1.4 | Firm-year aggregation + comparison with the official OSF csv | `outputs/validation_results.csv` |

### Phase 2: Discovery prototype ⭐ (the core: this IS the prototype)
| # | Task | Done when |
|---|---|---|
| 2.1 | Put the real 50 seeds (Table IA.III) in `config.yaml` | 50 seeds loaded |
| 2.2 | `split.py`: R vs S | Counts of R and S printed |
| 2.3 | `classify.py`: NB + SVC + RF on R + a sample of S; predict S in chunks; T = max probability > 0.8 | T saved to cache |
| 2.4 | `rank.py`: T-only bigrams + King likelihood + top 5% | Ranked bigram list saved |
| 2.5 | `build_dict.py`: C = seeds ∪ discovered, saved as `.pkl` | Your own dictionary file |
| 2.6 | **Check the discovery:** overlap between your C and the authors' 9,641 bigrams (what % of your top 500 is in theirs) | One number for the thesis |
| 2.7 | Score with `dictionary: discovered`, and correlate with the scores from the authors' dictionary | A correlation number |

> **Prototype = Phase 0 + 1 + 2.** At that point you have a working, start-to-finish pipeline: seeds → discovered bigrams → scores → comparison with official numbers.

### Phase 3: Make discovery faithful
| # | Task | Done when |
|---|---|---|
| 3.1 | Rough library: download IPCC report PDFs (free on ipcc.ch) and normal text (Project Gutenberg) → `rough_library.py` → set M | M saved; count printed |
| 3.2 | Grid-search cross-validation for the 3 classifiers | Best settings logged |
| 3.3 | Topic discovery: re-run with Table IA.IV seeds; drop bigrams shared across topics; intersect with C | Opportunity, regulatory and physical dictionaries |
| 3.4 | Compare your King likelihood against the King Dataverse code | Same ranking on a small example |

### Phase 4: Validation suite (move the old phase scripts into modules)
| # | Task | Status before |
|---|---|---|
| 4.1 | Correlations between measures (Table IA.V) | have → move in |
| 4.2 | Top-100 bigrams (Table II) | have → move in |
| 4.3 | Seeds only vs. full dictionary (Figure 2) | have → move in |
| 4.4 | Industry ranking (Table III) | have → move in |
| 4.5 | Variance decomposition (Table V) | have → move in |
| 4.6 | **Drop one seed at a time, now by re-running discovery** (the real paper version) | half → finish |
| 4.7 | **Measurement error (Table VI)**, needs no new data | missing → build |
| 4.8 | Human audit: label the snippet sheet, compute precision/recall/kappa | half → finish |

### Phase 5: Your extra tests (move them in)
Placebo, split-half reliability, preprocessing robustness, Paris 2015 event study, bootstrap confidence intervals, permutation test, comparison with 10-K MD&A. All exist; just move them into `src/extras/`.

### Phase 6: Outcome tests (only where data can be found)
| # | Paper test | Data | Status |
|---|---|---|---|
| 6.1 | Correlation with public climate attention (Table IV, Panel B) | Engle et al. climate news index (their slides say the series is free on Stroebel's website) | Doable |
| 6.2 | Correlation with emissions (Table IV, Panel A) | Trucost (paid); US alternative: EPA GHG Reporting Program | Partly doable |
| 6.3 | Comparison with Engle et al.'s word list (Tables IA.XI–XII) | Their vocabulary | Doable if the list is published |
| 6.4 | Green patents (Table VIII) | Patent data (USPTO PatentsView, free as far as I know) | Doable, more work |
| 6.5 | Green jobs (Table VII) | Burning Glass (paid) | Skip or say "future work" |
| 6.6 | Options (Table IX) | OptionMetrics (paid; ask IITK library if they have WRDS) | Probably skip |
| 6.7 | Stock-return factor (Table X) | Returns + Compustat | Only if WRDS access |

### Phase 7: Scale and India
| # | Task |
|---|---|
| 7.1 | Full mode on all transcripts: chunked prediction, multiprocessing, progress bar, resume after a crash |
| 7.2 | Read arpipe's MD&A output in `io_utils.py` |
| 7.3 | Run discovery on Indian MD&A text, so you get an India-specific dictionary |
| 7.4 | Compare India scores from the authors' dictionary vs your India dictionary (this is a thesis contribution) |

---

## 5. Current status → target

| Block | Now | After the prototype (Phase 0–2) | After everything |
|---|---|---|---|
| Data collection | 100% | 100% | 100% |
| Discovery (core) | ~30% | ~70% | ~95% |
| Scoring Eq. 1–4 | ~95% | 100% | 100% |
| Validation (paper) | ~60% | ~60% | ~90% |
| Applications | 0% | 0% | ~40–60% (depends on data) |
| **Overall vs paper** | **~50%** | **~60%** | **~85%** |

---

## 6. How much work with Claude Code (rough estimate)

Count **one task = one focused Claude Code request**, like "build `rank.py` with the King likelihood + a test". Each task is about 15–60 min of Claude Code time plus your review.

| Phase | Tasks | Claude Code sessions (rough) |
|---|---|---|
| 0 Setup | 4 | 2–3 |
| 1 Scoring | 4 | 2–3 |
| 2 Discovery prototype ⭐ | 7 | 4–6 |
| **Prototype total** | **15** | **~8–12 sessions (≈ 2–4 days part-time)** |
| 3 Faithful discovery | 4 | 3–4 |
| 4 Validation | 8 | 4–6 |
| 5 Extras | 1 (move 7 tests) | 2 |
| 6 Applications | 3–4 realistic | 4–8 (mostly getting the data) |
| 7 Scale + India | 4 | 3–5 |
| **Everything** | **~40 tasks** | **~25–35 sessions (≈ 2–3 weeks part-time)** |

How fast this goes depends on your Claude plan's usage limits and how long the data downloads take. The code itself is not the slow part. The slow parts are: (a) the discovery prediction step on a big corpus (hours on a laptop), and (b) getting outside data for Phase 6.

---

## 7. How to work with Claude Code (practical)

1. Put a `CLAUDE.md` in the repo root with: the goal, the folder layout above, "one shared preprocess.py", "never hard-code paths", and "every stage writes to cache/".
2. Give Claude Code **one task row at a time**, including its "Done when" check. Example:
   > "Do task 2.4: build `src/discovery/rank.py`. Input: `cache/T.parquet`, `cache/S_minus_T.parquet`. Keep T-only bigrams, keep shared bigrams with higher doc-freq in T, rank with betaln King likelihood (α=1), keep top 5%. Add a pytest with a tiny toy example. Done when the test passes and `python run.py --stage rank --sample` writes `cache/ranked_bigrams.parquet`."
3. After each phase, run `python run.py --stage all --sample` to make sure nothing broke.
4. Commit after each task (one task = one commit).

---

## 8. Your existing GitHub code: where each file goes

**Decision:** build the new pipeline **inside `hariom-s27/thesss1`** as a new folder `climate_pipeline/`, on a new branch (e.g. `pipeline-v1`). Keep `week1_thesis/` untouched as the reference/old version. arpipe stays a **separate repo** that only supplies Indian MD&A text (Phase 7).

| Your existing file (week1_thesis/) | Goes into (climate_pipeline/) | Action |
|---|---|---|
| `collect_multi_provider.py`, `collect_bulk_transcripts.py` | `src/collect.py` (Block 0) | Move in; read paths from config |
| `fetch_transcripts_fmp.py`, `fetch_transcripts_alphavantage.py`, `list_confirmed_empty.py` | `scripts/` (one-off tools) | Keep as they are |
| `exact_reproduction.py`, `exact_reproduction_api.py`, `score_and_correlate.py` | `src/preprocess.py` + `src/scoring.py` (Eq. 1) | **Base of Phase 0–1.** Merge into one |
| `phase2_sentiment_risk.py`, `phase2_api.py` | `src/scoring.py` (Eq. 2–3) | Merge; keep the 3 risk-list options |
| `phase3_tfidf.py`, `phase4_tfidf_and_risk.py` | `src/scoring.py` (Eq. 4) + `src/validation/risk_list.py` | Merge |
| `climate_exposure_full_algorithm.ipynb` | `src/discovery/*` | **Starting point for Phase 2**: reuse the R/S split; replace logistic regression with NB+SVC+RF, add T (p>0.8), King likelihood, top 5% |
| `phase5_validation_suite.py` | `src/validation/` (Table IA.V, Fig 2, drop-one-seed) + **50 seeds → config.yaml** | Move in; real seeds feed discovery |
| `phase6_analysis_suite.py` | `src/validation/` (Table III, Table V, trends) | Move in |
| `audit_bigrams.py` | `src/validation/top_bigrams.py` (Table II) | Move in |
| `phase9_snippet_audit.py` | `src/validation/human_audit.py` | Move in |
| `phase7_extended_validation.py`, `phase8_inference.py` | `src/extras/` | Move in |
| `gap_analysis.py`, `analyze_trends.py` | `src/extras/` | Move in |
| `outputs/*.csv` | `outputs/` | Keep; use as "before" numbers to check nothing changed |
| `ARPipe_Memory/`, `sep_week1/`, `sep_week2/` | stay where they are | arpipe docs, not part of this pipeline |

**What's new code (not in your repo yet):** `config.yaml`, `run.py`, `tests/`, discovery steps 1–2 and 4–6 (rough library, 3 classifiers, T set, King ranking, top 5%), Table VI measurement error, the real drop-one-seed re-run, Phase 6 outcome tests, and the arpipe reader.

**Rough split:** about **60% of the new pipeline is your existing code moved and cleaned**, about **40% is new code** (mostly discovery and the missing tests).

---

## 9. Sources

- Sautner et al. (2023), *Journal of Finance*, main text: Eq. 1–4, Section II.A.
- Sautner et al., ECGI working paper (revised March 2023), Internet Appendix Section I: discovery steps, Table IA.III seeds.
  https://www.ecgi.global/sites/default/files/2026-10/fin-686-2020_firm-level_climate_change_exposure.pdf
- King, Lam & Roberts (2017), *AJPS*: discovery algorithm + likelihood statistic. https://gking.harvard.edu/files/ajps12291_final.pdf
  Replication code: https://doi.org/10.7910/DVN/FMJDCD
- Sautner et al. data (OSF): https://doi.org/10.17605/OSF.IO/FD6JQ
- Engle et al. climate news index (series downloadable per the authors): https://pages.stern.nyu.edu/~jstroebe/EHHF/Hedging%20Climate%20Change%20News%20PhD_Class.pdf
- Your repos: `hariom-s27/thesss1` (week1_thesis/), `hariom-s27/arpipe`
