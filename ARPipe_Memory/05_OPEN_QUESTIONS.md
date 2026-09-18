# ARPipe — Open Questions and Research Hypotheses

This register documents active technical ambiguities, open research questions, and testable hypotheses across the ARPipe thesis. In accordance with project epistemological rules, open questions must never be silently resolved without direct empirical evidence.

---

## 1. Acquisition & Historical Causality

> [!NOTE]
> **Epistemic Principle:** P-R1X verified current endpoint reachability and client viability under single-worker polite pacing. It did **not** reproduce the historical failure and does **not** recover historical failure data. The historical cause of the 318 losses remains strictly **UNKNOWN / NOT ESTABLISHED** and open.

### OQ-ACQ-1: What caused the historical 2026-09-11 discovered $\rightarrow$ downloaded losses?
- **Status:** CLOSED — PERMANENT HISTORICAL INFORMATION GAP ESTABLISHED
- **Historical Audit Finding:** The Historical Acquisition-Cause Evidence Audit (commit `1b6fd1f496b3634ee57bef6b926f7a79524c1cac`) established that surviving records contain exactly **0.0% reason codes** (0 of 318). Request invocation state is **`REQUEST_NOT_CONFIRMED`** under `NO_REQUEST_EVIDENCE != REQUEST_DID_NOT_OCCUR`. Pre-R1 code silently dropped repeated 403/429/503 errors without setting `last_err` or logging to disk. What physically occurred on 2026-09-11 is historically unknowable from surviving evidence.
- **Resolution:** Formally closed with finding `UNKNOWN_AFTER_REVIEW`. Advances to Task 2 (Information-Gap / Observability Task) to classify the 318 cohort under structured R1 telemetry.

### OQ-ACQ-2: Can the historical failure condition be reproduced?
- **Status:** CLOSED — INSUFFICIENT HISTORICAL EVIDENCE FOR TARGETED EXPERIMENT
- **Context:** P-C0R (50/50 success) and P-R1X (20/20 valid success, 10/10 supplemental success) failed to reproduce any acquisition failure under polite pacing (`min_interval=1.5`s) and standard `httpx.Client`.
- **Historical Audit Decision:** With 0.0% reason codes and unconfirmed request invocation, designing a targeted reproduction or repair experiment claiming to test a specific historical mechanism is unguided speculation (`INSUFFICIENT HISTORICAL EVIDENCE FOR TARGETED EXPERIMENT`).
- **Resolution:** No targeted reproduction experiment will be run. The project advances to Task 2 to test all 318 un-downloaded pairs under R1 telemetry.

### OQ-ACQ-3: Is there time-dependent acquisition behavior not captured by the two valid windows?
- **Status:** OPEN / INCOMPLETE TEMPORAL OBSERVATION
- **Context:** P-R1X produced a valid two-window baseline at 20:05 and 21:35 UTC (01:35 and 03:05 IST), well outside Indian market hours. Window 3 missed its scheduled 23:05 UTC slot due to host sleep and ran at 08:17 UTC (13:47 IST, during market hours) as post-interruption supplemental data.
- **Open Issue:** Does `nsearchives.nseindia.com` enforce periodic maintenance windows, time-of-day access rules, or market-hours throttling that were not systematically evaluated by the two nighttime windows?
- **Resolution Path:** Assess whether future multi-window temporal probing during active trading hours is warranted after concluding the historical audit.

### OQ-ACQ-4: Does high-concurrency / full-universe acquisition behave differently from the single-worker pilot?
- **Status:** OPEN / UNTESTED AT SCALE
- **Context:** P-R1X tested an $N=10$ pilot sample sequentially with exactly 1 worker and 1.5s delay. The historical crawl operated across 576 company-years (512 discovered pairs) and may have utilized multiple workers, concurrent requests, or tighter intervals.
- **Open Issue:** Does high concurrency, connection pool exhaustion, or burst crawling trigger origin rate-limiting (429) or IP resets (`CURLE_RECV_ERROR 56`) that are completely absent during single-worker polite access?
- **Resolution Path:** Evaluate concurrency dependencies only after completing the historical artifact audit and establishing historical baseline parameters.

