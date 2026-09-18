# Step 0 — Dirty-Worktree Discovery & Forensic Classification

**Status:** HISTORICALLY ESTABLISHED  
**Target HEAD:** `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` (branch `main`)  
**Forensic Directory:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-step0-forensics`  
**Primary Artifact:** [`classification.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-step0-forensics/classification.md)

---

## 1. Overview and Incident Context
During preparation for baseline evaluation, inspection of the primary working tree `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-0.1.0` revealed extensive uncommitted and uncoordinated modifications. Multiple autonomous agent sessions had concurrently operated in the same working tree, interleaving independent code streams into shared files.

A full forensic capture was executed, saving raw diffs, patches, file inventories, and status logs into `arpipe-step0-forensics`.

---

## 2. Tracked File Contamination
13 tracked production files contained uncommitted changes mixing multiple independent initiatives:

| File | Initiative Markers Found in Diff | Observed Impact |
|---|---|---|
| `arpipe/cli.py` | `P-B5`, `PM1` | Two unrelated streams interleaved in CLI arguments |
| `arpipe/configs/default.yaml` | `P34` | Threshold additions matching `verify.py` |
| `arpipe/models.py` | `P-B2`, `P34`, `P5`, `P6` | New enum members and dataclass fields |
| `arpipe/ocr.py` | `P-B5` | OCR routing and bake-off additions |
| `arpipe/pipeline.py` | `P-B5`, `P18`, `P34`, `PM1` | Four independent streams interleaved |
| `arpipe/segment.py` | `P-B1`, `P-B2`, `P-B4` | Three streams interleaved |
| `arpipe/store.py` | `P18`, `P34` | Store modifications for state tracking |
| `arpipe/tests/test_pipeline.py` | `P34` | Appended test fixtures |
| `arpipe/textlayer.py` | `PM1` | Added full-width block detection helper |
| `arpipe/triage.py` | Unmarked | Triage adjustments |
| `arpipe/verify.py` | `P18`, `P21`, `P22`, `P34`, `PM1` | Five streams interleaved (+418 line diff) |
| `configs/eval_protocol.md` | `P-X2`, `P-X4`, `P11`, `P25`, `P27` | Full-file rewrite (131 $\rightarrow$ 925 lines) |
| `reports/pattern_audit.md` | `P25`, `P26`, `P27`, `P28` | **CORRUPTED**: Concurrent writers inserted duplicate rows out of order, asserting contradictory metrics |

---

## 3. Core Module Reversion: `arpipe/patterns.py`
`arpipe/patterns.py` had an uncommitted modification (Case B) affecting heading detection patterns. This change was verified, isolated, and cleanly reverted back to match HEAD `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14`. The module has remained 100% bitwise clean across all subsequent tasks.

---

## 4. Forensic Verdict & Lessons
- **Classification:** `E — UNKNOWN / CANNOT SAFELY CLASSIFY`. Baseline source versions for several modified files (`cli.py`, `pipeline.py`, `verify.py`) were never committed as Git objects and could not be recovered.
- **Root Cause:** Concurrency violation. Shared working tree access without session-level isolation.
- **Architectural Remedy:** Established mandatory rule: **ONE SESSION = ONE WORKTREE = ONE TASK**.

