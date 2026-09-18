# ARPipe — Architectural, Methodological, and Governance Decisions

This document records the binding architectural, methodological, and governance decisions established across the ARPipe thesis. Every decision reflects hard constraints derived from empirical evidence, forensic audits, and experiment closeouts.

---

## 1. Two-Funnel Model: Separate Acquisition from Extraction
- **Decision:** Decouple pipeline analysis into two independent funnels: the Acquisition Funnel (`Expected` → `Discovered` → `Downloaded` → `Valid Artifact` → `Identity Verified`) and the Extraction Funnel (`Valid Artifact` → `MDA Located` → `Language/OCR Clean` → `Quality Passing` → `Accepted`).
- **Date:** 2026-09-17
- **Evidence:** Historical P-M5 counts exhibited non-monotonic stage transitions (e.g. `mda_located = 182` exceeded `identity_verified = 170` by 12 observations) due to conflating retrieval with extraction.
- **Alternatives considered:** Single end-to-end monolithic pipeline metric (headline acceptance rate `127/576 = 22.05%`).
- **Why chosen:** A monolithic metric obscures where data loss occurs. 318 losses occurred at acquisition (before extraction began); evaluating extraction without isolating acquisition confounds algorithm defects with network/crawling gaps.
- **Consequences:** Extraction metrics are never computed over un-downloaded documents; denominators for thesis metrics must explicitly cite the specific funnel stage.

---

## 2. Do Not Freeze Universe V2 Before Acquisition Resolution
- **Decision:** The target research corpus (Universe V2) must not be frozen while the 318 discover→download losses remain unresolved.
- **Date:** 2026-09-17
- **Evidence:** P-M5 coverage audit (`reports/coverage.json`) proved only 194 of 576 expected company-years (33.68%) were downloaded on 2026-09-11.
- **Alternatives considered:** Freeze Universe V2 immediately using only the 194 historical downloads and proceed directly to gold-standard validation.
- **Why chosen:** Freezing on 194 documents accepts an uncharacterized 66.3% attrition rate across 8 entire fiscal years (`downloaded = 0`), compromising the empirical validity of downstream econometric analysis.
- **Consequences:** Downstream gold-standard validation (F1 → F2 → F3) and pipeline baseline rerun (P-B2 Phase 2R / P-C2) remain strictly **BLOCKED** until acquisition resolution concludes.

---

