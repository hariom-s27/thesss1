# R1 Telemetry Analysis & Acquisition-Resolution Experiment Design

## Status
COMPLETE / FROZEN ANALYSIS

## Date
2026-09-17

## Analysis Commit
`3beee249db36f9fdd1a8a2e01d6fdc3c6024d870` on branch `r1-telemetry-analysis`  
Worktree: `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-telemetry-analysis`

## Engineering Base Used by Proposed P-R1X
`56497721cb68c4831e6f225074b6bd7ea17bffb0` on branch `r1-fetch-telemetry`  
Worktree: `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-fetch-telemetry` (FROZEN / READ-ONLY)

## Final Verdict
# TELEMETRY ANALYSIS COMPLETE — NEXT EXPERIMENT SPECIFIED

---

## 1. Objective
Analyze the frozen R1 attempt-level failure telemetry (`r1-v1`) and determine the smallest evidence-supported acquisition-resolution experiment to distinguish remaining acquisition failure hypotheses without changing production acquisition behavior in advance.

---

## 2. Evidence Sources

| Artifact | Source Path / Commit | SHA-256 Digest | Status | Role in Analysis |
|---|---|---|---|---|
| `r1_matrix_telemetry.jsonl` | `reports/r1_telemetry/` | `466dca2953cea16b698fe81dec2ef852634c4b6e5a476acb831033b941a90631` | `CONTROLLED_TEST_EVIDENCE` | Authoritative 17-record controlled matrix trace |
| `r1_generation_summary.json` | `reports/r1_telemetry/` | `92e2dc8e4a82eec021dd1c91684b9b04ab51a42367cf5a6099a8e200135dce05` | `CONTROLLED_TEST_EVIDENCE` | Verification summary of 9 matrix test cases |
| `r1_fetch_telemetry.json` | `reports/` | `10310bd9cce4f55b198a7e6f5777e7c86d3ecce029f068003e750623fc6d26ab` | `CONTROLLED_TEST_EVIDENCE` | Machine-readable R1 verification record |
| `r1_fetch_telemetry.md` | `reports/` | `edf26f03a433e1e344c956195c1cab605b519dc3aec62a4e142a0dbbf48a895c` | `CONTROLLED_TEST_EVIDENCE` | Formal R1 specification and equivalence report |
| `pm5_stage_table.csv` | `sep_week1/arpipe-pm5-coverage/reports/` | `30e93b59ac689f00fab182583fb25883322e429be42b4ba14e13a1011b916dc9` | `HISTORICALLY_ESTABLISHED` | 576-observation universe establishing 318 losses |
| `pc0_sample_manifest.json` | `sep_week1/arpipe-pc0-coverage-diag/reports/` | `394c628d842bdcf967b6dd82ab695fb4b17a88602c7c79c0b17561a3d931bb0e` | `HISTORICALLY_ESTABLISHED` | Frozen 10-observation pilot sample |
| `pc0r_diagnosis.json` | `sep_week1/arpipe-pc0r-acquisition-pilot/reports/` | `b0f745be326f53a6d71329bf8df3a2862a98444a7ec52c92e92ec40b3bfaebf7` | `CURRENTLY_REPRODUCED` | Evidence ruling out client asymmetry (50/50 success) |

---

## 3. R1 Telemetry Schema (`r1-v1`)
The R1 implementation (`arpipe/telemetry.py`, `arpipe/fetch.py`) provides structured, attempt-level failure persistence:
- **Attempt Granularity:** Emits exactly one JSONL record per failed HTTP/network attempt. Successful acquisitions emit zero records.
- **Mandatory Fields (15):** `telemetry_schema_version` (`"r1-v1"`), `run_id`, `request_sequence_id`, `timestamp_utc`, `company_id`, `fy_end`, `source`, `url_redacted`, `url_sha256`, `attempt_number`, `terminal_state`, `retry_exhausted`, `error_type`, `status_code`, `error_message`.
- **Optional Fields (5):** `exception_class`, `first_failure_layer`, `response_content_type`, `bytes_received`, `elapsed_ms`.
- **Security & Redaction:** Sensitive query parameters (`token`, `auth`, `key`, `secret`, `signature`, `pwd`, `session`, `credential`, `X-Amz-*`) are replaced with `[REDACTED]`. `url_sha256` is computed over `url_redacted`.
- **Non-Blocking Writer:** Swallows writer exceptions (`PermissionError`, disk full `OSError(28)`, serialization errors) ensuring telemetry emission cannot interrupt or alter acquisition flow.

