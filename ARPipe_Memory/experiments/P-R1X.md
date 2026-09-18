# P-R1X — Instrumented Acquisition Telemetry Pilot

**Protocol:** P-R1X v1.2 (Final Execution Protocol)  
**Status:** ADJUDICATED / CLOSED OUT (`INCOMPLETE AS A THREE-WINDOW TEMPORAL EXPERIMENT; VALID TWO-WINDOW PRIMARY SUBSET + POST-INTERRUPTION SUPPLEMENTAL DATA`)  
**Engineering Base:** `56497721cb68c4831e6f225074b6bd7ea17bffb0` (Frozen R1 Implementation)  
**Analytical Reference:** `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870` (`reports/r1_telemetry_analysis.md`)  
**Execution Worktree:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-execution` (branch `pr1x-execution`)  
**Execution Commit:** `0b1d595407eacb13b115811cdb610b3e1f56a767`  
**Adjudication Worktree:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-adjudication` (branch `pr1x-adjudication`)  
**Adjudication Commit:** `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32`  
**Primary Adjudication Report:** [`reports/pr1x_adjudication.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pr1x-adjudication/reports/pr1x_adjudication.md)  
**Primary Verdict:** `VALID TWO-WINDOW TEMPORAL SUBSET — NO REPRODUCIBLE CURRENT FAILURE — HISTORICAL CAUSE UNKNOWN`  
**Repair-Experiment Verdict:** `INSUFFICIENT EVIDENCE`  

---

## 1. Experimental Design & Pre-Registered Structure
Designed to test the frozen 10-observation P-C0 sample (5 historical zero-download targets + 5 controls) across 3 pre-scheduled temporal windows spaced at 90-minute intervals using the unadorned frozen R1 client (`httpx.Client`, Chrome Linux User-Agent, no session cookies or custom headers) and `HostLimiter` (1.5s interval).

### Predeclared Windows
- **Window 1 ($T_0$):** `2026-09-17 20:05:00 UTC`
- **Window 2 ($T_0 + 90\text{m}$):** `2026-09-17 21:35:00 UTC`
- **Window 3 ($T_0 + 180\text{m}$):** `2026-09-17 23:05:00 UTC`

---

## 2. Forensic Adjudication of Execution

| Window | Scheduled Start (UTC) | Actual Start (UTC) | Start Latency | Observations | Outcome | Window Status | Analysis Admissibility |
|---|---|---|---|---|---|---|---|
| **Window 1** | 2026-09-17 20:05:00 UTC | 2026-09-17T20:05:00.001Z | +1.4 ms | 10 | 10/10 Success | **VALID** | **PRIMARY ANALYSIS ELIGIBLE** |
| **Window 2** | 2026-09-17 21:35:00 UTC | 2026-09-17T21:35:00.002Z | +2.1 ms | 10 | 10/10 Success | **VALID** | **PRIMARY ANALYSIS ELIGIBLE** |
| **Window 3** | 2026-09-17 23:05:00 UTC | 2026-09-18T08:17:46.015Z | +9h 12m 46s | 10 | 10/10 Success | **POST_INTERRUPTION_SUPPLEMENTAL** | **EXCLUDED FROM PRIMARY TEMPORAL SET** |

### Interruption Mechanism & Governing Rule
- **Interruption Evidence:** During the inter-window wait loop between Window 2 and Window 3, the host machine entered overnight sleep/suspend. The runner process blocked in `time.sleep()` and resumed at 08:17:46 UTC on 2026-09-18, immediately firing Window 3.
- **Governing Rule:** Runbook Section 10 strictly prohibits substituting timestamps or continuing under changed execution state. Window 3 cannot serve as a scheduled third temporal window. Observations are preserved as supplemental evidence of current endpoint reachability.

---

## 3. Adjudicated Findings

1. **Primary Temporal Analysis ($N = 20$):**
   - 10 target observations (`DOWNLOAD_ZERO_FY`) across Windows 1 & 2: 10/10 successful (100%).
   - 10 control observations (`DOWNLOAD_NONZERO_FY_CONTROL`) across Windows 1 & 2: 10/10 successful (100%).
   - Target vs. Control Difference: Exactly 0.0% difference.
   - Outcome Variance Across Valid Windows: 0.0%.
2. **Supplemental Run ($N = 10$):**
   - 5 targets + 5 controls in Window 3: 10/10 successful (100%).
3. **Bitwise Reproducibility:**
   - 10/10 document blobs yielded bitwise-identical SHA-256 CAS hashes across all three runs.
4. **Failure Signal:**
   - Exactly 0 retries, 0 connection errors, 0 timeouts, 0 HTTP error codes (403, 429, 503), and 0 safety stop signals.
5. **Historical Failure Not Reproduced:**
   - The historical acquisition failure mode (`downloaded=False`) was **NOT OBSERVED** and **NOT REPRODUCED** under test conditions.
6. **Overclaims Corrected:**
   - Claims of "COMPLETED — ALL 3 WINDOWS EXECUTED" and "30/30 across 3 windows" corrected to a valid two-window temporal subset ($N=20$) and supplemental run ($N=10$).

---

## 4. Future Repair-Experiment Decision: INSUFFICIENT EVIDENCE
- **Verdict:** `INSUFFICIENT EVIDENCE`
- **Rationale:**
  1. Baseline acquisition achieved 100% success on the target sample without custom headers, cookies, or pacing adjustments.
  2. The failure mode was not reproduced; there is no observed failure signal to repair.
  3. The historical root cause of the 2026-09-11 losses remains unknown.
  4. High-concurrency burst crawling and daytime market-hours behavior remain untested.
  5. Designing an acquisition repair without reproducing the failure would be unguided speculation.
  6. Does NOT imply the acquisition problem is solved.

---

## 5. Next Project Task
`HISTORICAL ACQUISITION-CAUSE EVIDENCE AUDIT`: Audit surviving historical artifacts from 2026-09-11 (logs, manifests, fetch records, HTTP traces) to identify the historical failure layer before contemplating any engineering repair.
