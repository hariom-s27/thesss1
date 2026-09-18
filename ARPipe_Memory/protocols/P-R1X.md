# P-R1X — Instrumented Acquisition Telemetry Pilot Protocol

**Protocol Version:** P-R1X v1.2 (Final Execution Protocol)  
**Protocol Status:** EXECUTED & ADJUDICATED (`INCOMPLETE AS A THREE-WINDOW TEMPORAL EXPERIMENT; VALID TWO-WINDOW PRIMARY SUBSET + POST-INTERRUPTION SUPPLEMENTAL DATA`)  
**Protocol Name:** P-R1X — Instrumented Acquisition Telemetry Pilot  
**Date Frozen:** 2026-09-17  
**Date Executed:** 2026-09-17 – 2026-09-18  
**Date Adjudicated:** 2026-09-18  
**Required Engineering Base:** `56497721cb68c4831e6f225074b6bd7ea17bffb0` (Frozen R1 Implementation)  
**Analytical / Protocol Reference:** `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870` (`reports/r1_telemetry_analysis.md`)  
**Execution Commit:** `0b1d595407eacb13b115811cdb610b3e1f56a767` (`arpipe-pr1x-execution`)  
**Adjudication Commit:** `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32` (`arpipe-pr1x-adjudication`)  

---

## 1. Lineage & Base SHA Requirement

> [!CRITICAL]
> **ENGINEERING BASE REQUIREMENT:**  
> Any future engineering worktree executing P-R1X **MUST** be branched directly from:  
> **`56497721cb68c4831e6f225074b6bd7ea17bffb0`** (Frozen R1 Implementation).  
> **`56497721cb68c4831e6f225074b6bd7ea17bffb0`** (Frozen R1 Implementation Commit).  
> 
> The R1 telemetry-analysis commit (`3beee249db36f9fdd1a8a2e01d6fdc3c6024d870`) contains analysis reports and protocol design documentation only. It is **NOT** the engineering base for P-R1X.
> The R1 telemetry-analysis commit (**`3beee249db36f9fdd1a8a2e01d6fdc3c6024d870`**) contains analysis reports and protocol evidence only. It is **NOT** the engineering base and **MUST NOT** be used as the P-R1X engineering branch point.

```
Engineering Lineage:
0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14
0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14  (P-B7 baseline)
    ↓
R1 implementation (telemetry-only repair)
R1 implementation (attempt-level telemetry repair)
    ↓
56497721cb68c4831e6f225074b6bd7ea17bffb0  <--- REQUIRED ENGINEERING BASE FOR P-R1X
    ↓
P-R1X engineering worktree (TO BE CREATED)
[P-R1X engineering worktree — TO BE CREATED AT EXECUTION TIME ONLY]

Separate Analytical Lineage:
3beee249db36f9fdd1a8a2e01d6fdc3c6024d870  <--- Protocol Evidence & Analysis Reference Only
3beee249db36f9fdd1a8a2e01d6fdc3c6024d870  <--- Analytical / Protocol Evidence Only (DO NOT BRANCH FROM THIS)
```

---

## 2. Objective
Deploy the frozen R1 attempt-level failure telemetry engine (`r1-v1`) in a bounded live diagnostic pilot to observe actual failure layers, status codes, and terminal states on the frozen P-C0 sample.
## 2. Objective & Diagnostic Boundary

The purpose is to distinguish, where observed:
- Transport/connect failure (`first_failure_layer in ('L1_CONNECT', 'L4_RECEIPT')`, `status_code=null`)
- Receipt/timeout failure (`L4_RECEIPT`, `ReadTimeout`)
Deploy the frozen R1 attempt-level failure telemetry engine (`r1-v1`) in a strictly bounded live diagnostic pilot on the frozen P-C0 sample across three pre-scheduled temporal observation windows to observe actual failure layers, status codes, and terminal states.

The diagnostic purpose is to classify failure layers where observed:
- Transport / connect failure (`first_failure_layer in ('L1_CONNECT', 'L4_RECEIPT')`, `status_code=null`)
- Receipt / timeout failure (`L4_RECEIPT`, `ReadTimeout`)
- HTTP-layer rejection (`L3_HTTP`, status codes 403, 429, 503)
- Payload validation failure (`L6_VALIDATION`, `BadZipFile` or corrupt PDF)
- Other telemetry categories supported by schema `r1-v1`
- Payload validation failure (`L6_VALIDATION`, `BadZipFile` or corrupt PDF requiring repair)
- Other telemetry categories defined in schema `r1-v1`

