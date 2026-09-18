# ARPipe — Evidence Register

This register catalogues every critical empirical claim, methodological hypothesis, architectural finding, and primary artifact across the ARPipe thesis. Every entry is classified according to our strict evidential taxonomy.

---

## Evidential Taxonomy

- **`HISTORICALLY ESTABLISHED`**: Directly attested by committed source code, immutable historical logs, or frozen and hash-verified evidence artifacts.
- **`CURRENTLY REPRODUCED`**: Directly verified through live controlled experiments under documented and repeatable test configurations.
- **`OBSERVED`**: Empirically witnessed in real-time execution, but subject to environmental or temporal non-stationarity.
- **`INFERRED`**: Logically derived from primary evidence, but lacking direct, unmediated physical logging.
- **`PLAUSIBLE BUT UNPROVEN`**: Theoretically consistent with available data and domain principles, but competing against alternative viable hypotheses.
- **`UNKNOWN`**: Unverifiable due to missing, unpersisted, or destroyed records.
- **`BLOCKED`**: Progress cannot proceed because a mandatory prerequisite has failed or halted under safety rules.
- **`RULED OUT`**: Formally disproven through direct empirical counter-evidence or rigorous counter-factual test matrices.

---

## 1. Claims and Findings Register

| ID | Claim / Finding | Evidence Status | Evidence Source & Key Artifacts | Notes & Epistemological Boundaries |
|:---|:---|:---|:---|:---|
| **EV-01** | Historical acquisition loss of 318 company-years at DISCOVERED → DOWNLOADED transition | **HISTORICALLY ESTABLISHED** | `reports/coverage.json` (SHA: `c8416674...`), `reports/pm5_stage_table.csv` | 512 discovered → 194 downloaded. Headline coverage: 127/576 (22.05%). Single largest loss. |
| **EV-02** | All 194 historical successful downloads occurred inside a single ~4.5-min window on 2026-09-11 | **HISTORICALLY ESTABLISHED** | `live_store_documents.jsonl` (SHA: `3a7c7bf1...`), `coverage_diagnosis.md` | Timestamps span 10:28:44–10:33:08 UTC across three FY bursts (`{2012,2013}`, `{2017,2018}`, `{2024,2025}`). |
| **EV-03** | Reason-code coverage for historical DISCOVERY and DOWNLOAD failures was 0.0% | **HISTORICALLY ESTABLISHED** | `reports/pm5_reason_code_completeness.csv` (SHA: `0adb7410...`), `arpipe/fetch.py` | Pre-R1 code printed to stderr or silently returned `None`; 0/318 reasons were stored on disk. |
| **EV-04** | Pre-fetch filter hypothesis: `cohort_fetch_manifest.jsonl` filtered 194 rows prior to fetch | **RULED OUT** | `cohort_fetch_manifest.jsonl`, `tools/seed_historical_labels.py`, commit `1d7dc05` | Proven to be a post-hoc export of already-successful downloads for an evaluation task, not an input filter. |
| **EV-05** | Three zero populations (`downloaded=0`, `mda_located=0`, `accepted=0`) are distinct | **HISTORICALLY ESTABLISHED** | `pm5_stage_table.csv`, `reports/coverage_diagnosis.md` | `downloaded=0` (8 FYs) ⊂ `mda_located=0` (9 FYs) ⊂ `accepted=0` (10 FYs). |
| **EV-06** | `nsearchives.nseindia.com` exhibits time-varying accessibility on sub-hour timescales | **CURRENTLY REPRODUCED** | Diagnostic Base Check (0/9 @ 13:17 UTC), P-C0 (10/10 @ 13:59 UTC), P-C0R (50/50 @ 14:40–15:21 UTC) | Observed over 2026-09-17 from IIT Kanpur campus network. Current behavior varies substantially by time window. |
| **EV-07** | Client configuration asymmetry (missing cookies/Referer) causes fetch failure | **RULED OUT** (as current cause) | P-C0R Part 6 Controlled A/B Trial (`reports/pc0r_client_comparison.csv`) | 10/10 pairs succeeded equally with Arm A (cookies+headers) and Arm B (unseeded fetch client). |
| **EV-08** | File format corruption or invalid payloads caused the 318 losses | **RULED OUT** (for tested sample) | P-C0 Step 4, P-C0R Part 5/6, `qpdf` checks | All tested URLs returned intact ZIP or PDF payloads with valid magic numbers. |
| **EV-09** | Historical 2026-09-11 failure mechanism of the 318 losses | **UNKNOWN** | Absence of per-attempt historical logs, `pc0r_diagnosis.md` | Historical invocation is UNKNOWN. Time-varying CDN access is plausible, but unprovable without 2026-09-11 logs. |
| **EV-10** | R1 telemetry repair preserves 100% behavioral invariance | **HISTORICALLY ESTABLISHED / PREVIOUSLY EXECUTED** | Commit `5649772`, `arpipe/tests/test_r1_fetch_telemetry.py`, `reports/r1_fetch_telemetry.md` | 15/15 PRE-vs-POST equivalence tests passed. Executed in external venv (`pm2.1`); local venv verified equivalent. |
| **EV-11** | R1 telemetry writing is non-blocking and swallows writer exceptions | **HISTORICALLY ESTABLISHED / PREVIOUSLY EXECUTED** | Commit `5649772`, `test_r1_fetch_telemetry.py` (Parametrized writer tests) | Swallows `PermissionError`, `OSError(28)` (disk full), and `RuntimeError` without modifying acquisition. |
| **EV-10** | R1 telemetry repair preserves 100% behavioral invariance | **CURRENTLY REPRODUCED** | Commit `5649772`, `arpipe/tests/test_r1_fetch_telemetry.py`, `reports/r1_fetch_telemetry.md` | 15/15 PRE-vs-POST equivalence tests passed. CURRENTLY REPRODUCED in dedicated local R1 `.venv`. Previous runs remain PREVIOUSLY EXECUTED. |
| **EV-11** | R1 telemetry writing is non-blocking and swallows writer exceptions | **CURRENTLY REPRODUCED** | Commit `5649772`, `test_r1_fetch_telemetry.py` (Parametrized writer tests) | Swallows `PermissionError`, `OSError(28)` (disk full), and `RuntimeError` without modifying acquisition. CURRENTLY REPRODUCED in dedicated R1 `.venv`. |
| **EV-12** | Core regex patterns module `arpipe/patterns.py` is clean | **HISTORICALLY ESTABLISHED** | Git diff against HEAD `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | 0 diff. Case B was reverted during Step 0; R1 maintained bitwise clean 0 diff. |
| **EV-13** | P33 benchmark: `is given below` pointer language correctly handled | **HISTORICALLY ESTABLISHED / PREVIOUSLY EXECUTED** | `test_p33_is_given_below_not_pointer` in `arpipe/tests/test_pipeline.py` | Verified passed in R1 regression run (1 passed in 0.31s in `pm2.1` venv). |
| **EV-13** | P33 benchmark: `is given below` pointer language correctly handled | **CURRENTLY REPRODUCED** | `test_p33_is_given_below_not_pointer` in `arpipe/tests/test_pipeline.py` | Verified passed in R1B regression run (1 passed, 84 deselected in local R1 `.venv`). Previous runs remain PREVIOUSLY EXECUTED. |
| **EV-14** | Document-level order quality score conceals bad physical pages | **HISTORICALLY ESTABLISHED** | `reports/pm1_per_page_orphan.md` | 84/194 documents have $\ge 1$ page with `orphan_start_frac > 0.03` while document score is $\le 0.03$. |
| **EV-15** | OCR pages exhibit higher `orphan_start_frac` than native pages at true page grain | **HISTORICALLY ESTABLISHED** | `reports/pm2_pagegrain_native_vs_ocr.md` | Native > 0.03: 25.17% (607/2,412 pages); OCR > 0.03: 41.79% (56/134 pages). |
| **EV-16** | Re-calibrated production threshold `.040` for `orphan_start_frac` | **PLAUSIBLE BUT UNPROVEN** | `reports/pm2_2_threshold_study.md` | Production threshold remains strictly `0.03`. `.040` is an unverified exploratory candidate. |
| **EV-17** | Decoupling of physical scan quality from OCR and extraction correctness | **HISTORICALLY ESTABLISHED** | `reports/pm3_scan_quality.md` | Methodological principle: Scan/Input Quality $\ne$ OCR Quality $\ne$ Extraction Correctness. |
| **EV-18** | Heading-form systematically drives extraction accuracy across cap bands | **UNKNOWN** | `reports/annexure_audit.md` | Only 3 annexure-labelled documents exist in eligible fit set ($n=18$). Sample is too small for generalizable claims. |
| **EV-19** | Legacy Indian font evidence presence vs. native text corruption | **HISTORICALLY ESTABLISHED** | `reports/legacy_font_corpus_measurement.md` | 2,075 pages (5.47%) show legacy fonts; 1,263 pages (3.33%) show native corruption. 2x2 matrix reconciled. |
| **EV-20** | Additive script telemetry causes zero behavioral change across corpus | **HISTORICALLY ESTABLISHED** | `reports/pb4_corpus_validation.json` | 194 documents / 37,917 pages evaluated; exactly 0 diffs in located status, bounds, or grades. |
| **EV-21** | Operational SQLite state layer with claim leasing and poison cutoff | **HISTORICALLY ESTABLISHED** | `arpipe/STATE.md`, `arpipe/state.py` | Implemented WAL SQLite queue with atomic `UPDATE ... RETURNING`, heartbeat leasing, and attempt 5 poison cutoff. |
| **EV-22** | Clean reconstructed production baseline exists for `arpipe-0.1.0` | **RULED OUT / UNRECOVERABLE** | `arpipe-step0a-recovery`, `arpipe-step0b-recovery`, Git object scans | Byte-exact baseline versions of `cli.py`, `pipeline.py`, `verify.py` do not exist as Git objects. Tree is dirty. |
| **EV-23** | Universe V2 is frozen and ready for gold-standard validation | **BLOCKED** | Project decisions and acquisition status | Cannot freeze Universe V2 until the 318-observation acquisition loss is diagnosed and resolved. |
| **EV-24** | R1 Git commit freezing failure telemetry with zero behavioral drift | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` | Base SHA `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14`. 9 files committed. Lineage confirmed. Main branch untouched. |
| **EV-25** | R1 telemetry-analysis report and P-R1X protocol freeze commit | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Commit `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870` | Branch `r1-telemetry-analysis`. Base `5649772`. Contains analysis report and protocol design. Analysis reference only. |
| **EV-26** | P-R1X engineering base implementation | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` | Frozen R1 implementation. Required engineering base for any future P-R1X worktree. Lineage: `0fb8cbf` → `5649772`. |
| **EV-27** | P-R1X frozen candidate population source manifest | **HISTORICALLY ESTABLISHED** | `reports/pc0_sample_manifest.json` (SHA-256: `394c628d842bdcf967b6dd82ab695fb4b17a88602c7c79c0b17561a3d931bb0e`) | 10-observation pilot sample (5 zero FY targets + 5 controls) derived from `pm5_stage_table.csv` (SHA-256: `30e93b59...`). 100% census. |
| **EV-28** | P-R1X execution commit and run provenance | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Commit `0b1d595407eacb13b115811cdb610b3e1f56a767` in `arpipe-pr1x-execution`, run ID `5e675cbec11647819858e673b9a95ab6` | 30 live requests executed across 3 windows using frozen R1 client and HostLimiter (1.5s). All attempts HTTP 200, 0 retries. |
| **EV-29** | P-R1X valid two-window primary temporal baseline | **CURRENTLY REPRODUCED** | `reports/pr1x_observation_results.json`, `reports/pr1x_temporal_validity.json` | Windows 1 and 2 started within 2.1ms of schedule. 20/20 acquisitions succeeded on Attempt 1. Target vs Control difference: 0.0%. Bitwise-identical payloads. |
| **EV-30** | P-R1X Window 3 process interruption and delayed execution | **HISTORICALLY ESTABLISHED / OBSERVED** | `reports/pr1x_observation_results.json`, `reports/pr1x_adjudication.md` | Window 3 missed schedule by 9h 12m 46s due to host sleep / process suspension. Adjudicated as POST_INTERRUPTION_SUPPLEMENTAL (10/10 success). Excluded from primary temporal set. |
| **EV-31** | Historical 2026-09-11 failure mode not reproduced in P-R1X; historical root cause | **UNKNOWN / NOT ESTABLISHED** | `reports/pr1x_adjudication.md`, `reports/pr1x_adjudication.json` | Current endpoints are viable; unadorned client succeeds. Historical failure was NOT OBSERVED and NOT REPRODUCED. Cause of 2026-09-11 losses remains UNKNOWN. |
| **EV-32** | P-R1X forensic adjudication and artifact integrity freeze | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Commit `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32` in `arpipe-pr1x-adjudication`, `reports/pr1x_artifact_hashes.json` | 5 adjudication artifacts committed. SHA-256 hashes pinned for all 10 execution and adjudication files. Repair experiment decision: INSUFFICIENT EVIDENCE. |

---


## 2. Verified R1 Milestone Artifact Register

All hashes below are verified direct SHA-256 digests computed over immutable files committed in Git commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` on branch `r1-fetch-telemetry`.

