# ARPipe — Historical Acquisition-Cause Evidence Audit

**Task:** Historical Acquisition-Cause Evidence Audit (2026-09-11 Acquisition Gap Investigation)  
**Status:** COMPLETE / ADJUDICATED HISTORICAL BASELINE  
**Investigation Mode:** LOCAL / OFFLINE READ-ONLY HISTORICAL FORENSICS  
**Audit Worktree:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-historical-audit` (branch `pr1x-historical-audit`)  
**Base Commit:** `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32` (P-R1X Forensic Adjudication)  
**Audit Commit:** `1b6fd1f496b3634ee57bef6b926f7a79524c1cac` (`Historical audit: classify 2026-09-11 acquisition losses`)  
**Primary Audit Report:** [`reports/historical_acquisition_cause_audit.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pr1x-historical-audit/reports/historical_acquisition_cause_audit.md)  
**Primary Machine-Readable Report:** [`reports/historical_acquisition_cause_audit.json`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pr1x-historical-audit/reports/historical_acquisition_cause_audit.json)  
**Primary Verdict:** `POPULATION RECONCILED (318/318) — HISTORICAL REASONS UNKNOWN (0.0% REASONS PERSISTED) — INSUFFICIENT HISTORICAL EVIDENCE FOR TARGETED EXPERIMENT`  
**Next Task:** `INFORMATION-GAP / OBSERVABILITY TASK` (Roadmap Task 2: Evidence-Driven Acquisition Strategy)  

---

## 1. Investigation Scope & Historical Gap

This forensic audit investigated the surviving physical evidence surrounding the original 2026-09-11 acquisition gap:
- **Expected Universe:** 576 company-years (36 companies &times; 16 fiscal years FY2010–2025)
- **Discovered Candidates:** 512 company-years (88.89%)
- **Downloaded Documents:** 194 company-years (33.68% of expected; 37.89% of discovered)
- **Transition Loss Under Investigation:** Exactly **318 company-years** lost between `DISCOVERED` and `DOWNLOADED`.

### Operating Rules
- Strictly read-only local forensics.
- Zero live network requests, zero probe pings, zero re-downloads.
- No rerun of P-R1X or production pipeline.
- No production code edits.
- Cryptographic hash verification before and after inspection across all sources.

---

## 2. Reconstructed Loss Population (318 of 318)

The 318 loss observations were reconstructed with exact identity reconciliation from `reports/pm5_stage_table.csv` and cross-referenced with `cohort_reports.jsonl`:
- **Unique Identities Reconstructed:** Exactly 318 of 318
- **Duplicate Rows:** 0
- **Missing Identities:** 0
- **Invented Identities:** 0
- **Discovered Candidate URLs:** 100% of 318 have valid candidate URLs (104 have 1 candidate, 46 have 2, 164 have 3, 4 have 4).
- **Candidate Sources:** 212 primary NSE (`nsearchives.nseindia.com`), 106 primary BSE (`bseindia.com`).
- **Candidate Extensions:** 211 ZIP archives, 107 PDF files.
- **Fiscal Year Distribution:**
  - 8 zero-download fiscal years: FY2010 (28), FY2014 (30), FY2016 (31), FY2019 (32), FY2020 (33), FY2021 (34), FY2022 (35), FY2023 (36) &rarr; Subtotal: 259 losses.
  - 2 partial-loss fiscal years: FY2011 (28 losses / 1 download), FY2015 (31 losses / 2 downloads) &rarr; Subtotal: 59 losses.
  - 6 complete-download fiscal years: FY2012, FY2013, FY2017, FY2018, FY2024, FY2025 &rarr; 0 losses.

Full loss ledger is permanently recorded in [`reports/historical_loss_ledger.csv`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pr1x-historical-audit/reports/historical_loss_ledger.csv).

---

## 3. Historical Telemetry Audit & Observability Void

1. **Reason-Code Completeness:** Exactly **0.0% (0 of 318)**.
   - The historical crawl executed on 2026-09-11 persisted zero per-attempt logs, zero HTTP status codes, zero socket exceptions, and zero terminal error codes to disk (`pm5_reason_code_completeness.csv` = 0.0%).
   - All 318 records are classified as `REASON_CODE_MISSING`.
2. **Request Invocation State:** **`REQUEST_NOT_CONFIRMED`**.
   - Governed by the mandatory epistemic rule: `NO_REQUEST_EVIDENCE != REQUEST_DID_NOT_OCCUR`.
   - Candidate URLs were discovered, but no record confirms whether HTTP requests were actually dispatched for the 318 losses.
3. **The Silent Drop Path:**
   - In pre-R1 `arpipe/fetch.py:fetch_one()`, encountering 403, 429, or 503 across all 3 retries executed `time.sleep()` and `continue` without setting `last_err`.
   - Upon loop exhaustion, `last_err` remained `None`, causing `fetch_one()` to execute `return None` **silently**—producing zero stderr prints and zero disk records.
4. **Intermediate Manifest Discovery:**
   - Contemporaneous file `cohort_fetch_manifest.jsonl` was written at 10:28:22 UTC on 2026-09-11 (22s before the first successful download began at 10:28:44 UTC).
   - It contains 460 rows covering **exactly the 194 successful download pairs** and **omits all 318 losses**.
   - Whether it served as an input manifest to `cmd_fetch` or was exported post-hoc cannot be proven due to absence of shell transcripts (`PLAUSIBLE_BUT_UNPROVEN`).

---

## 4. Evaluation of Failure Hypotheses