**Diagnostic Boundary:** The pilot is strictly diagnostic. It is **NOT** a production repair.
**Diagnostic Boundary:** The pilot is strictly diagnostic. It is **NOT** a production repair, nor does it alter production pipeline behavior.

---

## 3. Frozen Candidate Population
## 3. Verified R1 HTTP Client & Fetch Configuration

Inspect and preserve the **actual committed R1 fetch/client configuration** from commit `56497721cb68c4831e6f225074b6bd7ea17bffb0`:

- **HTTP Library:** `httpx` (using `httpx.Client`)
- **Client Configuration:**
  ```python
  cl = httpx.Client(
      headers={"User-Agent": discover.UA},
      timeout=120,
      follow_redirects=True,
  )
  ```
- **User-Agent String:**
  `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36` (`discover.UA`)
- **Streaming Fetch Request:**
  ```python
  with client.stream("GET", ref.url, follow_redirects=True, timeout=120.0) as r:
      ...
  ```
- **Payload Streaming & Max Bytes:**
  - Chunk size: `1 << 18` (256 KB)
  - Buffer limit: `max_bytes = 400 << 20` (400 MB)
- **Strict Configuration Invariants:**
  - Do **NOT** introduce `requests.Session` or `requests` library.
  - Do **NOT** introduce any alternative HTTP client or library (e.g. `aiohttp`, `urllib3`, `curl_cffi`).
  - Do **NOT** introduce new or modified headers (e.g. `Accept`, `Referer`, `Sec-Ch-Ua`).
  - Do **NOT** introduce cookies or session state reuse in the fetch client.
  - Do **NOT** introduce a new User-Agent string.
  - The diagnostic variable must remain the **temporal observation window**, NOT a client-configuration intervention.

---

## 4. Verified R1 Pacing & Rate Limiting Behavior

Inspect and preserve the **actual committed R1 pacing behavior** from commit `56497721cb68c4831e6f225074b6bd7ea17bffb0`:

- **Rate Limiter Class:** `fetch.HostLimiter` (token bucket per netloc host).
- **Interval Rule:**
  `min_interval: float = 1.5` seconds per target host (CLI default `--min-interval 1.5`).
- **Limiter Execution:**
  Called at the start of each attempt (`limiter.wait(ref.url)`), which enforces a minimum elapsed time of 1.5 seconds between requests targeting the same host (`urlparse(url).netloc`):
  ```python
  def wait(self, url: str) -> None:
      host = urlparse(url).netloc
      with self._lock:
          now = time.monotonic()
          last = self._last.get(host, 0.0)
          delay = self.min_interval - (now - last)
          self._last[host] = max(now, last + self.min_interval)
      if delay > 0:
          time.sleep(delay)
  ```
- **Retry Backoff Delays:**
  - HTTP 403, 429, 503: `time.sleep(5 * (attempt + 1) ** 2)`  
    (Attempt 1 failure: 5s sleep; Attempt 2 failure: 20s sleep; Attempt 3 failure: 45s sleep).
  - General Exceptions (Network, Timeout, Reset): `time.sleep(2 * (attempt + 1))`  
    (Attempt 1 failure: 2s sleep; Attempt 2 failure: 4s sleep; Attempt 3 failure: 6s sleep).
- **Strict Pacing Invariants:**
  - Do **NOT** invent or enforce an artificial "1 request/second" rate.
  - Do **NOT** invent or enforce an artificial "2 seconds/request" rate.
  - Do **NOT** introduce any new pacing rate or throttling intervention outside verified R1 behavior.

---

## 5. Frozen Candidate Population

- **Authoritative Population Source:** P-C0 frozen sample manifest:  
  `reports/pc0_sample_manifest.json` (SHA-256: `394c628d842bdcf967b6dd82ab695fb4b17a88602c7c79c0b17561a3d931bb0e`)
- **Originating Frozen Source:** P-M5 stage table:  
  `reports/pm5_stage_table.csv` (SHA-256: `30e93b59ac689f00fab182583fb25883322e429be42b4ba14e13a1011b916dc9`)
- **Pilot Population Size:** $N = 10$ distinct observations.
- **Population Size:** $N = 10$ distinct observations.
  > [!NOTE]
  > This is a **census of the frozen P-C0 pilot sample**. It is **NOT** a census of the 576-observation universe.