| Path | SHA-256 Digest | Task | Evidence Type | Evidence Status | Git Tracked / Committed Status | Interpretation | Limitation |
|:---|:---|:---:|:---|:---:|:---:|:---|:---|
| `sep_week1/arpipe-r1-fetch-telemetry/reports/r1_fetch_telemetry.md` | `edf26f03a433e1e344c956195c1cab605b519dc3aec62a4e142a0dbbf48a895c` | R1 | Milestone Report | **HISTORICALLY ESTABLISHED** | Committed (`5649772`) | Primary qualitative report detailing R1 scope, architecture, test matrix, and epistemological boundaries. | Cites tests executed in external venv (`pm2.1`); does not resolve historical 318 losses. |
| `sep_week1/arpipe-r1-fetch-telemetry/reports/r1_fetch_telemetry.json` | `10310bd9cce4f55b198a7e6f5777e7c86d3ecce029f068003e750623fc6d26ab` | R1 | Machine-Readable Report | **HISTORICALLY ESTABLISHED** | Committed (`5649772`) | Structured JSON summary of schema `r1-v1`, behavioral immutability guarantees, and test matrix results. | Confined to mock/synthetic test matrix fixtures. |
| `sep_week1/arpipe-r1-fetch-telemetry/reports/r1_telemetry/r1_matrix_telemetry.jsonl` | `466dca2953cea16b698fe81dec2ef852634c4b6e5a476acb831033b941a90631` | R1 | Diagnostic Output Fixture | **CURRENTLY REPRODUCED** | Committed (`5649772`) | 17 structured JSONL per-attempt failure records generated across 9 test cases proving attempt-level emission. | Generated via synthetic mock runner, not live network traffic. |
| `sep_week1/arpipe-r1-fetch-telemetry/reports/r1_telemetry/r1_generation_summary.json` | `92e2dc8e4a82eec021dd1c91684b9b04ab51a42367cf5a6099a8e200135dce05` | R1 | Diagnostic Metadata | **CURRENTLY REPRODUCED** | Committed (`5649772`) | Verification summary confirming 21 requests, 17 records persisted, and 0 records on success. | Verifies synthetic generator execution only. |
| `sep_week1/arpipe-r1-fetch-telemetry/arpipe/telemetry.py` | `667dc9c6f2e282d6c2ded859aeb7b4c7b61b49142d041f744c25cf3ae2ba9ca4` | R1 | Production Source Code | **HISTORICALLY ESTABLISHED** | Committed (`5649772`) | Schema `r1-v1` definitions, URL redaction, non-blocking file writer, and L0–L6 error classification. | Resides on branch `r1-fetch-telemetry`; not merged to `main`. |
| `sep_week1/arpipe-r1-fetch-telemetry/arpipe/fetch.py` | `2b20a66878e23c3ded5e86f8bd3dc756022f356b01b238a1b4d96ffef084db3f` | R1 | Production Source Code | **HISTORICALLY ESTABLISHED** | Committed (`5649772`) | Instrumented fetch module emitting non-blocking telemetry on failures while strictly preserving control flow. | Preserves existing 3 retries and silent `return None`; zero algorithmic repair. |
| `sep_week1/arpipe-r1-fetch-telemetry/arpipe/cli.py` | `df5e4bf43ef3266fd8b3f8b33ddc2eb93f4fe46d068d390c5f0d9a9a528c5149` | R1 | Production Source Code | **HISTORICALLY ESTABLISHED** | Committed (`5649772`) | Exposes `--telemetry-path` on fetch subcommand and plumbs sink to `_fetch_pair`. | CLI plumbing only; does not affect default pipeline behavior when flag is omitted. |
| `sep_week1/arpipe-r1-fetch-telemetry/arpipe/tests/test_r1_fetch_telemetry.py` | `ef9a609cec3d2b4751d9c7482dee070c5a50cf1fc0e4cf4ef00f891c880fce47` | R1 | Test Suite | **HISTORICALLY ESTABLISHED** | Committed (`5649772`) | Deterministic 15-case equivalence test suite and non-blocking writer failure absorbers. | Test outcomes classified as PREVIOUSLY EXECUTED in external venv. |
| `sep_week1/arpipe-r1-fetch-telemetry/tools/generate_r1_telemetry.py` | `e09191818755c8eba4f8a169a3b335d99ebf10f8c18d3468d68de341cde40e67` | R1 | Diagnostic Runner | **HISTORICALLY ESTABLISHED** | Committed (`5649772`) | Standalone test runner that exercises mock matrix cases and generates authoritative verification fixtures. | Mock test harness; does not execute live network requests. |

