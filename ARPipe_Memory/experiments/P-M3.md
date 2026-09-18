# P-M3 — Scan-Quality Measurement Report

**Status:** HISTORICALLY ESTABLISHED  
**Branch:** `pm3-scan-quality` @ `ec48e6454e278c789268519fe1f63d18374cd6b4`  
**Primary Report:** [`reports/pm3_scan_quality.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pm3-scan-quality/reports/pm3_scan_quality.md)  
**Companion Data:** `reports/pm3_scan_quality.json`, `pm3_scan_quality_by_year.csv`, `pm3_scan_quality_by_cap_band.csv`

---

## 1. Research Question & Explicit Boundaries
What is the empirical prevalence of scanned/raster content across the 194-document ARPipe corpus, and how do physical scan quality metrics distribute across fiscal eras and company size bands?

### Fundamental Methodological Boundary
```
SCAN / INPUT QUALITY  ≠  OCR QUALITY  ≠  EXTRACTION CORRECTNESS  ≠  OCR FAILURE
```
A poor scan does not automatically mean OCR will fail, and a clean scan does not guarantee correct reading-order or section-boundary extraction.

---

## 2. Population Accounting (194 Documents, 37,917 Pages)
- **Native-Only Pages:** 25,257 pages (66.61%)
- **Pages with Raster Content:** 12,464 pages (32.87%)
  - Full-Page Raster ($\ge 50\%$ page area): 2,909 pages (7.67%)
  - Partial Raster: 9,555 pages (25.20%)
- **Measurable Full-Page Raster Pages:** 2,909 pages (100.0% coverage)

---

## 3. Physical Component Distributions (2,909 Full-Page Raster Pages)

| Metric | Method & Direction | Min | P25 | Median | P75 | P95 | Max |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **DPI** | Min width/height placed DPI | 0.09 | 96.24 | **150.00** | 165.55 | 300.00 | 600.88 |
| **Skew Angle (°)** | Projection profile variance | -5.00 | -0.40 | **-0.20** | -0.20 | 0.40 | 5.00 |
| **Contrast** | Interdecile $(P_{95} - P_{05})/255$ | 0.00 | 0.3569 | **0.5412** | 0.7176 | 0.9216 | 1.0000 |
| **Noise / Speckle** | 3×3 median residual (higher = noisier) | 0.00 | 0.0058 | **0.0102** | 0.0155 | 0.0261 | 0.0622 |
| **Blur / Sharpness** | Laplacian variance (higher = sharper) | 0.59 | 1,261.26 | **2,690.90** | 5,245.90 | 10,324.18 | 31,994.88 |

---

## 4. Key Findings by Strata
1. **Era Concentration:** Older filings contain substantially more raster pages (FY2011: 100% of pages in lone document; FY2013: 21.5% raster). Modern filings are predominantly native text (FY2024: 6.1% raster; FY2025: 7.3% raster).
2. **Cap Band Distribution:** Micro-cap companies exhibit the highest raster fraction (14.8% of pages), whereas large-cap companies exhibit only 4.0% raster pages.
3. **Composite Scoring Status:** No arbitrary composite quality formula was fitted or enforced; raw physical metrics remain primary.