- **Sampling Discipline:** 100% census of the frozen P-C0 pilot sample. No substitution. No adaptive sampling. No post-hoc replacement.

### Target Observations ($N = 5$, `DOWNLOAD_ZERO_FY`)
1. `INE002A01018::FY2010` (Reliance Industries Limited, FY2010, NSE)
2. `INE040A01034::FY2014` (HDFC Bank Limited, FY2014, NSE)
3. `INE081A01020::FY2016` (Tata Steel Limited, FY2016, NSE)
4. `INE171A01029::FY2021` (The Federal Bank Limited, FY2021, NSE)
5. `INE226A01021::FY2022` (Voltas Limited, FY2022, NSE)
---

### Control Observations ($N = 5$, `DOWNLOAD_NONZERO_FY_CONTROL`)
6. `INE002A01018::FY2012` (Reliance Industries Limited, FY2012, NSE)
7. `INE009A01021::FY2013` (Infosys Limited, FY2013, NSE)
8. `INE040A01034::FY2017` (HDFC Bank Limited, FY2017, NSE)
9. `INE044A01036::FY2018` (Sun Pharmaceutical Industries Limited, FY2018, NSE)
10. `INE081A01020::FY2024` (Tata Steel Limited, FY2024, NSE)
## 6. Frozen Observation Order

---
The 10 observations must be executed in the **exact sequential order** defined in `reports/pc0_sample_manifest.json`. The **same order** must be strictly maintained across all three temporal windows:

## 4. Sampling Rule
100% census of the frozen pilot sample.  
**Strict Prohibitions:** No substitution. No adaptive selection. No post-hoc replacement.
| Sequence | Observation ID | Company Name | FY | Group | Target URL |
|---|---|---|---|---|---|
| 1 | `INE002A01018::FY2010` | Reliance Industries Limited | 2010 | `DOWNLOAD_ZERO_FY` | `https://nsearchives.nseindia.com/annual_reports/AR_RELIANCE_2009_2010_20082010120000.zip` |
| 2 | `INE040A01034::FY2014` | HDFC Bank Limited | 2014 | `DOWNLOAD_ZERO_FY` | `https://nsearchives.nseindia.com/annual_reports/AR_3393_HDFCBANK_2013_2014_12062014114216.zip` |
| 3 | `INE081A01020::FY2016` | Tata Steel Limited | 2016 | `DOWNLOAD_ZERO_FY` | `https://nsearchives.nseindia.com/annual_reports/AR_9362_TATASTEEL_2015_2016_16082016104323.zip` |
| 4 | `INE171A01029::FY2021` | The Federal Bank Limited | 2021 | `DOWNLOAD_ZERO_FY` | `https://nsearchives.nseindia.com/annual_reports/AR_18152_FEDERALBNK_2020_2021_17062021235201_18062021070010.zip` |
| 5 | `INE226A01021::FY2022` | Voltas Limited | 2022 | `DOWNLOAD_ZERO_FY` | `https://nsearchives.nseindia.com/annual_reports/AR_19956_VOLTAS_2021_2022_28052022144748_05282022150002.zip` |
| 6 | `INE002A01018::FY2012` | Reliance Industries Limited | 2012 | `DOWNLOAD_NONZERO_FY_CONTROL` | `https://nsearchives.nseindia.com/annual_reports/AR_RELIANCE_2011_2012_29062012101059.zip` |
| 7 | `INE009A01021::FY2013` | Infosys Limited | 2013 | `DOWNLOAD_NONZERO_FY_CONTROL` | `https://nsearchives.nseindia.com/annual_reports/AR_27_INFY_2012_2013_20062013105245.zip` |
| 8 | `INE040A01034::FY2017` | HDFC Bank Limited | 2017 | `DOWNLOAD_NONZERO_FY_CONTROL` | `https://nsearchives.nseindia.com/annual_reports/AR_10840_HDFCBANK_2016_2017_25072017151900.zip` |
| 9 | `INE044A01036::FY2018` | Sun Pharmaceutical Industries Limited | 2018 | `DOWNLOAD_NONZERO_FY_CONTROL` | `https://nsearchives.nseindia.com/annual_reports/AR_13921_SUNPHARMA_2017_2018_01102018175233.zip` |
| 10 | `INE081A01020::FY2024` | Tata Steel Limited | 2024 | `DOWNLOAD_NONZERO_FY_CONTROL` | `https://nsearchives.nseindia.com/annual_reports/AR_24166_TATASTEEL_2023_2024_2206202419194.pdf` |