---

## 4. Controlled Telemetry Findings
The R1 deterministic test matrix generated the following controlled verification results:
- **Total Records:** 17 structured failure records across 9 mock test cases (21 simulated HTTP requests).
- **Terminal vs. Non-Terminal:** Exactly 7 terminal failure records (5 retry-exhausted at attempt 3; 2 immediate validation aborts at attempt 1) and 10 non-terminal retry records.
- **Retry Exhaustion:** 5 retriable scenarios exhausted all 3 attempts: HTTP 403, 429, 503, `ReadTimeout`, and `ConnectError`.
- **Validation Aborts:** 2 validation fixtures (`BadZipFile` and corrupted PDF with `qpdf` repair failure) aborted on attempt 1 with `terminal_state=true`, `retry_exhausted=false`, and `status_code=200`, verifying that corrupt payloads do not trigger useless retries.
- **HTTP Status Codes:** 403, 429, 503, 200 (validation failure), and `null` (transport/timeout exceptions).
- **Error Types & Failure Layers:**
  - `HTTP_FAILURE` (9 records) $\rightarrow$ Layer `L3_HTTP`
  - `TIMEOUT` (3 records) $\rightarrow$ Layer `L4_RECEIPT`
  - `NETWORK_FAILURE` (3 records) $\rightarrow$ Layer `L1_CONNECT`
  - `VALIDATION_FAILURE` (2 records) $\rightarrow$ Layer `L6_VALIDATION`
- **Writer Absorption:** Injected `PermissionError`, disk-full `OSError(28)`, and `RuntimeError` were swallowed without altering return values or control flow.

---

## 5. Critical Statistical Restriction

> [!CAUTION]
> The R1 deterministic telemetry matrix is a controlled test fixture. It is **NOT** a random sample of historical acquisition failures.
> 
> Therefore, do **NOT** compute or report from that matrix:
> - historical failure rate
> - dominant historical failure probability
> - expected historical distribution
> - historical prevalence
> - population-level failure estimates
> 
> The matrix must only be used to characterize telemetry software behavior across code paths.

---

## 6. Historical Evidence Limitations
- **Surviving Evidence Boundary:** The historical cause of the 2026-09-11 acquisition losses cannot be established from the surviving evidence.
- **Reason-Code Absence:** All 318 losses at the DISCOVERED $\rightarrow$ DOWNLOADED transition were recorded with 0.0% reason codes (`REASON_CODE_MISSING`).
- **Pre-R1 Silent Fall-Through:** Pre-R1 code logged network exceptions only to stderr and silently returned `None` upon exhausted 403/429/503 retries, preserving zero structured records on disk.
- **Historical Invocations:** Because no attempt-level dispatch logs exist from 2026-09-11, whether requests were actually dispatched across the wire for all 318 pairs or aborted early during the 4.5-minute burst remains unproven.

---

## 7. Reconciliation with P-C0 / P-C0R / P-M5
1. **What R1 Makes Measurable:** For any future attempt, R1 records attempt number, status code, error type, exception class, first failure layer, elapsed latency, and terminal state.
2. **What R1 Does NOT Make Recoverable:** Retrospective analysis cannot invent telemetry that was never recorded on 2026-09-11. Historical root cause remains unestablished from surviving evidence.
3. **Better Instrumented Questions:** Unpersisted errors (such as the connection resets at ~13:17 UTC in P-C0) will now be captured as structured JSONL records with layer classification (`L1_CONNECT`, `L3_HTTP`, etc.).
4. **Status of Hypotheses:**
   - Pre-fetch filter: RULED OUT (P-C0).
   - Client header/cookie asymmetry: RULED OUT (P-C0R proved identical 10/10 success across paired arms).
   - Payload corruption: RULED OUT for successful downloads (P-C0).
   - Temporal access variation: CURRENTLY REPRODUCED (observed across time windows).

---

## 8. Remaining Hypotheses

