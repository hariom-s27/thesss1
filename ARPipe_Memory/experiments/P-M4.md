# P-M4 — Annexure-Form Heading Audit & Diagnostic Report

**Status:** HISTORICALLY ESTABLISHED  
**Branch:** `pm4-annexure-audit` @ `e387d6b8879d25af7b6d6946e28aaa635cb97165`  
**Base Commit:** `158a9eac48a3374a9506af8281acb93f49a37a0d`  
**Primary Report:** [`reports/annexure_audit.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pm4-annexure-audit/reports/annexure_audit.md)  
**Companion Data:** `reports/annexure_audit.json`, `annexure_audit_document_labels.csv`

---

## 1. Research Question & Scope
Is the structural form of the MD&A heading systematically associated with company size (cap band) or fiscal era, and does extraction accuracy vary across these forms?

- **Audit Nature:** Diagnostic and audit study only.
- **Production Guardrail:** ZERO production segmentation rules, regex patterns, or triage policies were modified.
- **Integrity Guard:** Holdout labels and holdout outcomes were NOT inspected.

---

## 2. Population Accounting
- **Total Frozen Fit Universe:** 112 documents (20 historical labelled + 92 unlabelled queue)
- **Eligible Documents (Known True Start):** 18 documents
- **Excluded Documents (`NO_VERIFIED_TRUE_START`):** 2 documents

---

## 3. Heading-Form Distribution (18 Eligible Fit Documents)

| Heading Form | N Documents | Fraction | Description |
|---|:---:|:---:|---|
| `standalone_heading` | 12 | 66.67% | Dedicated "Management Discussion and Analysis" heading on its own line/page |
| `annexure_labelled` | 3 | 16.67% | Section formatted explicitly as an Annexure to Directors' Report |
| `combined_with_directors_report` | 1 | 5.56% | Section integrated directly into Directors' Report |
| `other` | 2 | 11.11% | Atypical or non-standard heading formatting |

---

## 4. Methodological Findings & Limits
1. **Dominance of Standalone Headings:** Two-thirds (66.7%) of eligible fit reports use straightforward standalone headings.
2. **Small Sample Constraint:** Only 3 documents exhibit `annexure_labelled` headings.
3. **No Strong Causal Claims:** Because the sample of annexure documents is extremely small ($n=3$), no statistically reliable claim can be made regarding systematic cap-band or era association.

