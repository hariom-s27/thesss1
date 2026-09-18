# P-C0 — Coverage Problem Diagnosis

**Status:** HISTORICALLY ESTABLISHED  
**Mode:** READ-ONLY DIAGNOSIS  
**Worktree:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pc0-coverage-diag`  
**Base Commit:** `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14`  
**Verdict:** `COVERAGE MECHANISM PARTIALLY IDENTIFIED — FURTHER EVIDENCE REQUIRED`  
**Primary Report:** [`reports/coverage_diagnosis.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pc0-coverage-diag/reports/coverage_diagnosis.md)  
**Companion Data:** `reports/coverage_diagnosis.json`, `reports/pc0_sample_manifest.json`

---

## 1. Problem Statement
Diagnosed why ARPipe historical coverage was limited to 22.05% (127/576 accepted company-years), focusing specifically on the 318 company-year loss at the DISCOVERED $\rightarrow$ DOWNLOADED transition.

---

## 2. Three Distinct Zero-Coverage Populations
P-C0 strictly distinguished between three different zero-coverage stages that prior summaries had conflated:

| Zero Population | Fiscal Years | Count ($N$) | Definition |
|---|---|:---:|---|
| **`downloaded = 0`** | 2010, 2014, 2016, 2019, 2020, 2021, 2022, 2023 | **8** | Strictly zero archive downloads acquired |
| **`mda_located = 0`** | 2010, 2014, 2015, 2016, 2019, 2020, 2021, 2022, 2023 | **9** | `downloaded=0` + FY2015 (2 downloaded, 0 located) |
| **`accepted = 0`** | 2010, 2011, 2014, 2015, 2016, 2019, 2020, 2021, 2022, 2023 | **10** | `mda_located=0` + FY2011 (1 downloaded, 1 located, 0 accepted) |

**Relationship:** `downloaded=0` $\subset$ `mda_located=0` $\subset$ `accepted=0`. The phrase "8 zero fiscal years" applies strictly to `downloaded=0`.

---

## 3. Ruled-Out Hypotheses
1. **Pre-Fetch Filter Ruled Out:** `cohort_fetch_manifest.jsonl` contains exactly 194 distinct company-years matching `downloaded=True`. Git investigation proved it was committed at `1d7dc05` for evaluation labeling (`tools/seed_historical_labels.py`), derived *post-hoc* from already-successful downloads in `documents.jsonl`. No code in `cmd_fetch` ever used it to filter candidates prior to fetching.
2. **File Format & Corruption Ruled Out:** Live probes of sampled zero-coverage and control URLs all returned valid ZIP and PDF payloads with correct magic bytes (`PK\x03\x04` and `%PDF`), verified with `qpdf`.

---

## 4. Current Access Variation Observed
Testing a frozen 10-observation sample on 2026-09-17 revealed dramatic temporal volatility:
- **~13:17 UTC (Diagnostic Base Check):** 0/9 successes on `nsearchives.nseindia.com` (connection resets and 45s timeouts).
- **~13:59 UTC (P-C0 Diagnostic):** **10/10 successes** with clean HTTP 200s and valid payloads.
- **Significance:** Within under an hour, identical URLs flipped from total failure to total success on the same network with zero code changes.

---

## 5. Acute Observability Defect Identified
Committed code inspection (`arpipe/fetch.py`, `arpipe/cli.py`) revealed why historical causes were unknowable:
1. `_fetch_pair()` caught network exceptions and printed a single `WARN` line to **stderr only**.
2. When HTTP 403, 429, or 503 retries were exhausted, `fetch_one()` silently fell through to `return None` without logging or raising.
3. Failures never wrote to `documents.jsonl` or any disk file; 0/318 reasons were preserved.

---

## 6. Historical Epistemology & Verdict
- **Historical Invocation:** Strictly **UNKNOWN**. Absence of a download is not evidence that fetch was ever executed for those 318 pairs on 2026-09-11.
- **Primary Mechanism:** Time-varying access condition on the archive host (Confidence: MEDIUM).
- **Minimal Next Repair:** Defined additive, non-blocking per-attempt failure logging (R1).
- **Final Verdict:** `COVERAGE MECHANISM PARTIALLY IDENTIFIED — FURTHER EVIDENCE REQUIRED`.

