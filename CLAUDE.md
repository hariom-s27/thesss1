# CLAUDE.md — climate_pipeline

## Goal
Rebuild the Sautner, van Lent, Vilkov & Zhang (2023, JF) climate-exposure method as ONE
pipeline: seeds → keyword discovery → bigram dictionary → scores (Eq. 1–4) → validation.
Prototype on ~200 transcripts (`--sample`), same code scales to full corpus and Indian MD&A.
Full plan: ROADMAP_climate_exposure_pipeline.md (work task by task, in order).

## Rules
- Build everything in `climate_pipeline/`. NEVER edit `week1_thesis/` (old reference code).
- No hard-coded paths. All paths/settings come from `climate_pipeline/config.yaml`.
- ONE text cleaner: `src/preprocess.py` (spaCy lemmas + CountVectorizer(ngram_range=(2,2),
  stop_words="english"), bigrams never cross sentences). Every stage uses it.
- Each stage reads from and writes to `cache/` (parquet), so stages can re-run alone.
- Entry point: `python run.py --stage <name> [--sample]`.
- Every task adds/updates a pytest in `tests/` and must pass before finishing.
- Old outputs in `outputs/` are the "before" numbers; new code must match them
  (e.g. ExxonMobil 2024 CCExposure = 0.00451 with the authors' dictionary).
- One task = one commit. Never commit data, .env, or API keys.
- Always use .venv\Scripts\python.exe in this repo (never D:\sem_iitk\sem9\thesis\.venv).

## Data locations (outside repo, read-only)
- Authors' dictionaries (.pkl): D:/sem_iitk/sem 8/thesis/old _work/code/jofi13219-sup-0002-replicationcode/Replication Files Sautner et al. (2023)/B. Figure 1 2, Table 2, and IA Table 6 7 8 9 11/bigrams
- API transcripts: D:/sem_iitk/sem 8/thesis/api_transcripts
- PDF transcripts: D:/sem_iitk/sem 8/thesis/old _work/transcript
- Official scores: D:/sem_iitk/sem 8/thesis/old _work/csv/firmyear_score_2024Q4_Version_2025_Jul_03.csv
