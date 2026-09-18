# Protocol 01 — Worktree Safety & Concurrency Isolation

**Status:** ACTIVE MANDATORY PROTOCOL  
**Enforcement:** ALL TASKS AND SESSIONS

---

## 1. The Core Law
> **ONE SESSION = ONE WORKTREE = ONE TASK.**

Never share an active working tree between concurrent agent sessions or human developers. Every task must be conducted in its own dedicated, isolated Git worktree.

---

## 2. Protected Forensics: `arpipe-0.1.0` is Read-Only
1. `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-0.1.0` is permanently declared **READ-ONLY FORENSIC EVIDENCE**.
2. **Forbidden Actions:** Never run `git checkout`, `git commit`, `git merge`, `git pull`, file editing, or file deletion inside `arpipe-0.1.0`.
3. Read access to `arpipe-0.1.0` is permitted strictly for read-only forensic inspection or when creating a new detached/branched worktree via `git worktree add`.

---

## 3. Worktree Lifecycle Procedure

### Phase A: Pre-Execution Registration
Before creating or touching files:
1. Verify the canonical base commit SHA (`0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14`).
2. Create an isolated worktree via `git worktree add <path> -b <branch> <base-sha>`.
3. Pre-register the task, model, worktree path, starting SHA, and boundaries in `04_WORKTREE_REGISTER.md`.

### Phase B: Execution Guardrails
During active work:
1. Confine all modifications strictly to the designated worktree.
2. Never touch files in sibling worktrees (`arpipe-pm5-coverage`, `arpipe-pc0-coverage-diag`, `arpipe-pc0r-acquisition-pilot`, etc.).
3. If an automated monitor or filesystem check detects an unexpected external modification to `.git` or tracked files, **HALT IMMEDIATELY** and record a mandatory stop receipt (as established in Step 0A/0B).

### Phase C: Post-Execution Verification
After completing the task:
1. Verify test pass rates, regression status, and behavioral equivalence.
2. Record all changed files and commit hashes.
3. Compute and record SHA-256 hashes of all generated reports and data artifacts.
4. Update `00_MASTER_LOG.md`, `01_CURRENT_STATE.md`, `03_EVIDENCE_REGISTER.md`, and `04_WORKTREE_REGISTER.md`.

