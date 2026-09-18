# P-B4 — Additive Script Telemetry & Invariance Validation

**Status:** HISTORICALLY ESTABLISHED  
**Primary Report:** [`reports/pb4_corpus_validation.json`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-0.1.0/reports/pb4_corpus_validation.json)  
**Baseline Metrics:** `reports/b4_baseline_metrics.json`

---

## 1. Objective and Additions
Added per-page and per-document script telemetry to provide visibility into Devanagari and English language content without altering pipeline behavior or extraction outcomes.

### Added Telemetry Fields
- `dominant_script`: Classified as `english`, `bilingual`, or `unknown`.
- `devanagari_frac`: Fraction of Devanagari Unicode codepoints.
- `english_word_frac`: Fraction of recognizable English vocabulary words.
- `legacy_font_suspected`: Boolean indicator for font name and character encoding anomalies.

---

## 2. Corpus Coverage (194 Documents, 37,917 Pages)
- **Pages with Script Map:** 37,917 (100%)
- **Pages with Devanagari Fraction:** 36,866 (97.2%)
- **Pages with English Word Fraction:** 36,309 (95.8%)
- **Dominant Script Distribution:**
  - `english`: 36,755 pages (96.9%)
  - `unknown`: 1,160 pages (3.1%)
  - `bilingual`: 2 pages (<0.01%)

---

## 3. Strict Behavioral Invariance Verification
Side-by-side execution against pre-B4 baseline verified zero drift across all 194 documents:

| Invariance Dimension | Baseline | Post-B4 | Difference |
|---|:---:|:---:|:---:|
| Total Documents Processed | 194 | 194 | 0 |
| MDA Located Documents | 182 | 182 | 0 |
| MDA Not Located Documents | 12 | 12 | 0 |
| Page Count Mismatches | 0 | 0 | 0 |
| MDA Start Page Diffs | 0 | 0 | 0 |
| MDA End Page Diffs | 0 | 0 | 0 |
| Grade / Confidence Diffs | 0 | 0 | 0 |
| Accepted Count (Medium + High) | 127 | 127 | 0 |
| Low Quality Count | 53 | 53 | 0 |
| Quarantine Count | 2 | 2 | 0 |
| Failure Reason Distribution | Identical | Identical | 0 |