### OQ-ACQ-5: Can surviving historical logs or external evidence classify the historical failure layer?
- **Status:** CLOSED — COMPLETED AUDIT (0.0% HISTORICAL COVERAGE)
- **Historical Audit Finding:** All 29 surviving historical source artifacts across the repository, worktrees, and cache stores were inventoried and hashed (`pre_hash == post_hash`). Exactly 0 HTTP status codes, socket exceptions, or terminal error logs survive. Reason-code completeness is 0.0%.
- **Resolution:** Confirmed that historical logging was strictly unpersisted (stderr only, or silent drop in `fetch_one`). All 318 losses recorded as `REASON_CODE_MISSING` / `UNKNOWN_AFTER_REVIEW`. Sealed permanently in Decision 27.

---



## 2. Extraction Quality & Section Boundaries

### OQ-EXT-1: What is the optimal production threshold for `orphan_start_frac`?
- **Status:** OPEN / EXPLORATORY (P-M2.2)
- **Context:** Current production threshold is `0.030`. Sensitivity analysis tested `[0.020, 0.060]`. `0.040` flags 21.5% of native pages (vs. 25.2% at `0.030`) and 31.3% of OCR pages (vs. 41.8% at `0.030`).
- **Open Issue:** Modifying the production threshold without human-verified gold labels risks admitting scrambled reading order into the downstream thesis corpus.
- **Resolution Path:** Block any production threshold change until Universe V2 is frozen and gold-standard evaluation labels (~103 FIT labels) are adjudicated.

### OQ-EXT-2: How should legacy Indian fonts be routed between native extraction and OCR?
- **Status:** OPEN (P-B3 / P-B5)
- **Context:** P-B3 established that legacy font evidence is present on 2,075 pages (5.47%), but 1,625 of those pages (78.3%) have native text that is apparently clean.
- **Open Issue:** Forcing full rasterize-and-OCR on all legacy font pages introduces OCR noise on pages whose native extraction was already legible.
- **Resolution Path:** Develop a selective routing rule that triggers OCR only when legacy font evidence coincides with native text corruption (Quadrant B in P-B3 2×2 matrix: 437 pages).

### OQ-EXT-3: Can annexure-labelled MD&A headings be segmented without false positives?
- **Status:** OPEN (P-M4)
- **Context:** Only 3 annexure-labelled MD&A sections were identified in the 18 eligible fit documents. Pointer language like "Management Discussion and Analysis is given in Annexure IV" must not be mistaken for the actual section heading.
- **Resolution Path:** Combine typographical cues (font size, bold style) with bookmark hierarchy (S1/S2) and negative pointer guards (P33 regex patterns).

---

## 3. Corpus Definition & Thesis Downstream Impact

### OQ-CORP-1: Which of the 318 missing company-years are genuinely recoverable?
- **Status:** OPEN (Active focus of post-R1 diagnosis)
- **Context:** Some company-years may be missing due to corporate events (incorporation date post-2010, delisting, merger/amalgamation) or regulatory filing gaps on exchange portals.
- **Resolution Path:** Separate technical retrieval failures (recoverable via retry/re-fetch) from genuine non-existence (documented with frozen exclusion rules).

### OQ-CORP-2: What is the final target size and composition of Universe V2?
- **Status:** BLOCKED ON ACQUISITION DIAGNOSIS
- **Context:** The target was originally 576 company-years (36 companies × 16 years). Universe V2 cannot be finalized until acquisition feasibility is established.
- **Resolution Path:** Complete R1 diagnostic probes → classify re-fetchable vs. excluded rows → freeze Universe V2 manifest.