## 3. Acquisition Failure Telemetry is Now Instrumented
- **Decision:** Incorporate structured, attempt-level failure telemetry into `arpipe/fetch.py` and expose `--telemetry-path` via `arpipe/cli.py` (milestone R1), maintaining zero behavioral alteration.
- **Date:** 2026-09-17
- **Evidence:** P-C0 and P-C0R demonstrated that pre-R1 fetch failures printed unpersisted stderr lines or silently returned `None` on exhausted 403/429/503 retries, leaving zero failure records on disk (`pm5_reason_code_completeness.csv` = 0.0%).
- **Alternatives considered:** (a) Immediate algorithmic repair (increasing retries or altering headers) without logging; (b) Raising unhandled exceptions on all non-200 responses.
- **Why chosen:** Changing acquisition parameters before observing actual failure modes risks introducing regressions. Raising exceptions alters control flow and breaks caller contracts. Telemetry-only instrumentation provides observability while keeping behavior 100% invariant.
- **Consequences:** Commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` on branch `r1-fetch-telemetry` provides complete attempt-level diagnostic logging (`r1-v1`) on disk.

---

## 4. Telemetry Writing Must Remain Non-Blocking
- **Decision:** Telemetry emission must be wrapped in fail-safe exception absorbers that swallow writer failures without interrupting fetch execution.
- **Date:** 2026-09-17
- **Evidence:** Parametrized test `test_telemetry_writer_failure_cannot_affect_acquisition` verified identical acquisition outcomes under injected `PermissionError`, `OSError(28)` (disk full), and `RuntimeError`.
- **Alternatives considered:** Allow I/O errors to propagate and halt the acquisition crawl.
- **Why chosen:** Diagnostic instrumentation must never cause an acquisition run to fail due to logging subsystem issues (e.g. disk quota exhaustion or permission errors).
- **Consequences:** Telemetry writers log an internal flag upon error and silently return `False`; fetch retry loops, sleep intervals, and return values continue uninterrupted.

---

## 5. One Telemetry Record Per Actual HTTP/Network Attempt (`r1-v1`)
- **Decision:** Emit exactly one structured JSONL record for every individual HTTP/network request attempt rather than one summary record per URL.
- **Date:** 2026-09-17
- **Evidence:** P-C0R revealed rapid sub-hour accessibility shifts on `nsearchives.nseindia.com` (0/9 failures @ 13:17 UTC followed by 10/10 successes @ 13:59 UTC). High-level summaries mask retry progression and transient response transitions.
- **Alternatives considered:** Emit a single aggregated record per company-year upon terminal failure or success.
- **Why chosen:** Attempt-level granularity isolates intermediate status codes, backoff progression, transient CDN behavior, and distinguishes retry exhaustion from immediate aborts.
- **Consequences:** Schema `r1-v1` includes sequential `attempt_number`, `terminal_state`, `retry_exhausted`, redacted URL, URL SHA-256, and architectural layer classifications (L0–L6).

---

## 6. R1 Worktree is Frozen / Read-Only After Commit
- **Decision:** The dedicated worktree `arpipe-r1-fetch-telemetry` is declared permanently **FROZEN / READ-ONLY** following verification of final commit `56497721cb68c4831e6f225074b6bd7ea17bffb0`.
- **Date:** 2026-09-17
- **Evidence:** Final commit `5649772` incorporates all 9 required implementation, report, test, and fixture files. The working tree is clean with 0 diff on `arpipe/patterns.py`.
- **Alternatives considered:** Continue developing live diagnostic probes or acquisition resolution experiments directly inside `arpipe-r1-fetch-telemetry`.
- **Why chosen:** Preserves an immutable, verifiable milestone record of the telemetry implementation and prevents cross-task state contamination.
- **Consequences:** No further code edits, test runs, or commits may occur in `arpipe-r1-fetch-telemetry`. It serves as a permanent reference artifact.

---

## 7. Future Acquisition Work Must Use a Separate Dedicated Worktree
- **Decision:** All future engineering tasks (including live probe diagnosis and acquisition resolution) must execute in a NEW dedicated Git worktree branched from verified commit `56497721cb68c4831e6f225074b6bd7ea17bffb0`.
- **Date:** 2026-09-17
- **Evidence:** Forensic incident Step 0 demonstrated that reusing workspaces or sharing working trees led to catastrophic code interleaved diffs, untracked changes, and report corruption.
- **Alternatives considered:** Branch new tasks from uncommitted working tree states or from historical `0fb8cbf` without R1 telemetry.
- **Why chosen:** Enforces the fundamental safety rule: **ONE SESSION = ONE WORKTREE = ONE TASK**. Branching from `5649772` ensures future work inherits proven telemetry capabilities while keeping Git history clean and traceable.
- **Consequences:** The next task must create a new worktree (e.g. `arpipe-acq-diag-r1`) based on `5649772`.

---

## 8. Historical Acquisition Causality Remains Unresolved
- **Decision:** The root cause of the 318 discover→download losses on 2026-09-11 is formally classified as **UNKNOWN**; current endpoint access variation must not be asserted as historical cause.
- **Date:** 2026-09-17
- **Evidence:** No per-attempt logs, HTTP response headers, or error traces were persisted on 2026-09-11 (`pm5_reason_code_completeness.csv` = 0.0%). All 194 successful downloads occurred in a single 4.5-minute burst.
- **Alternatives considered:** Assert that NSE CDN rate-limiting or IIT Kanpur network egress caused the 2026-09-11 failures based on contemporary observations.
- **Why chosen:** Scientific epistemology prohibits asserting an inference as fact without contemporaneous physical logging. Historical crawl termination or script aborts remain equally viable alternative hypotheses.
- **Consequences:** Historical uncertainty is permanently preserved. Contemporary findings are classified strictly as `CURRENTLY REPRODUCED` or `OBSERVED`, never as retroactively proven historical facts.

---

## 9. Keep Diagnostics Separate from Gold Truth
- **Decision:** Diagnostic metric scores (e.g. `orphan_start_frac > 0.03`, DPI, skew, heading form) do not automatically modify production grading, candidate filtering, or gold ground truth.
- **Date:** 2026-09-17
- **Evidence:** P-M2.2 demonstrated that candidate threshold `0.040` shifted page flag rates significantly (native: 25.2% → 21.5%; OCR: 41.8% → 31.3%), but its impact on true reading-order extraction cannot be confirmed without human-adjudicated labels.
- **Alternatives considered:** Adopt candidate threshold `0.040` into production based solely on distribution histograms.
- **Why chosen:** Uncalibrated threshold adjustments risk admitting scrambled or corrupted text into the final thesis corpus.
- **Consequences:** Production threshold remains pinned at `0.030`. Candidate `0.040` remains strictly exploratory until evaluated against gold FIT labels.

---

## 10. Worktree Governance: ONE SESSION = ONE WORKTREE = ONE TASK
- **Decision:** Every development or diagnostic session must operate in its own dedicated, isolated Git worktree; `arpipe-0.1.0` is permanently locked as read-only forensic evidence.
- **Date:** 2026-09-17
- **Evidence:** Step 0 forensics revealed 13 modified tracked files and corrupted reports in `arpipe-0.1.0` caused by concurrent, uncoordinated sessions. Step 0A and Step 0B demonstrated that lost baseline versions could not be recovered from Git objects.
- **Alternatives considered:** Continue using a single shared repository with branching.
- **Why chosen:** Concurrent agents and shell processes sharing a single working tree inevitably overwrite untracked files and create dirty uncommitted states.
- **Consequences:** Worktrees must never be shared across sessions or tasks; automated filesystem monitors halt tasks immediately if external modifications are detected.

---

## 11. Protected Modules: Zero Drift on `arpipe/patterns.py`
- **Decision:** Core regular expression module `arpipe/patterns.py` is locked against ad-hoc modifications; every diagnostic task must verify `git diff -- arpipe/patterns.py` is empty.
- **Date:** 2026-09-17
- **Evidence:** Past uncoordinated regex edits introduced subtle regressions (e.g. historical `is given below` pointer false positives, P33).
- **Alternatives considered:** Permit minor regex tweaks during feature tasks.
- **Why chosen:** Regex modifications have wide, non-linear effects across the entire corpus. Changes must be isolated and evaluated against dedicated pattern audit fixture suites.
- **Consequences:** R1 maintained 0 diff against base commit `0fb8cbf`. All future acquisition tasks must maintain 0 diff on `patterns.py`.

---

## 12. Do Not Rerun Completed Experiments
- **Decision:** Do not re-execute completed experiments (`P-M5`, `P-C0`, `P-C0R`, `R1`, `P-B3`, `P-M2.1`, etc.) merely to regenerate figures or metrics already supported by frozen, hash-verified artifacts.
- **Date:** 2026-09-17
- **Evidence:** Historical experiment reports and datasets are immutably preserved with SHA-256 digests in `ARPipe_Memory/evidence/INDEX.md`.
- **Alternatives considered:** Re-run full pipeline runs periodically to ensure freshness.
- **Why chosen:** Unnecessary reruns consume extensive compute and network resources, risk non-deterministic drift, and violate scientific reproducibility protocols.
- **Consequences:** Completed findings are cited directly from frozen evidence. Any rerun requires formal pre-registration and justification in project memory.

---

## 13. Memory Update Rule: Preserve Historical Findings
- **Decision:** When new empirical evidence clarifies, qualifies, or supersedes an earlier finding, the original finding must be preserved verbatim alongside the updated finding and an explicit relationship description.
- **Date:** 2026-09-17
- **Evidence:** Earlier conclusions regarding `cohort_fetch_manifest.jsonl` were initially hypothesized as a pre-fetch filter before P-C0 proved it was a post-hoc store export. Preserving both hypotheses documents the discovery trajectory.
- **Alternatives considered:** Silently overwrite outdated claims with current knowledge.
- **Why chosen:** Overwriting history creates "memory amnesia", obscures why certain design decisions were made, and destroys forensic auditability.
- **Consequences:** Master log and evidence register strictly append and annotate superseded items without erasing historical entries.

---

## 14. R1 Freeze
- **Decision:** R1 is frozen after successful local environment reproduction, deterministic test verification, and commit creation.
- **Date:** 2026-09-17
- **Evidence:** Dedicated local environment `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-fetch-telemetry\.venv` executed bounded deterministic tests with 32 passed, 0 failed, 0 skipped (P33, 15 R1 telemetry fixtures, discover/config regression). Commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` contains exactly the 9 verified files.
- **Alternatives considered:** Continue modifying R1 to add speculative retry/backoff repairs before freezing.
- **Why chosen:** R1's objective was strictly additive observability with zero behavioral change. Mixing failure telemetry and speculative repairs violates milestone boundaries.
- **Consequences:** R1 is immutably frozen at commit `56497721cb68c4831e6f225074b6bd7ea17bffb0`. The implementation cannot be silently modified or re-implemented.

