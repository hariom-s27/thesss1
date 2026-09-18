# P-B1 — Production Baseline & Windowed Language Gate

**Status:** HISTORICALLY ESTABLISHED  
**Primary Artifacts:** `arpipe/verify.py`, `arpipe/pipeline.py`, `live_store/documents.jsonl`

---

## 1. Objective and Architecture
Established the initial end-to-end extraction baseline for the 194-document cohort and implemented the windowed wrong-language quarantine gate in `verify.py`.

---

## 2. Windowed Language Gate
- **Function:** `verify.looks_like_wrong_language(sample)`
- **Mechanism:** Evaluates sliding windows of prose tokens (`WRONG_LANGUAGE_WINDOW = 300` words).
- **Thresholds:** A window flags a risk if `english_word_frac < ENGLISH_WORD_FRAC_MAX` and anomalous characters or legacy font indicators exceed threshold.
- **Quarantine Outcome:** Documents triggering the gate are marked with failure reason `WRONG_LANGUAGE_RISK` and assigned grade `quarantine`.

---

## 3. Baseline Extraction Results
Across the 194-document population:
- **Total Processed:** 194 documents
- **MDA Located:** 182 documents
- **Accepted:** 127 documents (Medium: 85, High: 42)
- **Low Quality / Rejected:** 53 documents
- **Failed (MDA Not Located):** 12 documents
- **Quarantined:** 2 documents (`INE008A01015` FY2024 and FY2025).

---

## 4. Stability and Downstream Role
P-B1 established the baseline against which subsequent diagnostic streams (P-B3, P-B4, PM1, PM2.1) evaluated behavioral invariance. Its detector thresholds and quarantine gate have remained stable and unedited.

