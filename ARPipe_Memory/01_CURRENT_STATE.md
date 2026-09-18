# ARPipe — Current Project State

**Last Updated:** 2026-09-17
**Vault Root:** `D:\sem_iitk\sem9\thesis\ARPipe_Memory`

---

## 1. What phase are we in?
**POST-P-R1X FORENSIC CLOSEOUT / HISTORICAL CAUSE AUDIT**

P-R1X v1.2 execution has been forensically adjudicated against the frozen protocol and Runbook Section 10 Interruption Rule.

> [!IMPORTANT]
> **GOVERNING ADJUDICATION STATEMENT:**  
> P-R1X did not produce a clean three-window temporal experiment. It produced a valid two-window primary temporal subset plus a post-interruption supplemental observation run.

We are now in the post-adjudication memory closeout phase, transitioning to the Historical Acquisition-Cause Evidence Audit.

---

## 2. What was the last completed task?
**P-R1X: Forensic Adjudication & Memory Closeout**

- **Task Status:** **COMPLETE / ADJUDICATED**
- **Experimental Status:** `INCOMPLETE AS A THREE-WINDOW TEMPORAL EXPERIMENT (VALID TWO-WINDOW PRIMARY SUBSET + POST-INTERRUPTION SUPPLEMENTAL DATA)`
- **Protocol Version:** `P-R1X v1.2`
- **Adjudication Worktree:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-adjudication` (branch `pr1x-adjudication`)
- **Adjudication Commit SHA:** `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32`
- **Execution Worktree:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-execution` (branch `pr1x-execution`, UNTOUCHED)
- **Execution Commit SHA:** `0b1d595407eacb13b115811cdb610b3e1f56a767`
- **Engineering Base SHA:** `56497721cb68c4831e6f225074b6bd7ea17bffb0` (Frozen R1 Implementation)
- **Analytical Reference SHA:** `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870`
- **Committed Adjudication Artifacts:**
  - `reports/pr1x_adjudication.md` (Full forensic report with all 18 required sections)
  - `reports/pr1x_adjudication.json` (Machine-readable comprehensive adjudication findings)
  - `reports/pr1x_temporal_validity.json` (Per-window validity classifications: W1 VALID, W2 VALID, W3 POST_INTERRUPTION_SUPPLEMENTAL)
  - `reports/pr1x_memory_update_notes.md` (Memory reconciliation specifications)
  - `reports/pr1x_artifact_hashes.json` (Canonical SHA-256 manifests of execution and adjudication files)
- **Key Evidence Established:**
  - *Window 1:* VALID (Started on schedule: 2026-09-17 20:05:00.001 UTC; delay 1.4ms; 10/10 success).
  - *Window 2:* VALID (Started on schedule: 2026-09-17 21:35:00.002 UTC; delay 2.1ms; 10/10 success).
  - *Window 3:* POST_INTERRUPTION_SUPPLEMENTAL (Delayed by 9h 12m 46s due to host sleep / process suspension during nominal inter-window wait loop; resumed 2026-09-18 08:17:46 UTC; 10/10 success).
  - *Primary Temporal Analysis:* 20 observations across valid Windows 1 and 2 (10 target, 10 control; 100% success; 0 difference; bitwise-identical SHA-256 CAS blob payloads).
  - *Supplemental Dataset:* 10 observations from Window 3 retained separately as descriptive current-access evidence.
  - *Historical Causality:* UNKNOWN / NOT ESTABLISHED. Historical failure mode (`downloaded=False`) was NOT REPRODUCED.
  - *Future Repair-Experiment Decision:* `INSUFFICIENT EVIDENCE` (No failure to repair; unguided speculation avoided; problem not declared solved).


---

## 3. What is currently proven?

### A. Acquisition & Coverage
1. **P-M5 Funnel Dimensions:**
   - 576 expected company-years (36 companies × FY2010–2025)
   - 512 discovered (88.89%)
   - 194 downloaded (33.68% of expected; 37.89% of discovered)
   - 170 identity-verified (29.51%)
   - 182 MDA-located (31.60%; non-monotonic with identity verification)
   - 127 accepted (22.05% headline coverage)
   - **Primary Loss:** 318 company-years lost at DISCOVERED → DOWNLOADED transition.
2. **Three Distinct Zero-Coverage Populations (P-C0):**
   - `downloaded = 0`: 8 fiscal years (2010, 2014, 2016, 2019, 2020, 2021, 2022, 2023)
   - `mda_located = 0`: 9 fiscal years (`downloaded=0` + FY2015)
   - `accepted = 0`: 10 fiscal years (`mda_located=0` + FY2011)
   - Nested relationship: `downloaded=0` ⊂ `mda_located=0` ⊂ `accepted=0`.
3. **Pre-Fetch Filter Ruled Out (P-C0):**
   - `cohort_fetch_manifest.jsonl` (194 rows) is a post-hoc store export derived from already-successful downloads, not an input filter.
