# Protocol 04 — Corpus Partitioning & Evaluation Protocol

**Status:** ACTIVE MANDATORY PROTOCOL  
**Enforcement:** ALL EXTRACTION VALIDATION AND PERFORMANCE METRICS

---

## 1. Population Hierarchy & Denominators
In accordance with the two-funnel architectural decision, evaluation metrics must explicitly define their population denominator:

| Denominator Population | Cardinality ($N$) | Proper Usage |
|:---|:---:|:---|
| **Intended Universe (V1/V2)** | 576 (V1) | Full academic coverage claims |
| **Discovered Candidates** | 512 | Discovery recall evaluation |
| **Downloaded Archives** | 194 | Extraction feasibility / text availability |
| **Located MD&A Sections** | 182 | Boundary accuracy & reading-order quality |
| **Accepted Documents** | 127 | Downstream NLP / climate exposure scoring |

**Prohibition:** Never divide accepted documents (127) by downloaded documents (194) and report it as "coverage of the universe". The denominator must be stated alongside every percentage.

---

## 2. Dataset Partitioning Guardrails
1. **Three Partitions:**
   - **`FIT` Set (~103 documents):** Training and algorithmic heuristic tuning.
   - **`HOLDOUT` Set:** Strictly untouched test set for unbiased generalization evaluation.
   - **`RESERVE` Set:** Edge-case stress testing (low DPI scans, legacy fonts, bilingual text).
2. **Leakage Prohibition:**
   - No developer or agent may inspect holdout labels or holdout outcomes during development.
   - Any tuning of thresholds (`orphan_start_frac`, regex boundaries, language filters) must be executed strictly against the `FIT` set.
3. **Formal Validation Sequence:**
   - **Stage F1:** Fit set evaluation against gold ground truth.
   - **Stage F2:** Single-pass evaluation against frozen Holdout set.
   - **Stage F3:** Stress testing on Reserve edge cases.

---

## 3. Pre-Registration & Hash Verification
1. Every experimental trial must pre-freeze its sample manifest and request configuration with SHA-256 hashes prior to running the first probe.
2. No post-hoc sample substitution is permitted. If an observation fails or is disqualified, the disqualification and reason must be reported explicitly in the final report.