---

## 15. R1 Isolation
- **Decision:** The R1 worktree (`D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-fetch-telemetry`) is permanently read-only for all subsequent work.
- **Date:** 2026-09-17
- **Evidence:** Worktree contamination in P-B2 Phase 1 proved that executing subsequent tasks in existing worktrees destroys baseline reproducibility and loses Git objects.
- **Alternatives considered:** Keep R1 worktree active for future diagnostic probe runs.
- **Why chosen:** To guarantee that the R1 verification milestone remains pristine and auditable as an immutable reference point.
- **Consequences:** No further code modifications, test executions, or commits are permitted in `arpipe-r1-fetch-telemetry`.

---

## 16. New-Worktree Rule
- **Decision:** All future engineering tasks must use a new dedicated worktree created specifically for that task.
- **Date:** 2026-09-17
- **Evidence:** Permanent worktree safety rule: ONE SESSION = ONE WORKTREE = ONE TASK. Shared worktrees in `arpipe-0.1.0` and `arpipe-pb2-p1-recovery` caused uncommitted file conflicts and forensic loss.
- **Alternatives considered:** Reuse existing worktrees to save disk space.
- **Why chosen:** Full workspace isolation prevents race conditions, untracked file overwrites, and dirty branch states.
- **Consequences:** The next engineering task will branch from commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` into a newly created dedicated worktree. The worktree path is marked TO BE CREATED until actually provisioned.

---

## 17. Acquisition Decision
- **Decision:** The next acquisition intervention must be selected only after analyzing R1 telemetry; no repair mechanism (retry count, backoff delays, session warming, scheduling) may be chosen in advance.
- **Date:** 2026-09-17
- **Evidence:** P-C0 and P-C0R demonstrated that failure modes vary dramatically over time (9/9 failures at 13:17 UTC vs 50/50 successes during P-C0R). Speculative fixes without telemetry risk addressing the wrong failure layer (e.g. tuning HTTP retries for transport resets).
- **Alternatives considered:** Pre-emptively increase retry counts or alter backoff delays.
- **Why chosen:** Scientific rigor requires empirical diagnosis of actual failure layers (L1 Connect, L3 HTTP status, L4 Receipt, L6 Validation) before altering acquisition logic.
- **Consequences:** Next task is restricted to analyzing R1 telemetry and determining the minimal evidence-supported experiment. Blind algorithmic changes are strictly forbidden.

---

## 18. Historical-Causality Decision
- **Decision:** R1 does not establish the historical cause of the 318 acquisition losses from 2026-09-11.
- **Date:** 2026-09-17
- **Evidence:** The crawl on 2026-09-11 persisted zero per-attempt telemetry, error logs, or HTTP status codes. The code running on that day in dirty working tree `arpipe-0.1.0` cannot be verified as byte-identical to commit `0fb8cbf`.
- **Alternatives considered:** Infer historical causality from modern probe success/failure patterns.
- **Why chosen:** Converting contemporary observations into retroactive historical proof violates epistemic rules (CURRENTLY REPRODUCED $\neq$ HISTORICAL PROOF).
- **Consequences:** The physical root cause of the historical 318 losses remains permanently classified as UNKNOWN. R1 provides observability for present and future acquisition only.

---

## 19. R1 Synthetic Matrix Epistemic Status
- **Decision:** The R1 deterministic telemetry matrix is controlled diagnostic evidence verifying software functionality, NOT historical population data.
- **Date:** 2026-09-17
- **Evidence:** `reports/r1_telemetry/r1_matrix_telemetry.jsonl` was generated by a deterministic synthetic test runner (`tools/generate_r1_telemetry.py`) exercising 9 specific code-branch fixtures under mock transports.
- **Alternatives considered:** Compute empirical failure proportions (e.g. 403 vs 429 vs timeout frequency) from the 17 matrix records.
- **Why chosen:** Treating a synthetic test fixture as an empirical population sample commits a severe category error.
- **Consequences:** Computing failure rates, dominant failure probabilities, expected historical distributions, or population estimates from the R1 matrix is strictly prohibited.

---

## 20. P-R1X Frozen Population Rule
- **Decision:** P-R1X will use the frozen 10-observation sample from `reports/pc0_sample_manifest.json` as its candidate population.
- **Date:** 2026-09-17
- **Evidence:** P-C0 established a pre-registered, hash-verified 10-observation sample (SHA-256: `394c628d842bdcf967b6dd82ab695fb4b17a88602c7c79c0b17561a3d931bb0e`) derived from `reports/pm5_stage_table.csv`, spanning 5 target zero-download FYs and 5 controls. P-C0R established a longitudinal baseline on this exact set.
- **Alternatives considered:** Draw a new sample from `pm5_stage_table.csv`, or test the full 318 un-downloaded cohort.
- **Why chosen:** Verbatim reuse of the frozen P-C0 sample provides direct continuity, eliminates degrees of freedom, and ensures minimal, non-destructive execution.
- **Consequences:** P-R1X executes a 100% census of this frozen 10-observation sample. No substitution or adaptive selection is permitted.

---

## 21. P-R1X Engineering Base Lineage
- **Decision:** P-R1X must use the frozen R1 implementation commit (`56497721cb68c4831e6f225074b6bd7ea17bffb0`) as its engineering base.
- **Date:** 2026-09-17
- **Evidence:** Commit `56497721cb68c4831e6f225074b6bd7ea17bffb0` contains the verified, reproducible telemetry implementation with 32 passing tests. Commit `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870` contains analysis reports and protocol design documentation only.
- **Alternatives considered:** Branch P-R1X from analysis commit `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870`.
- **Why chosen:** To maintain strict separation between engineering code and analytical documentation, preventing non-code report commits from becoming operational parents.
- **Consequences:** The engineering worktree for P-R1X must branch directly from `56497721cb68c4831e6f225074b6bd7ea17bffb0`.

---

## 22. Production Acquisition Invariance Decision
- **Decision:** No production acquisition repair (retries, backoff, timeouts, session warming, headers) is justified prior to collecting live diagnostic telemetry.
- **Date:** 2026-09-17
- **Evidence:** Historical cause cannot be established from surviving evidence. Live failure-layer distribution has never been observed under structured logging. P-C0R demonstrated 100% success (50/50) under standard client configuration during open windows and ruled out client header asymmetry.
- **Alternatives considered:** Pre-emptively adjust retry counts, exponential backoff multipliers, or add session warming headers.
- **Why chosen:** Speculative repairs without empirical layer identification risk masking root causes, triggering aggressive IP bans, or introducing regressions.
- **Consequences:** Production acquisition behavior remains strictly invariant. Decision status is recorded as `INSUFFICIENT EVIDENCE`.

---

## 23. P-R1X Dedicated Worktree Requirement
- **Decision:** P-R1X must be executed in a NEW dedicated worktree created specifically for that experiment.
- **Date:** 2026-09-17
- **Evidence:** Worktree safety rules: ONE SESSION = ONE WORKTREE = ONE TASK. Both `arpipe-r1-fetch-telemetry` (implementation milestone) and `arpipe-r1-telemetry-analysis` (analysis milestone) are permanently frozen and read-only.
- **Alternatives considered:** Reuse `arpipe-r1-fetch-telemetry` or `arpipe-r1-telemetry-analysis`.
- **Why chosen:** Reusing worktrees destroys baseline reproducibility, creates dirty states, and risks uncommitted file loss.
- **Consequences:** A new dedicated worktree must be provisioned from `56497721cb68c4831e6f225074b6bd7ea17bffb0` when executing P-R1X.

---

## 24. P-R1X Temporal Validity Adjudication & Interruption Handling
- **Decision:** Adjudicate Windows 1 and 2 as VALID scheduled temporal windows. Adjudicate Window 3 as POST_INTERRUPTION_SUPPLEMENTAL. Restrict the primary temporal analysis strictly to the 20 observations executed in Windows 1 and 2.
- **Date:** 2026-09-18
- **Evidence:** Timestamps in `reports/pr1x_observation_results.json` prove Windows 1 and 2 began within 2.1 ms of schedule. Window 3 missed its scheduled start (2026-09-17 23:05:00 UTC) by 9 hours, 12 minutes, 46 seconds due to host machine sleep / process suspension during the nominal wait loop, executing at 2026-09-18 08:17:46 UTC.
- **Alternatives considered:** (a) Count Window 3 as a valid third scheduled temporal window ("30/30 across 3 windows"); (b) Discard Window 3 entirely and erase records.
- **Why chosen:** Protocol Runbook Section 10 Interruption Rule strictly prohibits creating substitute timestamps or continuing under changed execution state. Window 3 cannot serve as a scheduled 3-window baseline. However, discarding evidence violates data preservation rules. Retaining Window 3 as supplemental preserves evidence without distorting temporal validity.
- **Consequences:** Primary analysis sample size is $N=20$ (10 target, 10 control; 100% success; 0 difference). Window 3 ($N=10$) is preserved separately as supplemental current-access evidence.

---

## 25. Future Repair Experiment Justification: INSUFFICIENT EVIDENCE
- **Decision:** A future acquisition repair experiment is **NOT JUSTIFIED** by current P-R1X evidence. Adjudicated verdict: **`INSUFFICIENT EVIDENCE`**.
- **Date:** 2026-09-18
- **Evidence:** P-R1X baseline acquisition succeeded on Attempt 1 across 20/20 valid observations and 10/10 supplemental observations without custom headers, session cookies, or pacing changes. The historical failure mode (`downloaded=False`) was NOT OBSERVED and NOT REPRODUCED.
- **Alternatives considered:** (a) Decide "YES" and design a browser-session simulation repair; (b) Decide "NO" and declare the acquisition problem permanently resolved.
- **Why chosen:** Designing an acquisition repair without reproducing the failure would constitute unguided speculation. Conversely, declaring the problem resolved ignores that the historical cause remains UNKNOWN, the temporal experiment was incomplete, and concurrency/market-hours conditions remain untested.
- **Consequences:** Production code and acquisition engine remain strictly invariant. The decision status is recorded as `INSUFFICIENT EVIDENCE`. This must NOT be interpreted as claiming the acquisition problem is solved.

---

## 26. Next Task: Historical Acquisition-Cause Evidence Audit
- **Decision:** The next project task is a systematic evidence audit of surviving historical artifacts to identify the 2026-09-11 failure layer before any repair experiment is designed.
- **Date:** 2026-09-18
- **Evidence:** Historical reason-code coverage is 0.0% in primary stage tables, but raw run artifacts, logs, discovery manifests, command outputs, and environment traces from 2026-09-11 may contain unindexed failure signals.
- **Alternatives considered:** Jump directly into designing another live crawling experiment or synthetic repair.
- **Why chosen:** Historical evidence must always take precedence over contemporary speculation. If historical artifacts contain the failure layer, future experiments can target the exact failure mechanism. If insufficient evidence exists, the empirical boundary is formally closed and documented.
- **Consequences:** The project advances to `HISTORICAL ACQUISITION-CAUSE EVIDENCE AUDIT` in read-only mode.

---

## 27. Historical Acquisition-Cause Evidence Audit Adjudication & Verdict
- **Decision:** Formally accept and freeze the Historical Acquisition-Cause Evidence Audit findings as the definitive baseline of what is historically knowable about the 2026-09-11 acquisition gap (`DISCOVERED` &rarr; `DOWNLOADED`).
- **Date:** 2026-09-18
- **Evidence:** Dedicated worktree `arpipe-pr1x-historical-audit` commit `1b6fd1f496b3634ee57bef6b926f7a79524c1cac`. Reconstructed all 318 loss identities with 0 duplicates, 0 missing, 0 invented (`reports/historical_loss_ledger.csv`). Established 0.0% reason-code completeness across surviving 2026-09-11 records (`pm5_reason_code_completeness.csv` = 0.0%). Proved request invocation state is `REQUEST_NOT_CONFIRMED`. Discovered silent drop path in pre-R1 `fetch_one()` where repeated 403/429/503 encounters yielded silent `return None`. Cryptographic source hashes verified 100% preserved (`pre_hash == post_hash` across all 29 inspected source files).
- **Alternatives considered:** (a) Postulate a specific failure mechanism (e.g. origin rate-limiting, IP blocking) based on contemporary P-C0 observations and design a targeted repair experiment; (b) Declare the 318 losses permanently unrecoverable without further empirical investigation.
- **Why chosen:** Protocol Section 33 strictly prohibits inventing missing historical facts. With 0.0% reason codes and unconfirmed request invocation, designing a targeted repair or reproduction experiment claiming to test a specific historical mechanism is unguided speculation.
- **Consequences:**
  1. Next-experiment decision is bindingly adjudicated as **`INSUFFICIENT HISTORICAL EVIDENCE FOR TARGETED EXPERIMENT`**.
  2. The project advances to an **`INFORMATION-GAP / OBSERVABILITY TASK`** (Roadmap Task 2: Evidence-Driven Acquisition Strategy).
  3. Worktree `arpipe-pr1x-historical-audit` is declared permanently **FROZEN / READ-ONLY**.