| Hypothesis | Direct Evidence | Indirect Evidence | Contradicting Evidence | Final Audit Status |
|:---|:---|:---|:---|:---:|
| **HTTP 403/429/503 Rejection** | None (0 records) | Code gap: silent `return None` without logging | 0/80 rejections in contemporary open windows (P-C0, P-C0R, P-R1X) | `PLAUSIBLE_BUT_UNPROVEN` |
| **Transport Failure (Reset / Connect)** | None (0 records) | P-C0 Step 3 experienced `CURLE_RECV_ERROR 56` | 0/20 resets in P-R1X valid windows; 50/50 success in P-C0R | `PLAUSIBLE_BUT_UNPROVEN` |
| **Timeout (Connect / Read)** | None (0 records) | P-C0 Step 3 experienced 45s read timeouts | 0/30 timeouts in P-R1X; mean response < 3.5s | `PLAUSIBLE_BUT_UNPROVEN` |
| **Payload / Format Corruption** | None (0 records) | `qpdf` fallback pass existed in code | Sampled URLs from zero FYs yielded 100% valid ZIP/PDF files with matching magic bytes and bitwise CAS hashes | **`RULED_OUT`** (for tested sample) |
| **Acquisition Invocation Gap** | Intermediate manifest written @ 10:28:22 UTC omitted all 318 losses | `cmd_fetch` accepts manifest filter | Terminal transcripts not preserved | `PLAUSIBLE_BUT_UNPROVEN` |
| **URL Syntax / Malformation Defect** | None | None | All 318 candidate URLs are valid, syntactically well-formed regulatory links | **`RULED_OUT`** |
| **Client Configuration Asymmetry** | None | `cmd_discover` used cookies; `cmd_fetch` was unseeded | P-C0R Part 6 trial showed 10/10 paired comparisons succeeded identically with/without cookies | **`RULED_OUT`** (as technical barrier) |
| **Temporal / Time-of-Day Policy** | All 194 successes occurred in one 4.5-min burst | P-C0 observed sub-hour shift (0/9 failures &rarr; 10/10 successes in 50m) | P-R1X Window 3 ran during Indian market hours (13:47 IST) and achieved 10/10 success | `PLAUSIBLE_BUT_UNPROVEN` |
| **Concurrency / Burst Load Throttle** | None (0 records) | `cmd_fetch` used 4 concurrent worker threads | 194 documents downloaded in 4.5 min (~1.36s/doc) under 4 workers | `PLAUSIBLE_BUT_UNPROVEN` |
| **Retry Exhaustion** | None (0 records) | `fetch_one()` hardcoded `retries = 3` | 20/20 valid requests succeeded on Attempt 1 in P-R1X | `PLAUSIBLE_BUT_UNPROVEN` |

---

## 5. Next-Experiment Decision: INSUFFICIENT HISTORICAL EVIDENCE FOR TARGETED EXPERIMENT

```
============================================================
NEXT-EXPERIMENT DECISION:
INSUFFICIENT HISTORICAL EVIDENCE FOR TARGETED EXPERIMENT
============================================================
```

### Governing Rationale
Under Section 33 of the audit protocol, a targeted experiment is justified only if:
1. A specific historical mechanism is sufficiently evidenced,
2. The mechanism is testable,
3. Unresolved confounders are explicit, and
4. The experiment can be designed without inventing missing historical facts.

Because surviving historical records contain **0.0% reason codes**, zero HTTP telemetry, zero socket error traces, and cannot even confirm whether requests were invoked (`REQUEST_NOT_CONFIRMED`), designing a targeted repair or reproduction experiment claiming to test a specific historical failure mechanism would constitute **unguided speculation and invention of unrecorded historical facts**.

### Required Next Task
In accordance with Section 40 of the protocol:
- **Next Task:** **`INFORMATION-GAP / OBSERVABILITY TASK`**
- **Roadmap Identifier:** `Task 2 (Evidence-Driven Acquisition Strategy: Classify Recoverable vs. Excluded vs. Unrecoverable)`
- **Objective:** Deploy structured R1 attempt-level telemetry across the full 318 un-downloaded cohort to systematically categorize each company-year into Category A (Recoverable Technical Gaps), Category B (Systematic URL/Parser Defects), or Category C (Genuine Archival Unavailability).

---

## 6. Cryptographic Chain of Custody & Audit Artifacts

All 29 source artifacts inspected during the audit were pre-hashed and post-hashed. SHA-256 digests were 100% identical (`pre_hash == post_hash`). Zero source files were modified.

The 8 authoritative audit deliverables are permanently committed in `1b6fd1f496b3634ee57bef6b926f7a79524c1cac` on branch `pr1x-historical-audit`:
1. `reports/historical_loss_ledger.csv` (SHA: `cb2aa1176d34...`, 228,223 bytes)
2. `reports/historical_evidence_register.csv` (SHA: `86c94ba16239...`, 7,145 bytes)
3. `reports/historical_configuration_snapshot.json` (SHA: `0b979ce0f52c...`, 2,478 bytes)
4. `reports/historical_hypothesis_matrix.csv` (SHA: `0f98cfdbab23...`, 4,936 bytes)
5. `reports/historical_git_timeline.md` (SHA: `adce8ada6016...`, 7,174 bytes)
6. `reports/historical_acquisition_cause_audit.json` (SHA: `9e1233a0e0cc...`, 10,651 bytes)
7. `reports/historical_acquisition_cause_audit.md` (SHA: `3294afc37ddb...`, 23,518 bytes)
8. `reports/historical_audit_hashes.json` (SHA: `eef359b0017d...`, 12,830 bytes)