---

## 3. R1 Committed Artifacts & Test Evidence Summary

### Committed Artifact Status
All four authoritative R1 artifacts are committed in commit `56497721cb68c4831e6f225074b6bd7ea17bffb0`:
1. `reports/r1_fetch_telemetry.md` (SHA-256: `EDF26F03A433E1E344C956195C1CAB605b519DC3AEC62A4E142A0DBBF48A895C`)
2. `reports/r1_fetch_telemetry.json` (SHA-256: `10310BD9CCE4F55B198A7E6F5777E7C86D3ECCE029F068003E750623FC6D26AB`)
3. `reports/r1_telemetry/r1_matrix_telemetry.jsonl` (SHA-256: `466DCA2953CEA16B698FE81DEC2EF852634C4B6E5A476ACB831033B941A90631`)
4. `reports/r1_telemetry/r1_generation_summary.json` (SHA-256: `92e2dc8e4a82eec021dd1c91684b9b04ab51a42367cf5a6099a8e200135dce05`)

`walkthrough.md`: **MISSING / intentionally not recreated** (per R1B protocol).

### R1 Test Evidence Classification
Test evidence is strictly separated into local reproduction vs. historical external runs:
- **CURRENT LOCAL TESTS (`CURRENTLY REPRODUCED`):**
  - Executed in `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-fetch-telemetry\.venv` during R1B:
    - P33 benchmark (`test_p33_is_given_below_not_pointer`): **1 passed, 84 deselected** (`CURRENTLY REPRODUCED`)
    - R1 telemetry tests (`test_r1_fetch_telemetry.py`): **15 passed, 0 failed** (`CURRENTLY REPRODUCED`)
    - Existing regression (`test_discover.py`, `test_config.py`): **16 passed, 0 failed** (`CURRENTLY REPRODUCED`)
    - Total: **32 passed, 0 failed, 0 skipped** (`CURRENTLY REPRODUCED`)
