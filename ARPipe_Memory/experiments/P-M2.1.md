# P-M2.1 — Native vs. OCR at True Page Grain

**Status:** HISTORICALLY ESTABLISHED  
**Branch:** `pm2.1-pagegrain-native-vs-ocr` @ `158a9eac48a3374a9506af8281acb93f49a37a0d`  
**Primary Report:** [`reports/pm2_pagegrain_native_vs_ocr.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pm2.1-pagegrain/reports/pm2_pagegrain_native_vs_ocr.md)  
**Companion Data:** `reports/pm2_pagegrain_native_vs_ocr.json`

---

## 1. Research Question
Is OCR text extraction materially different from native PDF extraction in its reading-order quality (`orphan_start_frac`) when evaluated at true physical page grain rather than document grain?

---

## 2. Population Accounting Reconciliation
- **Total Corpus Documents:** 194
- **Located Documents:** 182 (12 unlocated documents excluded due to `mda_not_located`)
- **Total MD&A Physical Pages:** 2,734
- **Measured Page Scores:** 2,547 pages
  - Native Pages: 2,412 measured (180 null/unmeasured)
  - OCR Pages: 134 measured (7 null/unmeasured)
  - Unknown Provenance: 1 measured (0 unmeasured)
- **Null / Unmeasured Pages:** 187 pages (all due to `fewer_than_min_paragraphs` [< 2 paragraphs])
- **Reconciliation Check:** $2,412 + 134 + 1 + 187 = 2,734$ (Verified True).

---

## 3. Threshold Diagnostics at Page Grain

| Metric | Native Pages | OCR Pages | Delta (OCR − Native) |
|---|:---:|:---:|:---:|
| Total Measured Pages ($N$) | 2,412 | 134 | — |
| Independent Documents ($N_{docs}$) | 169 | 21 | — |
| Median `orphan_start_frac` | 0.0000 | 0.0000 | 0.0000 |
| P75 | 0.0303 | 0.0620 | +0.0317 |
| P90 | 0.0833 | 0.1250 | +0.0417 |
| P95 | 0.1221 | 0.1667 | +0.0446 |
| Maximum Score | 0.6471 | 0.4286 | −0.2185 |
| Pages $> 0.03$ | 607 | 56 | — |
| **Fraction $> 0.03$** | **25.17%** | **41.79%** | **+16.63%** |

---

## 4. Key Epistemological Constraints
1. **Elevated Tail Risk in OCR:** While medians are both 0.0000, OCR pages show higher 75th/90th/95th percentiles and a significantly higher proportion exceeding 0.03 (41.8% vs. 25.2%).
2. **Document Clustering Warning:** The 134 OCR pages come from only 21 independent documents (5 pure-OCR + 16 mixed). High intra-document correlation requires inferential claims to respect the effective sample size ($N=21$).