**Strict Execution Order Invariants:**
- Do **NOT** reorder observations between windows.
- Do **NOT** sort observations differently between windows.
- Do **NOT** substitute or skip observations.
- Do **NOT** adapt order after observing outcomes in preceding observations.
- The observation order is frozen before execution.

---

## 5. Independent Variable
**Pre-scheduled temporal observation windows:**  
Testing the frozen 10-observation sample across three pre-specified observation windows:
- Window 1: $T_0$
- Window 2: $T_0 + 30$ minutes
- Window 3: $T_0 + 60$ minutes
## 7. Temporal Window Design & Execution Rules

*Rule:* Do not alter the schedule after observing intermediate results.
### 7.1 Predeclared Schedule & UTC Timestamp Freeze
Three temporal observation windows are predeclared:
- **Window 1:** $T_0$
- **Window 2:** $T_0 + 30\text{ minutes}$
- **Window 3:** $T_0 + 60\text{ minutes}$

> [!IMPORTANT]
> **PRE-EXECUTION TIMESTAMP FREEZE:**  
> Before the first live network request is executed, the execution agent **MUST** convert $T_0$, $T_0 + 30\text{m}$, and $T_0 + 60\text{m}$ into exact UTC timestamps in the protocol runbook:
> - `Window 1: YYYY-MM-DD HH:MM:SS UTC`
> - `Window 2: YYYY-MM-DD HH:MM:SS UTC`
> - `Window 3: YYYY-MM-DD HH:MM:SS UTC`
> 
> Once frozen, these exact timestamps **MUST NOT** be altered after observing intermediate results.

### 7.2 Window Execution Discipline
Each temporal window has **ONE predeclared START timestamp**.

At each window start:
1. Begin the frozen 10-observation sequence at the exact scheduled START timestamp.
2. Execute in the frozen observation sequence order (1 through 10).
3. Preserve the frozen R1 client and fetch behavior throughout.
4. Record the actual start timestamp of every observation (`observation_start_utc`).
5. Record the actual end timestamp of every observation (`observation_end_utc`).

**Critical Timing Rules:**
- The temporal window is defined strictly by its **predeclared START timestamp**, NOT by the completion time of the previous observation.
- Do **NOT** delay observations to improve an outcome.
- Do **NOT** accelerate observations artificially.
- Do **NOT** reorder observations.
- Do **NOT** reschedule an observation because of an error or status code.
- Do **NOT** shift or move a window after seeing outcomes.
- Any unavoidable execution deviation (e.g. OS scheduling jitter) must be recorded explicitly rather than hidden.

---

## 6. Controlled Variables
Execute using the frozen R1 implementation and baseline acquisition behavior.
## 8. Non-Discretionary Stop Conditions & Safety Protections

Do **NOT** change:
- retry count (preserved at `retries = 3`)
- retry order
- retry delays / backoff (preserved at `5 * (attempt + 1) ** 2`)
- timeout (preserved at `120.0s`)
- headers
- cookies
- User-Agent
- HTTP client behavior
- URL selection
- discovery logic
### 8.1 Ordinary Failures Are Observations, NOT Stop Conditions
In a diagnostic telemetry pilot, ordinary acquisition failures are data points. They **MUST NOT** trigger early termination.

Use the existing standard client configuration. Pacing must use `HostLimiter` with $\ge 2.0$s delay between consecutive requests.
The following failure modes **MUST NOT** by themselves trigger pilot cessation:
- HTTP `403 Forbidden`
- HTTP `429 Too Many Requests`
- HTTP `503 Service Unavailable`
- Socket or HTTP timeouts (`ReadTimeout`, `ConnectTimeout`)
- Connection resets (`RemoteProtocolError`, `ConnectionResetError`)
- Network reachability / connect errors (`ConnectError`)
- Other ordinary R1 telemetry-classified failures (`L1_CONNECT`, `L3_HTTP`, `L4_RECEIPT`, `L6_VALIDATION`)

