# ARPipe — Worktree Register

This register catalogues all Git worktrees, forensic directories, and experiment workspaces in the ARPipe repository structure. All paths and commit SHAs have been directly verified against Git metadata and filesystem state.

---

## Permanent Worktree Rules
1. **ONE SESSION = ONE WORKTREE = ONE TASK.**
2. **Never modify `arpipe-0.1.0`** (Permanent read-only forensic source tree).
3. **Never touch an existing completed experiment worktree.**
4. **The next engineering task must use a NEW dedicated worktree based on the verified final R1 commit (`56497721cb68c4831e6f225074b6bd7ea17bffb0`).** Do not reuse the frozen R1 worktree. Do not invent the new worktree path before it is created.

---

## Registered Worktrees and Workspaces

| Worktree / Directory Path | Branch Name | Base / Current SHA | Task / Role | Operational Status | Access Mode | Safety Restrictions |
|:---|:---|:---|:---|:---|:---|:---|
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-fetch-telemetry` | `r1-fetch-telemetry` | Base: `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14`<br>Final: `56497721cb68c4831e6f225074b6bd7ea17bffb0` | R1: Failure telemetry-only repair (implementation) | **FROZEN / READ-ONLY** | **READ-ONLY** (Frozen Milestone) | **STRICTLY FROZEN / READ-ONLY**. Milestone frozen in commit `56497721cb68c4831e6f225074b6bd7ea17bffb0`. Never edit, commit, rerun tests, or reuse for subsequent tasks. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-r1-telemetry-analysis` | `r1-telemetry-analysis` | Base: `56497721cb68c4831e6f225074b6bd7ea17bffb0`<br>Final: `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870` | R1: Telemetry analysis & P-R1X protocol design | **COMPLETED ANALYSIS / READ-ONLY** | **READ-ONLY** (Frozen Analysis) | **STRICTLY READ-ONLY**. Analysis committed in `3beee249db36f9fdd1a8a2e01d6fdc3c6024d870`. Never edit, commit, or reuse for engineering tasks. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-0.1.0` | `main` | `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | Primary historical repository root | **DIRTY** (13 modified tracked files, ~45 untracked) | **READ-ONLY** (Forensic) | **STRICTLY READ-ONLY**. Never run git checkout, edit, commit, or merge. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pc0r-acquisition-pilot` | `pc0r-acquisition-pilot` | `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | P-C0R: Acquisition resolution pilot | **COMPLETED** (No reproducible failure; 50/50 success) | **READ-ONLY** | Completed diagnostic. Do not modify or rerun. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pc0-coverage-diag` | *detached* | `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | P-C0: Coverage problem diagnosis | **COMPLETED** (Mechanism partially identified) | **READ-ONLY** | Completed diagnostic. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pc0-diagnostic-base` | *detached* | `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | Diagnostic base sufficiency gate | **COMPLETED** (Base sufficient; P-C0 cleared) | **READ-ONLY** | Completed gate. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pm5-coverage` | `pm5-coverage-funnel` | `7292111149ab1cf9fc8d638d1f08023e3fcb13d5` | P-M5: Coverage funnel snapshot | **COMPLETED / FROZEN** (318 losses recorded) | **READ-ONLY** (Frozen Evidence) | Frozen evidence store. Hashes pinned. Do not modify or rerun. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pm4-annexure-audit` | `pm4-annexure-audit` | Base: `158a9eac...`<br>HEAD: `e387d6b8879d25af7b6d6946e28aaa635cb97165` | P-M4: Annexure heading form audit | **COMPLETED** (18 eligible fit docs audited) | **READ-ONLY** | Completed audit. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pm3-scan-quality` | `pm3-scan-quality` | `ec48e6454e278c789268519fe1f63d18374cd6b4` | P-M3: Physical scan quality audit | **COMPLETED** (37,917 pages evaluated) | **READ-ONLY** | Completed audit. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pm2.2-sensitivity` | `pm2.2-threshold-sensitivity` | Base: `158a9eac...`<br>HEAD: `6d91dfa8e8db4c9d570ba98dd234a228e4d3c57a` | P-M2.2: Threshold sensitivity study | **COMPLETED** (`0.03` preserved; `0.040` exploratory) | **READ-ONLY** | Completed study. Do not recalibrate production thresholds. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pm2.1-pagegrain` | `pm2.1-pagegrain-native-vs-ocr` | `158a9eac48a3374a9506af8281acb93f49a37a0d` | P-M2.1: Native vs OCR at true page grain | **COMPLETED** (2,547 pages measured) | **READ-ONLY** | Completed diagnostic. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pm2-native-vs-ocr` | `pm2-native-vs-ocr-orphan` | `f53f9cdbd5fe74ad8fa42713f73fe0ccd7c100a9` | P-M2: Native vs OCR initial study | **COMPLETED** (Superseded by P-M2.1) | **READ-ONLY** | Superseded study. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pb2-p1-recovery` | `pb2-p1-recovery` | Base: `0fb8cbf...`<br>HEAD: `16dfcf42a009105e30e4035327b1a801a04bd460` | P-B2 Phase 1 provenance recovery | **HALTED** (Partially recovered; Phase 2R blocked) | **READ-ONLY** | Recovery halted. Missing Git objects. Do not proceed with Phase 2R. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-step0-forensics` | *N/A (audit dir)* | Target: `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | Step 0: Dirty-file classification | **COMPLETED** (13 modified files audited) | **READ-ONLY** | Preserved forensic evidence. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-step0a-candidate` | `step0a-baseline` | `0d39395dfb81c987e05546471fbb80947c8fdce8` | Step 0A provisional candidate | **HALTED / PROVISIONAL** (Never accepted as canonical) | **READ-ONLY** | DO NOT USE AS BASELINE. Halted on FETCH_HEAD alert. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-step0a-recovery` | *N/A (recovery dir)* | Target: `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | Step 0A candidate recovery | **HALTED** (Mandatory stop receipt recorded) | **READ-ONLY** | Halted. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-step0b-recovery` | *N/A (recovery dir)* | Target: `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` | Step 0B blocker quantification | **HALTED** (Mandatory stop receipt recorded) | **READ-ONLY** | Halted. Do not modify. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-execution` | `pr1x-execution` | Base: `56497721cb68c4831e6f225074b6bd7ea17bffb0`<br>Final: `0b1d595407eacb13b115811cdb610b3e1f56a767` | P-R1X: Instrumented acquisition telemetry pilot (execution) | **COMPLETED PILOT / READ-ONLY** | **READ-ONLY** | **STRICTLY READ-ONLY**. Completed pilot execution. Preserved untouched. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-adjudication` | `pr1x-adjudication` | Base: `0b1d595407eacb13b115811cdb610b3e1f56a767`<br>Final: `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32` | P-R1X: Forensic adjudication & protocol compliance audit | **COMPLETED ADJUDICATION / READ-ONLY** | **READ-ONLY** | **STRICTLY READ-ONLY**. Contains 5 committed adjudication reports and hash manifests. |
| `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pr1x-historical-audit` | `pr1x-historical-audit` | Base: `ca92b8e8d043cccb9556a6fc591927b3bbf1cf32`<br>Final: `1b6fd1f496b3634ee57bef6b926f7a79524c1cac` | Historical Acquisition-Cause Evidence Audit | **COMPLETED AUDIT / READ-ONLY** | **READ-ONLY** | **STRICTLY READ-ONLY**. Contains 8 committed audit reports and cryptographic manifests. |

---

## Next Task: Task 2 — Evidence-Driven Acquisition Strategy
- **Target Task:** **Task 2: Evidence-Driven Acquisition Strategy**
- **Operational Mode:** **INFORMATION-GAP / OBSERVABILITY TASK** (Deploy structured R1 telemetry across the 318 un-downloaded cohort).
- **Reference Commits:**
  - Engineering Base: `56497721cb68c4831e6f225074b6bd7ea17bffb0`
  - Historical Audit Baseline: `1b6fd1f496b3634ee57bef6b926f7a79524c1cac`
- **Rule:** Any future engineering task requiring code execution must provision a NEW dedicated worktree. Existing completed worktrees remain strictly read-only.

---

## Inactive / Unregistered Worktree Paths
- Any path outside `D:\sem_iitk\sem9\thesis\sep_week1` is not an active ARPipe worktree.
- Root repository `D:\sem_iitk\sem9\thesis` (branch `main`) houses thesis scripts and documentation, and must never be used for ARPipe pipeline execution.

