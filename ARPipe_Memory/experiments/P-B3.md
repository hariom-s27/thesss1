# P-B3 — Legacy-Font Corpus Audit

**Status:** HISTORICALLY ESTABLISHED  
**Mode:** MEASURE-ONLY DIAGNOSTIC AUDIT  
**Base Commit:** `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14`  
**Primary Report:** [`reports/legacy_font_corpus_measurement.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-0.1.0/reports/legacy_font_corpus_measurement.md)  
**Companion Data:** `reports/legacy_font_corpus_measurement.json`, `.csv`

---

## 1. Research Question
What is the empirical prevalence of legacy Indian fonts (Devanagari encoded as Latin codepoints, e.g. Akruti, Shree-Dev) across the ARPipe corpus, and does legacy font presence correlate with native text extraction corruption?

---

## 2. Population Accounting
- **Population Manifest:** `live_store/documents.jsonl`
- **Total Documents:** 194 verified PDF documents
- **Total Physical Pages:** 37,917 physical pages across 36 listed companies
- **Measurement Timestamp:** `2026-09-16T21:31:44.588677+00:00`

---

## 3. Descriptive 2×2 Matrix (Resolved Pages)

| Dimension | Native Text Apparently Clean | Native Text Apparently Corrupted |
|---|:---:|:---:|
| **Legacy-Font Evidence Present** | **A:** 1,625 pages | **B:** 437 pages |
| **No Supported Legacy-Font Evidence** | **D:** 33,986 pages | **C:** 826 pages |

### Reconciliation
- **Total Resolved Pages ($A + B + C + D$):** 36,874 pages
- **Unresolved / Unknown Pages:** 1,043 pages
- **Sum:** $36,874 + 1,043 = 37,917$ pages (Exact Match)

---

## 4. Key Findings
1. **Prevalence:** Legacy font evidence is present on 2,075 pages (5.47% of all pages), concentrated across 9 documents (4.64%) and 3 companies.
2. **Native Text Independence:**
   - 78.3% of pages with legacy font evidence (1,625 / 2,075) have **clean native text**.
   - 65.4% of corrupted pages (826 / 1,263) have **no legacy font evidence**.
3. **Conceptual Distinction:** **Legacy-font presence $\ne$ text corruption.** The presence of legacy font encodings in PDF streams does not imply that the extracted text layer is unusable.
4. **P-B1 Overlap:** The 2 documents quarantined by P-B1 account for 1,137 legacy font pages (54.8% of all corpus legacy-font pages), leaving 7 legacy-font documents unquarantined because their extracted body text passed language thresholds.