### 8.2 Explicit Predeclared Safety Stop Conditions
The pilot must halt **ONLY** for explicitly predeclared, non-discretionary safety and access-protection conditions:
1. **Explicit WAF / Cloud Intercept Challenge:** Remote origin returns a CAPTCHA, Cloudflare Challenge, Akamai bot challenge page, or anti-bot challenge interstitial.
2. **Explicit Provider Blocking Page:** Remote origin serves an explicit notice indicating an IP ban, account ban, or permanent access prohibition.
3. **Credential / Security Issue:** Authentication or TLS certificate trust boundary breakdown indicating systemic origin compromise or unauthorized privilege requirement.
4. **Provider Instruction Requiring Cessation:** Remote origin administrator, security team, or provider notice explicitly demanding crawler cessation.
5. **Infrastructure Safety Condition:** Local environment failure (e.g. disk corruption, unrecoverable socket exhaustion, host OS crash) that makes continuing requests unsafe.

> [!CAUTION]
> **PRE-EXECUTION STOP SIGNAL DECLARATION:**  
> Before the first live request is fired, the execution agent **MUST** document the exact observable signal corresponding to each safety stop.  
> No new stop conditions may be invented after observing live results.  
> The standard bounded retry cap (3 attempts per observation) and bounded sample cap ($N=10$) remain strictly enforced.

---

## 7. Measurements
For every actual attempt executed across all windows, retain structured R1 telemetry where produced:
## 9. Preserved Frozen R1 Baseline Behavior

The following parameters and behaviors from the frozen R1 implementation commit (`56497721cb68c4831e6f225074b6bd7ea17bffb0`) are strictly preserved:
- **Retry Count:** Fixed at `retries = 3` attempts per observation.
- **Retry Delays & Backoff:**
  - HTTP 403/429/503: `5 * (attempt + 1) ** 2` seconds
  - Exceptions: `2 * (attempt + 1)` seconds
- **Timeout:** Fixed at `120.0s` per request stream.
- **Candidate URL Selection:** Highest priority available (`NSE > BSE > Screener`).
- **Discovery Logic:** Verbatim as manifest.
- **Acceptance & Validation Logic:** Verbatim R1 validation (`BadZipFile`, empty ZIP, corrupted PDF, `qpdf` repair).
- **Telemetry Schema:** Verbatim `r1-v1`.

---

## 10. Measurements & Observables

### 10.1 Attempt-Level Telemetry (`r1-v1`)
For every attempt executed across all windows, retain the fields emitted by the frozen R1 implementation:
- `run_id` (string UUID / run identifier)
- `request_sequence_id` (integer)
- `attempt_number` (1, 2, 3)
- `terminal_state` (`true` / `false`)
- `retry_exhausted` (`true` / `false`)
- `status_code` (integer or `null`)
- `terminal_state` (boolean: `true` if final attempt of sequence or unrecoverable validation error)
- `retry_exhausted` (boolean: `true` if attempt reached retry limit without success)
- `status_code` (integer HTTP status code, or `null` if transport failure)
- `first_failure_layer` (`L0_DNS`, `L1_CONNECT`, `L2_TLS`, `L3_HTTP`, `L4_RECEIPT`, `L6_VALIDATION`)
- `error_type` (`HTTP_FAILURE`, `NETWORK_FAILURE`, `TIMEOUT`, `RESET`, `VALIDATION_FAILURE`)
- `exception_class` where available
- `elapsed_ms`
- `bytes_received` where available
- `url_redacted` / `url_sha256`
- `run_id`, `request_sequence_id`, `timestamp_utc`
- `exception_class` (e.g. `httpx.ReadTimeout`, `httpx.ConnectError`, `zipfile.BadZipFile`, or `null`)
- `elapsed_ms` (floating-point duration in milliseconds)
- `bytes_received` (integer byte count)
- `url_redacted` (string)
- `url_sha256` (SHA-256 hex digest of target URL)
- `company_id`, `fy_end`, `source`, `error_message`, `response_content_type`, `timestamp_utc`

Also record the observation-level final outcome (`StoredDoc`, `None`, or raised exception).
### 10.2 Observation-Level & Window Telemetry
In addition to attempt-level records, record:
- `window_id` (`Window 1`, `Window 2`, `Window 3`)
- `observation_start_utc` (actual ISO-8601 UTC timestamp at observation launch)
- `observation_end_utc` (actual ISO-8601 UTC timestamp upon completion/terminal state)
- `observation_outcome` (`StoredDoc`, `None`, or raised unhandled exception)

