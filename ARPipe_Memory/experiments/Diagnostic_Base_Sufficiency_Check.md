# Diagnostic Base Sufficiency Check

**Status:** HISTORICALLY ESTABLISHED  
**Mode:** READ-ONLY DIAGNOSTIC GATE  
**Worktree:** `D:\sem_iitk\sem9\thesis\sep_week1\arpipe-pc0-diagnostic-base`  
**Base Commit:** `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14`  
**Verdict:** `DIAGNOSTIC BASE SUFFICIENT — P-C0 MAY START`  
**Primary Artifact:** [`reports/pc0_diagnostic_base_check.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-pc0-diagnostic-base/reports/pc0_diagnostic_base_check.md)

---

## 1. Objective and Provenance Gate
Evaluated whether clean committed HEAD `0fb8cbf6d932f4190bdfe3b2a1fecf62170cca14` plus the already-frozen P-M5 evidence in `arpipe-pm5-coverage` (branch `pm5-coverage-funnel` @ `7292111`) are sufficient to diagnose the 22.05% coverage problem (P-C0) without modifying or reconstructing `arpipe-0.1.0`.

### Recomputed SHA-256 Hashes of Frozen P-M5 Evidence
All evidence hashes were verified independently and matched the embedded values in `coverage.json`:
- `reports/coverage.json`: `c84166741d36a9774b7c9f29d71ea9583934d98c2ab153e651ec66ec4d371bcf`
- `reports/pm5_stage_table.csv`: `30e93b59ac689f00fab182583fb25883322e429be42b4ba14e13a1011b916dc9`
- `reports/pm5_expected_universe_snapshot.csv`: `b287a82d0fa2b15098882c328be6afc2c1672c9255f64103e4aaeabd94ccebe5`
- `reports/pm5_source_snapshots/cohort_reports.jsonl`: `c24f148ae5971dca545168921caa207aa6cfd84021958fcf969bd812a4a04b67`
- `reports/pm5_source_snapshots/live_store_documents.jsonl`: `3a7c7bf15f554298e1c7f4a62b90ea6328a9e1e1e4ecde4840aee7ce42abab31`
- `reports/pm5_source_snapshots/live_dataset_manifest.jsonl`: `8607cd29d9e660fee1b18ce9d980e0a39c217275201d72114e4ce0a9fe89a625`

---

## 2. Fiscal-Year Pattern Analysis
Audited all 16 fiscal years (FY2010–2025) from `pm5_stage_table.csv`:
- **Zero-Coverage FYs (10):** 2010, 2011, 2014, 2015, 2016, 2019, 2020, 2021, 2022, 2023.
- **Non-Zero Coverage FYs (6):** 2012, 2013, 2017, 2018, 2024, 2025.
- **Clustering:** Three tight 2-year non-zero clusters (`{2012,2013}`, `{2017,2018}`, `{2024,2025}`) separated by multi-year zero runs.
- **Timestamp Clustering:** All 194 successful downloads occurred within a single ~4.5-minute window on 2026-09-11 (10:28:44–10:33:08 UTC).

---

## 3. Raw HTTP Probes (2026-09-17 @ ~13:17 UTC)
A 10-observation diagnostic sample (5 zero-coverage + 5 non-zero control) was tested via `curl`:
- **9 URLs on `nsearchives.nseindia.com`:** 100% failed (mix of `CURLE_RECV_ERROR 56` connection resets and 45s timeouts). Failures were uniform across both zero-coverage and non-zero control groups.
- **1 URL on `www.bseindia.com` (Infosys FY2011):** Succeeded cleanly (`HTTP/1.1 200 OK`, 5,698,015 bytes, valid PDF).

---

## 4. Sufficiency Determination
All four gate criteria were met:
1. Frozen P-M5 evidence is consumable directly without worktree reconstruction.
2. 10 diagnostic observations were cleanly selectable from frozen data.
3. Committed HEAD has sufficient fetch and invocation logic to support direct comparison.
4. No dirty-tree changes from `arpipe-0.1.0` were required.

**Verdict:** `DIAGNOSTIC BASE SUFFICIENT — P-C0 MAY START`.