- **PREVIOUS EXTERNAL TESTS (`PREVIOUSLY EXECUTED`):**
  - Executed during R1 development in `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pm2.1-pagegrain\.venv` (Python 3.14.3, pytest 9.1.1).
  - Categorized strictly as `PREVIOUSLY EXECUTED`. The two categories are not collapsed.

### Environment Equivalence Wording
Relevant Python/package versions matched between the previous external environment (`arpipe-pm2.1-pagegrain\.venv`) and the dedicated R1 environment (`arpipe-r1-fetch-telemetry\.venv`): Python 3.14.3, pytest 9.1.1, httpx 0.28.1, pydantic 2.13.5, pymupdf 1.28.2. This supports environment equivalence for the bounded R1 tests. Full virtual environments are **NOT** claimed to be bitwise identical because that was not established.

---

## 4. R1 Telemetry Analysis & P-R1X Evidence Register

### R1 Telemetry-Analysis Artifacts (Commit `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870`)
- **Git Commit:** `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870`
- **Branch:** `r1-telemetry-analysis` in `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-telemetry-analysis`
- **Evidence Type:** Git commit & committed analytical reports
- **Status:** **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED**
- **Committed Files:**
  1. `reports/r1_telemetry_analysis.md` (Formal Markdown analysis report)
  2. `reports/r1_telemetry_analysis.json` (Structured machine-readable evidence dataset)