---

## 8. Success Criteria
## 11. Diagnostic Success & Failure Criteria

### 11.1 Success Criteria
The experiment succeeds diagnostically if:
1. All three scheduled windows execute as specified.
2. Structured, interpretable attempt-level telemetry is produced and persisted to JSONL for any failed attempts.
3. Observation-level outcomes are comprehensively logged.
1. All three scheduled temporal observation windows execute at their predeclared START timestamps.
2. Structured, schema-compliant `r1-v1` attempt-level telemetry is captured and persisted to JSONL for all failed attempts.
3. Observation-level outcomes, start timestamps, and end timestamps are comprehensively logged.
4. Telemetry writer failure count is exactly zero.

---

## 9. Failure Criteria
### 11.2 Failure Criteria
The experiment fails diagnostically if:
1. Telemetry is missing unexpectedly upon attempt failure.
1. Telemetry is missing or unpersisted upon attempt failure.
2. The frozen population cannot be executed as specified.
3. Experimental conditions drift during execution.
4. Adaptive substitution of observations occurs.
5. Unexpected production code changes are introduced.
5. Unauthorized client, pacing, or production code alterations are introduced.

---

## 10. Stop Conditions
Immediately halt execution if:
1. Protocol conditions cannot be maintained.
2. A production behavior change becomes necessary.
3. Unexpected source repository or exchange structural changes occur.
4. The sample integrity cannot be preserved.
5. Remote origin issues an explicit IP-ban or persistent block.
## 12. What P-R1X Cannot Prove

1. **Historical Causality:** P-R1X cannot retroactively reconstruct the exact historical 2026-09-11 failure distribution.
2. **Historical Root Cause:** P-R1X cannot by itself prove the historical root cause of the historical 318 document losses.
3. **Unsampled Cohorts:** P-R1X cannot prove the origin behavior for unsampled zero-download FYs (FY2019, FY2020, FY2023) or unsampled companies.
4. **Burst Scaling:** P-R1X uses polite pacing ($N=10$, `HostLimiter` with `min_interval=1.5`s); it cannot prove origin behavior under high-concurrency burst load (e.g. 512 simultaneous requests).

---

## 11. What P-R1X Cannot Prove
1. **Historical Causality:** P-R1X cannot retroactively reconstruct the exact historical 2026-09-11 failure distribution.
2. **Historical Root Cause:** P-R1X cannot by itself prove the historical root cause of the 318 losses.
3. **Unsampled Cohorts:** P-R1X cannot prove the behavior of unsampled zero-download FYs (FY2019, FY2020, FY2023) or unsampled companies.
4. **Burst Scaling:** P-R1X uses polite pacing ($N=10$, 2.0s delay); it cannot prove origin behavior under high-concurrency 512-request burst load.
## 13. Changes from P-R1X v1.0

P-R1X can only characterize failure behavior observed under the frozen current protocol.
1. **HTTP/client configuration corrected** to use the exact committed R1 fetch/client configuration (`httpx.Client(headers={"User-Agent": discover.UA}, timeout=120, follow_redirects=True)`).
2. **Invented "requests-session headers" configuration removed.**
3. **Invented "1 request/second" pacing removed.**
4. **Pacing now uses the exact verified R1 behavior** (`HostLimiter(min_interval=1.5)` per host netloc, with committed retry delay schedules).
5. **Ordinary 403/429/503/timeouts/resets/connections are observations, not automatic stop conditions.**
6. **Safety stop conditions must be defined before execution** and restricted to non-discretionary access-protection / WAF triggers.
7. **Exact UTC window START timestamps must be frozen before execution** and held immutable.
8. **Observation order is frozen to the exact order in the P-C0 sample manifest** and must remain identical across all three windows.
9. **Actual per-observation start/end timestamps must be recorded** alongside attempt-level telemetry.

---

## 14. Execution Prohibition & Worktree Rules

> [!CAUTION]
> **DO NOT EXECUTE P-R1X:**  
> This protocol document amendment is strictly memory and specification hardening.  
> 
> Under no circumstances during this task shall:
> - the P-R1X engineering worktree be created
> - live network requests be fired
> - NSE or remote endpoints be queried
> - samples be executed
> - live telemetry files be produced
> - production repositories or worktrees be altered
> 
> **P-R1X Status:** DESIGNED — NOT EXECUTED.
