# Protocol 03 — Acquisition & Failure Telemetry Protocol

**Status:** ACTIVE MANDATORY PROTOCOL  
**Enforcement:** ALL FETCH AND ACQUISITION WORK

---

## 1. Scope & Behavioral Neutrality
Acquisition failure telemetry repairs must adhere to strict behavioral invariance:
1. Telemetry emission must be **purely additive**.
2. Telemetry must never modify return values, exception types, retry counts, backoff schedules, timeouts, or terminal fall-through behavior.
3. Telemetry emission must be non-blocking: any writer exception (`PermissionError`, `OSError`, disk full) must be absorbed within the telemetry subsystem and never escape to disrupt acquisition control flow.

---

## 2. Schema Specification (`r1-v1`)
All acquisition failure telemetry must conform to schema `r1-v1`, outputting newline-delimited JSON (`JSONL`):

### Required Fields
- `telemetry_schema_version`: `"r1-v1"`
- `run_id`: Unique batch identifier
- `request_sequence_id`: 1-based sequential sequence counter per run
- `timestamp_utc`: ISO 8601 UTC timestamp
- `company_id`: Company ISIN
- `fy_end`: Target fiscal year
- `source`: Exchange portal (`nse`, `bse`, `screener`)
- `url_redacted`: Target URL with sensitive query parameters redacted
- `url_sha256`: SHA-256 hex digest of `url_redacted`
- `attempt_number`: 1-based sequential attempt index
- `terminal_state`: Boolean (true only when this attempt terminates the fetch)
- `retry_exhausted`: Boolean (true only when retry policy has been exhausted)
- `error_type`: Error classification (`HTTP_FAILURE`, `NETWORK_FAILURE`, `TIMEOUT`, `RESET`, `VALIDATION_FAILURE`, `OTHER_FAILURE`)
- `status_code`: HTTP status integer (e.g. 403, 429, 503) or `null` on network errors
- `error_message`: Error message string

### Optional Diagnostic Fields
- `exception_class`: Fully-qualified Python exception class name
- `first_failure_layer`: Architectural layer (`L0_DNS`, `L1_CONNECT`, `L2_TLS`, `L3_HTTP`, `L4_RECEIPT`, `L5_CLASSIFICATION`, `L6_VALIDATION`)
- `response_content_type`: String header value
- `bytes_received`: Integer byte count
- `elapsed_ms`: Floating point request duration in milliseconds

---

## 3. Secret & URL Redaction Policy
1. **Never Persist Secrets:** Authorization headers, cookies, set-cookies, API keys, session tokens, and passwords must never be written to telemetry.
2. **Query Parameter Redaction:** Any query parameter whose key contains `token`, `auth`, `key`, `secret`, `sig`, `session`, `pwd`, `credential`, or `X-Amz-*` must have its value replaced with `[REDACTED]`.
3. **Preserve URL Core:** Scheme, host, and path must remain unredacted to maintain forensic debuggability.