- **Role:** Analysis reference and protocol specification only. It is **NOT** the engineering base for P-R1X.

### P-R1X Engineering Base
- **Git Commit:** `56497721cb68c4831e6f225074b6bd7ea17bffb0`
- **Branch:** `r1-fetch-telemetry` in `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-fetch-telemetry` (FROZEN / READ-ONLY)
- **Evidence Type:** Git commit & frozen production codebase
- **Status:** **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED**
- **Role:** Mandatory engineering base for any future P-R1X worktree. Lineage: `0fb8cbf` → `5649772`.

### P-R1X Population Source
- **Artifact:** `reports/pc0_sample_manifest.json` from P-C0
- **SHA-256 Digest:** `394c628d842bdcf967b6dd82ab695fb4b17a88602c7c79c0b17561a3d931bb0e`
- **Originating Source:** `reports/pm5_stage_table.csv` (SHA-256: `30e93b59ac689f00fab182583fb25883322e429be42b4ba14e13a1011b916dc9`)
- **Evidence Type:** Frozen sample manifest
- **Status:** **HISTORICALLY ESTABLISHED**
- **Population:** $N = 10$ distinct observations (5 target zero-download FY observations + 5 controls).
- **Sampling Rule:** 100% census of the frozen pilot sample. No substitution, no adaptive selection.

