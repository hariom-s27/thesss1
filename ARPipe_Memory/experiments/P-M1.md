# P-M1 — Per-Page `orphan_start_frac` Diagnostic & Order QC

**Status:** HISTORICALLY ESTABLISHED  
**Branch:** `pm1-canonical` @ `c9d71bb127fcc46d690a8fbd9e5088b7049b6c05`  
**Primary Report:** [`reports/pm1_per_page_orphan.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-0.1.0/reports/pm1_per_page_orphan.md)  
**Deliverables:** `arpipe/verify.py`, `arpipe/cli.py` (`arpipe orderqc`), `reports/pm1_per_page_orphan.json`

---

## 1. Central Finding
> **84 of 194 documents have at least one page with `orphan_start_frac > 0.03` while their document-level score remains `≤ 0.03`.**

Document-level aggregation acts as a low-pass filter that dilutes localized reading-order corruption across multi-page sections.

---

## 2. Metric Source and Page Attribution
- **Identical Computation:** The page-level calculation uses the exact same paragraph-reconstruction and orphan-detection scoring algorithm (`_score_paragraphs`) as the document-level metric (`verify.order_quality`).
- **Attribution Rule:** A reconstructed paragraph is attributed to the physical page containing its first non-whitespace source character.
- **Diagnostic Thresholds:**
  - `PAGE_ORPHAN_DIAGNOSTIC_THRESHOLD = 0.03`
  - `PAGE_ORPHAN_MIN_PARAGRAPHS = 2`

---

## 3. Production Boundaries
- **Task Nature:** Purely additive diagnostic audit.
- **Zero Drift:** MD&A candidate detection, ranking, arbitration, reading order, `_column_cut`, extracted text boundaries, grading, acceptance/rejection, OCR routing, and `ORPHAN_START_FRAC_MAX` remained 100% untouched and verified identical.
- **Identified Edge Case:** Discovered that broad pattern matching on `is given below` could misidentify pointer language as actual section headings (subsequently addressed in P33 benchmark).

