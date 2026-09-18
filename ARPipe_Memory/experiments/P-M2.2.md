# P-M2.2 — Exploratory Threshold Sensitivity Study

**Status:** HISTORICALLY ESTABLISHED (Exploratory)  
**Branch:** `pm2.2-threshold-sensitivity` @ `6d91dfa8e8db4c9d570ba98dd234a228e4d3c57a`  
**Base Commit:** `158a9eac48a3374a9506af8281acb93f49a37a0d`  
**Primary Report:** [`reports/pm2_2_threshold_study.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pm2.2-sensitivity/reports/pm2_2_threshold_study.md)  
**Companion Data:** `reports/pm2_2_threshold_candidates.json`, `pm2_2_threshold_study.json`

---

## 1. Study Scope & Mandatory Guardrails
- **Exploratory Status:** Pre-gold, sensitivity analysis only.
- **Production Gate Preserved:** `ORPHAN_START_FRAC_MAX = 0.03` remained **strictly unchanged**.
- **Rule:** Threshold recalibration is prohibited until formal gold-standard evaluation on held-out labels is executed.

---

## 2. Predeclared Candidate Grid Results

| Threshold ($T$) | Rationale | Native Page Frac $> T$ | Native Doc Frac Flagged | OCR Page Frac $> T$ | OCR Doc Frac Flagged |
|:---:|:---|:---:|:---:|:---:|:---:|
| **0.020** | Lower-band sensitivity | 28.57% | 71.05% | 47.01% | 100.0% |
| **0.025** | Lower-band sensitivity | 26.99% | 70.39% | 46.27% | 100.0% |
| **0.030** | Current production gate | **25.17%** | **67.76%** | **41.79%** | **100.0%** |
| **0.035** | Near-current upper sensitivity | 22.97% | 65.79% | 36.57% | 75.00% |
| **0.040** | Upper-band candidate | **21.48%** | **63.82%** | **31.34%** | **75.00%** |
| **0.050** | Wider upper sensitivity | 18.45% | 57.24% | 28.36% | 75.00% |
| **0.060** | Wider upper sensitivity | 15.96% | 55.26% | 26.12% | 75.00% |

---

## 3. Analysis & Epistemological Status of `.040`
1. **Behavior at 0.040:**
   - Drops native page rejection fraction from 25.2% to 21.5% (-3.7 pp).
   - Drops OCR page rejection fraction from 41.8% to 31.3% (-10.5 pp).
   - Reduces flagged OCR document fraction from 100% to 75%.
2. **Exploratory Constraint:**
   - While `.040` shows attractive trade-offs in reducing over-flagging on acceptable pages, it remains strictly **EXPLORATORY**.
   - No production threshold change may occur without evaluating downstream impact against human gold labels (~103 FIT labels).

