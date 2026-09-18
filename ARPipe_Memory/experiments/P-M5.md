# P-M5 — Coverage Funnel Snapshot & Stage Transition Audit

**Status:** HISTORICALLY ESTABLISHED / FROZEN EVIDENCE  
**Branch:** `pm5-coverage-funnel` @ `7292111149ab1cf9fc8d638d1f08023e3fcb13d5`  
**Primary Report:** [`reports/coverage.json`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pm5-coverage/reports/coverage.json) (SHA-256: `c84166741d36a9774b7c9f29d71ea9583934d98c2ab153e651ec66ec4d371bcf`)  
**Stage Table:** [`reports/pm5_stage_table.csv`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pm5-coverage/reports/pm5_stage_table.csv) (SHA-256: `30e93b59ac689f00fab182583fb25883322e429be42b4ba14e13a1011b916dc9`)

---

## 1. Funnel Accounting & Headline Coverage
Evaluating 36 companies over 16 fiscal years (FY2010–FY2025 = 576 expected company-years):

| Funnel Stage | Count | % of Expected (576) | % of Prior Stage | Transition Loss |
|:---|:---:|:---:|:---:|:---:|
| **1. EXPECTED** | **576** | 100.00% | — | — |
| **2. DISCOVERED** | **512** | 88.89% | 88.89% | 64 company-years |
| **3. DOWNLOADED** | **194** | 33.68% | 37.89% | **318 company-years (62.11% loss)** |
| **4. IDENTITY_VERIFIED** | **170** | 29.51% | 87.63% | 24 company-years |
| **5. MDA_LOCATED** | **182** | 31.60% | 107.06%* | -12 company-years (non-monotonic) |
| **6. ACCEPTED** | **127** | **22.05%** | 69.78% | 55 company-years |

*\*Non-monotonicity: 12 company-years had `mda_located=True` while `identity_verified=False` (e.g., `INE007A01025::FY2012`), demonstrating that identity and section location are independent checks in ARPipe.*

---

## 2. The Dominant Pipeline Loss: 318 Company-Years
- **Magnitude:** The transition from DISCOVERED (512) to DOWNLOADED (194) accounts for **318 lost company-years**.
- **Proportion:** Represents **62.11% of all discovered reports** and dwarfs all downstream extraction losses combined (total extraction losses = 67 company-years).
- **Reason-Code Completeness:** **0.0%** (0 of 318 DOWNLOAD losses and 0 of 64 DISCOVERY losses recorded structured failure reasons; all coded `REASON_CODE_MISSING`).

---

## 3. Historical Timestamp Clustering
Inspection of client-side `fetched_at` timestamps in `reports/pm5_source_snapshots/live_store_documents.jsonl` revealed:
- **Single Continuous Window:** All 194 historical successful downloads completed within **one 4.5-minute window** on 2026-09-11 between `10:28:44` and `10:33:08` UTC.
- **FY Bursts:**
  - Burst 1: FY2012 / 2013 (10:28:44–10:29:58 UTC)
  - Burst 2: FY2017 / 2018 (10:30:04–10:31:26 UTC)
  - Burst 3: FY2024 / 2025 (10:31:29–10:33:08 UTC)
- **Significance:** Rules out separate partial crawls across different days; confirms a single burst execution.

---

## 4. Two-Funnel Conceptual Model
P-M5 established that treating ARPipe as a single linear funnel is invalid. The process consists of two distinct funnels:

```
ACQUISITION FUNNEL:
Expected (576) ──> Discovered (512) ──> Downloaded (194) ──> Valid PDF (194) ──> Identity Verified (170)

EXTRACTION FUNNEL:
Valid PDF (194) ──> MDA Located (182) ──> Language/OCR Clean (180) ──> Quality Passing (127) ──> Accepted (127)
```
The 127 accepted documents must NEVER be treated as the intended universe denominator.