4. **Current Access Variation Observed (P-C0 / P-C0R):**
   - At ~13:17 UTC (2026-09-17), probes failed 9/9 on `nsearchives.nseindia.com` (connection resets, 45s timeouts).
   - At ~13:59 UTC, the same URLs succeeded 10/10 with valid payloads.
   - During P-C0R (14:40–15:21 UTC), probes succeeded 50/50 across repeated and paired arms.
5. **Client Asymmetry Ruled Out as Current Cause (P-C0R):**
   - 10/10 paired comparisons succeeded identically with Arm A (session cookies + headers) and Arm B (unseeded fetch client).
6. **Payload Validity Established (P-C0 / P-C0R):**
   - All successful downloads returned valid ZIP or PDF payloads verified by magic bytes and `qpdf`.
7. **R1 Telemetry Implementation Verified & Committed:**
   - Commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` on branch `r1-fetch-telemetry`.
   - Emits structured `r1-v1` attempt-level records on disk.
   - Non-blocking error absorption ensures telemetry write failures cannot interrupt acquisition.
   - Zero behavioral change: 15/15 PRE-vs-POST equivalence fixtures matched.
   - Core regex patterns (`arpipe/patterns.py`) have 0 diff.

### B. Extraction, Quality & Boundaries
1. **Document-Level Score Concealment (P-M1):** 84/194 documents conceal bad pages (`orphan_start_frac > 0.03`) beneath document-level passing scores.
2. **True Page-Grain Native vs. OCR (P-M2.1):** 2,412 native pages (25.2% > 0.03) vs. 134 OCR pages (41.8% > 0.03) across 21 OCR-bearing documents.
3. **Threshold Stability (P-M2.2):** `ORPHAN_START_FRAC_MAX = 0.03` preserved; `0.040` remains strictly exploratory.
4. **Physical Quality Boundaries (P-M3):** Physical scan quality across 37,917 pages evaluated; strictly decoupled from OCR quality and extraction correctness.
5. **Annexure Form Distribution (P-M4):** 12 standalone heading, 3 annexure-labelled, 1 combined, 2 other out of 18 eligible fit documents ($n=3$ annexure docs is insufficient for generalization).
6. **Legacy Fonts vs. Corruption (P-B3):** Legacy-font presence (5.47% pages, 9 documents) distinguished from native text corruption (3.33% pages).
7. **Script Telemetry (P-B4):** Script and language fractions added with zero behavioral drift across 194 documents.
8. **Operational Fencing (P-B7):** SQLite WAL queue with atomic claim lease fencing and poison cutoff after 4 failed attempts.
9. **P-R1X Temporal Validity & Current Viability (P-R1X):**
   - Windows 1 and 2 started precisely on schedule (+1.4ms and +2.1ms delay), executing sequentially with 1 worker under `HostLimiter` (1.5s).
   - Primary temporal analysis ($N=20$, 10 targets, 10 controls): 20/20 acquisitions succeeded on Attempt 1 (`SUCCESS_STORED_DOC`, HTTP 200, 0 retries, 0 safety stops).
   - Target vs. Control Difference: Exactly 0.0% difference under test conditions.
   - Bitwise Reproducibility: 10/10 observations produced bitwise-identical SHA-256 CAS blob hashes across Windows 1, 2, and 3.
   - Window 3 was delayed by 9h 12m 46s due to host sleep / process suspension during inter-window wait loop; adjudicated as `POST_INTERRUPTION_SUPPLEMENTAL` (10/10 success). Excluded from primary temporal comparison.
   - Historical failure mode (`downloaded=False`) was NOT OBSERVED and NOT REPRODUCED on this pilot sample under tested conditions.
   - Repair-Experiment Decision: `INSUFFICIENT EVIDENCE`.

---

## 4. What remains unknown?
1. **Historical Cause of 2026-09-11 Losses:**
   - The root cause of the 318 historical discovered $\rightarrow$ downloaded losses on 2026-09-11 remains strictly **UNKNOWN / NOT ESTABLISHED**. Surviving historical records contain 0.0% reason codes.
2. **Failure Reproducibility:**
   - Whether the historical failure mode can be reproduced at all under any controlled contemporary conditions.
3. **Time-Dependent Acquisition Behavior Outside Tested Windows:**
   - Whether periodic maintenance, time-of-day policies, or market-hours access rules exist that were not captured by the two valid windows.
4. **Concurrency & Scale Effects:**
   - How origin behaves under multi-worker high concurrency or full-universe (576 company-years) crawling compared to the polite single-worker pilot.
5. **Historical Failure Layer Classification:**
   - Whether surviving unindexed logs or external artifacts can classify whether failures occurred at L1 (Connect), L3 (HTTP status), or L4 (Receipt).

---

## 5. What is the current blocker?
1. **Universe V2 Cannot Be Frozen:**
   - Universe V2 and downstream gold-standard validation (F1 → F2 → F3) are blocked until the 318-observation acquisition loss is diagnosed and resolved.
2. **P-B2 Phase 2R / P-C2 Clean Rerun Blocked:**
   - P-B2 Phase 1 baseline was partially lost due to shared-worktree corruption. A clean rerun requires a stable acquisition state and frozen Universe V2.

---

## 6. What is the exact next task?
**HISTORICAL ACQUISITION-CAUSE EVIDENCE AUDIT**

- **Task Identifier:** `HISTORICAL-AUDIT`
- **Objective:** Search surviving historical artifacts across the thesis repository and logs for evidence that can classify the 2026-09-11 discovered $\rightarrow$ downloaded losses.
- **Search Scope:**
  - Historical logs and terminal outputs
  - Discovery manifests and store logs
  - Prior telemetry and fetch records
  - Preserved HTTP status records and error messages
  - Preserved command outputs, cached artifacts, and run summaries
  - Historical experiment worktree logs
- **Priority:** **Historical evidence FIRST.**
  - Do NOT jump directly to an acquisition repair.
  - Do NOT infer the historical cause from current pilot success.
  - If sufficient evidence exists: design the next experiment from the identified evidence.
  - If insufficient evidence exists: record the information gap explicitly in project memory.
- **Rules:** Read-only historical investigation. No live network requests. No production code changes.

---

## 7. Which worktree should be used?
**Dedicated adjudication worktree:**
`D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-adjudication` (branch `pr1x-adjudication`, commit `ca92b8e`)

> [!CRITICAL]
> The worktrees `arpipe-r1-fetch-telemetry`, `arpipe-r1-telemetry-analysis`, and `arpipe-pr1x-execution` are **PERMANENTLY FROZEN / READ-ONLY**.
> The historical evidence audit operates in read-only mode across surviving repository artifacts.

---

## 8. Which base SHA should be used?
**`56497721cb68c4831e6f225074b6bd7ea17bffb0`** (Frozen R1 Implementation)  
Current Adjudication HEAD: **`ca92b8e8d043cccb9556a6fc591927b3bbf1cf32`** (branch `pr1x-adjudication`).

Verified lineage:
`0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` → `56497721cb68c4831e6f225074b6bd7ea17bffb0` (R1 implementation)
*(Note: Commit `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870` contains analysis reports and protocol design only; it is not the engineering base).*


---

## 9. Which files/worktrees must not be touched?
1. **`D:\sem_iitk\sem9\thesis\sep_week1\arpipe-0.1.0`** (Permanent read-only forensic evidence; MUST NOT BE TOUCHED).
2. **`D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-fetch-telemetry`** (**FROZEN / READ-ONLY**; permanent milestone record; MUST NOT BE TOUCHED).
3. **All Completed Experiment Worktrees (Read-Only):**
   - `arpipe-pb2-p1-recovery`
   - `arpipe-pc0-coverage-diag`
   - `arpipe-pc0-diagnostic-base`
   - `arpipe-pc0r-acquisition-pilot`
   - `arpipe-pm2-native-vs-ocr`
   - `arpipe-pm2.1-pagegrain`
   - `arpipe-pm2.2-sensitivity`
   - `arpipe-pm3-scan-quality`
   - `arpipe-pm4-annexure-audit`
   - `arpipe-pm5-coverage`
   - `arpipe-step0-forensics`
   - `arpipe-step0a-candidate`
   - `arpipe-step0a-recovery`
   - `arpipe-step0b-recovery`
4. **All production code and experiment artifacts outside `ARPipe_Memory`.**
5. **`arpipe/patterns.py`** (Protected core module; must have 0 diff).
6. **Production `main` branch.**

---

## 10. Which experiments must not be repeated?
Completed experiments must NOT be rerun merely to regenerate figures or metrics already supported by frozen evidence:
- **DO NOT RERUN:**
  - `R1` (Telemetry implementation and equivalence matrix are frozen in commit `5649772`)
  - `P-M5` (Coverage funnel counts are frozen in `reports/coverage.json` and `pm5_stage_table.csv`)
  - `P-C0` (Coverage diagnosis findings are frozen in `reports/coverage_diagnosis.json`)
  - `P-C0R` (Pilot results are frozen in `reports/pc0r_diagnosis.json` and raw telemetry logs)
  - `P-B1`, `P-B3`, `P-B4`, `P-B5`, `P-B7`, `P-M1`, `P-M2.1`, `P-M2.2`, `P-M3`, `P-M4`
  - `Step 0`, `Step 0A`, `Step 0B`, `Diagnostic Base Sufficiency Check`

A rerun is permitted only if a future protocol explicitly requires an updated controlled trial, in which case the justification and methodology must be pre-registered in memory first.
### Forbidden Actions:
- Modifying R1 worktree
- Modifying main/production
- Blind retry/backoff changes
- Corpus rerun
- Changing Universe V2 before acquisition diagnosis
- Repeating frozen experiments without a new protocol