---

## 5. P-R1X Execution & Adjudication Artifact Register

All hashes below are verified direct SHA-256 digests computed over immutable files committed in Git commit `0b1d595407eacb13b115811cdb610b3e1f56a767` (`pr1x-execution`) and `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32` (`pr1x-adjudication`).

| Path | SHA-256 Digest | Bytes | Commit | Status | Interpretation |
|:---|:---|:---:|:---:|:---:|:---|
| `reports/pc0_sample_manifest.json` | `394c628d842bdcf967b6dd82ab695fb4b17a88602c7c79c0b17561a3d931bb0e` | 11,752 | `efbc93e` | **HISTORICALLY ESTABLISHED** | Frozen 10-observation census manifest (5 zero FY targets + 5 controls). |
| `reports/pr1x_execution_runbook.md` | `4d6f9b320dcb612b4ab9eb3eb0ffd9530589c692a8b19d29c826e18506e39de9` | 7,768 | `efbc93e` | **HISTORICALLY ESTABLISHED** | Predeclared schedule, 90m spacing rule, single-worker rule, and Section 10 Interruption Rule. |
| `reports/pr1x_environment.json` | `cc8f9ed239e27b2dbda896545cd691e6eeb12bab6477ecedd726719f419a79bd` | 1,047 | `efbc93e` | **HISTORICALLY ESTABLISHED** | Runtime environment metadata (Python 3.14.3, httpx 0.28.1, Win32 clock info). |
| `reports/pr1x_live_telemetry.jsonl` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` | 1 | `0b1d595` | **HISTORICALLY ESTABLISHED** | Live telemetry sink. Contains 0 failure records because 0 attempts failed. |
| `reports/pr1x_observation_results.json` | `6fc3c5af586e4d2c185e01184e76065a1f72dc16a52a2e1c9e498988dab2e987` | 35,376 | `0b1d595` | **HISTORICALLY ESTABLISHED** | Complete execution ledger containing per-window and per-observation timestamps, outcomes, and CAS hashes. |
| `reports/pr1x_execution_summary.md` | `6dbcf74005f9e1c9bceaf30fbf8641b67f91a7d6490c49c8071396e056bca298` | 8,744 | `0b1d595` | **HISTORICALLY ESTABLISHED** | Initial prose report. Overclaims corrected by adjudication report. |
| `reports/pr1x_temporal_validity.json` | `c39cf4e54ccdbba8c6f5bb3a4acc806710eaf5bd59d19d1ea2160c488b3281bd` | 3,681 | `ca92b8e` | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Machine-readable temporal validity adjudication (W1 VALID, W2 VALID, W3 POST_INTERRUPTION_SUPPLEMENTAL). |
| `reports/pr1x_adjudication.json` | `7ae6b930b24ab7011d070afc3c1ff6e49b6153a0751b9f84aca7dabb41067001` | 10,098 | `ca92b8e` | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Comprehensive structured adjudication findings and evidence classification. |
| `reports/pr1x_adjudication.md` | `1bc89188f047ec8a63d452e813fa056651a240179a42bf6c7152ce121f273f81` | 15,034 | `ca92b8e` | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Full forensic report with 18 mandatory sections. P-R1X classified as incomplete 3-window experiment. |
| `reports/pr1x_memory_update_notes.md` | `0697d2910469e46e236d82f7f739ca26ffac8c9332ba62cd1fdd56d5e579151a` | 3,793 | `ca92b8e` | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Memory reconciliation plan for Phase B closeout. |
| `reports/pr1x_artifact_hashes.json` | `37803f2c5e5baecfe54b1f4db5ea5d7ba372e9895ba42ea2d6ecbc0745582c68` | 2,341 | `ca92b8e` | **HISTORICALLY ESTABLISHED / CURRENTLY VERIFIED** | Pinned cryptographic digest manifest of all execution and adjudication files. |
