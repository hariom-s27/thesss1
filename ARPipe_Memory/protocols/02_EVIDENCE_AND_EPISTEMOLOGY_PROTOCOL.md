# Protocol 02 — Evidence Hierarchy & Epistemological Boundaries

**Status:** ACTIVE MANDATORY PROTOCOL  
**Enforcement:** ALL THESIS ANALYSIS AND REPORTING

---

## 1. Epistemological Classifications
Every factual claim, measurement, and hypothesis in ARPipe must be explicitly categorized into one of seven mutually exclusive evidential statuses:

1. **`HISTORICALLY ESTABLISHED`**: Directly proven by committed Git history, immutable source snapshots, or hash-verified historical reports.
2. **`CURRENTLY REPRODUCED`**: Directly verified through live execution under controlled, documented test configurations.
3. **`INFERRED`**: Logically deduced from primary data, but lacking direct physical logging. Must be labelled as inference.
4. **`PLAUSIBLE`**: Theoretically compatible with known facts, but competing against alternative unrefuted hypotheses.
5. **`UNKNOWN`**: Missing, destroyed, or unpersisted records. Must be stated as unknown without speculation.
6. **`BLOCKED`**: Cannot proceed due to missing prerequisites or safety halt conditions.
7. **`RULED OUT`**: Empirically or logically disproven through counter-evidence or falsification trials.

---

## 2. Core Prohibitions
1. **Never Convert Inference into Fact:** A plausible hypothesis (e.g. "NSE CDN throttled the 2026-09-11 crawl") must never be asserted as an established historical truth.
2. **Never Silently Resolve Contradictions:** If two sources or runs produce conflicting numbers, record both, quantify the discrepancy, and investigate the divergence explicitly.
3. **Never Invent Missing Telemetry:** If an error code or timestamp was not persisted to disk, it is permanently **UNKNOWN** or **UNRECOVERABLE**. Do not reconstruct it from memory or plausibility.
4. **Preserve Prior Findings:** When new evidence changes interpretation, preserve the earlier finding verbatim, document the new evidence, explain the relationship, and record whether the earlier finding is superseded.

---

## 3. The Historical vs. Current Boundary
A strict boundary must be maintained between what happened on 2026-09-11 and what is observed today:
- **What is historically proven:** 194 successful downloads completed in a single 4.5-minute window. 318 discovered pairs have zero download records and zero error logs.
- **What is currently proven:** Probes on 2026-09-17 show that `nsearchives.nseindia.com` accessibility varies over time, and that client cookie/header asymmetry does not affect outcome.
- **The Bridge:** Observed current access variation makes a transient blocking mechanism plausible for 2026-09-11, but does **not prove** it.