| ID | Hypothesis Name | Supporting Evidence | Contrary Evidence | Current Status | Distinguishing Observation | Confidence |
|:---:|---|---|---|:---:|---|:---:|
| **H1** | **Transient Transport Collapse** (`L1_CONNECT` / `L4_RECEIPT`) | Resets (`10054`) and 45s timeouts observed at ~13:17 UTC in P-C0. | Probes in P-C0R at 14:40–15:20 UTC had 0 connection drops across 50 probes. | `PLAUSIBLE BUT UNPROVEN` | Live telemetry records `first_failure_layer in ('L1_CONNECT', 'L4_RECEIPT')` with `status_code=null`. | MEDIUM |
| **H2** | **Rate / Cadence Limiting** (`L3_HTTP` 429 / 403) | Historical crawl ran 512 requests in a dense 4.5-minute burst (~1.9 req/s). | Polite pacing in P-C0R had 100% success; no 429 observed under polite pacing. | `PLAUSIBLE BUT UNPROVEN` | Live telemetry records `first_failure_layer='L3_HTTP'` with `status_code=429` or `403` under rapid request cadence. | MEDIUM |
| **H3** | **Temporal Access Variation** | Outcomes differed across observed time windows (0/9 at ~13:17 UTC vs 10/10 at ~13:59 UTC). | P-C0R 40-minute window was uniformly 100% stable; temporal boundaries are not yet mapped. | `CURRENTLY REPRODUCED` | Observed outcomes differed across observed time windows. (*Note: A specific market-hours schedule, maintenance window, or other periodic temporal mechanism is NOT established*). | HIGH |
| **H4** | **URL-Specific Stale / Missing Artifacts** | 313 of the 318 un-downloaded URLs have never been probed in any diagnostic experiment. | All 5 zero-download URLs probed in P-C0/P-C0R existed and returned valid payloads. | `PLAUSIBLE BUT UNPROVEN` | Live telemetry records persistent 404 or `VALIDATION_FAILURE` for specific URLs while controls succeed. | LOW |
| **H5** | **Historical Invocation Gap** | Timestamps show 3 discrete FY bursts totaling only 194 successful writes; no failed records written. | Pre-R1 code had silent fall-through on 403/429/503 which naturally produces zero writes. | `PLAUSIBLE BUT UNPROVEN` | Historical runtime logs or external dispatch records confirming batch script abort. | MEDIUM |

---

## 9. Information Gap
Absence of structured, layer-classified, attempt-level failure telemetry collected during live acquisition probes on historical candidate un-downloaded URLs under controlled temporal and pacing conditions, leaving transport-layer collapse (`status_code=null`) indistinguishable from HTTP-layer rejection (`status_code=429/403`) and URL invalidity.

---

## 10. Production-Change Decision
**DECISION: INSUFFICIENT EVIDENCE**
- Historical root cause cannot be established from surviving evidence.
- Live failure-layer distribution has not yet been observed under this protocol.
- Previous current-window observations succeeded (50/50 in P-C0R).
- Changing acquisition behavior (retry counts, backoff timings, session pooling, or headers) before collecting live diagnostic telemetry would be speculative.

---

## 11. Proposed Next Experiment Design: P-R1X Summary
- **Protocol File:** `protocols/P-R1X.md`
- **Status:** DESIGNED — NOT EXECUTED
- **Engineering Base:** `56497721cb68c4831e6f225074b6bd7ea17bffb0` (frozen R1 implementation)
- **Population:** $N = 10$ census of frozen P-C0 sample manifest (`reports/pc0_sample_manifest.json`, SHA-256: `394c628d842bdcf967b6dd82ab695fb4b17a88602c7c79c0b17561a3d931bb0e`).
- **Independent Variable:** 3 pre-scheduled temporal observation windows ($T_0$, $T_0 + 30$m, $T_0 + 60$m).
- **Controlled Variables:** Standard unseeded `httpx.Client`, polite pacing ($\ge 2.0$s pause), frozen retry policy (`retries=3`, timeout=120s, backoff `5 * (attempt + 1)**2`), local JSONL sink.
- **Output:** Structured attempt-level telemetry classifying any observed failure into exact layer (`L1_CONNECT`, `L3_HTTP`, `L4_RECEIPT`, `L6_VALIDATION`).

