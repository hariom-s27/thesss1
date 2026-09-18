# ARPipe — Evidence Artifact Index

This index provides direct paths and verified SHA-256 digests for all primary evidence files across the project. When any memory summary conflicts with a frozen artifact, the frozen artifact is the sole source of truth.

---

## 1. Acquisition & Coverage Evidence (P-M5 / P-C0 / P-C0R / R1)

| Evidence Role | File Path | SHA-256 Digest |
|---|---|---|
| P-M5 Headline Coverage | `arpipe-pm5-coverage/reports/coverage.json` | `c84166741d36a9774b7c9f29d71ea9583934d98c2ab153e651ec66ec4d371bcf` |
| P-M5 Stage Transition Table | `arpipe-pm5-coverage/reports/pm5_stage_table.csv` | `30e93b59ac689f00fab182583fb25883322e429be42b4ba14e13a1011b916dc9` |
| P-M5 Expected Universe | `arpipe-pm5-coverage/reports/pm5_expected_universe_snapshot.csv` | `b287a82d0fa2b15098882c328be6afc2c1672c9255f64103e4aaeabd94ccebe5` |
| P-M5 Reason Code Completeness | `arpipe-pm5-coverage/reports/pm5_reason_code_completeness.csv` | `0adb7410a857435e8a859d30c7ede67e7fa4beb4a4f8c7abda76eb43a246684c` |
| P-M5 Discovered Cohort Snapshot | `arpipe-pm5-coverage/reports/pm5_source_snapshots/cohort_reports.jsonl` | `c24f148ae5971dca545168921caa207aa6cfd84021958fcf969bd812a4a04b67` |
| P-M5 Live Store Snapshot | `arpipe-pm5-coverage/reports/pm5_source_snapshots/live_store_documents.jsonl` | `3a7c7bf15f554298e1c7f4a62b90ea6328a9e1e1e4ecde4840aee7ce42abab31` |
| Diagnostic Base Gate Report | `arpipe-pc0-diagnostic-base/reports/pc0_diagnostic_base_check.md` | `53968bf73621bc08ed754336437f12e39723ab7a01b47f887b2596fb9a9d46c7` |
| P-C0 Frozen Sample Manifest | `arpipe-pc0-coverage-diag/reports/pc0_sample_manifest.json` | `4b971a8069d3eeb1ec3528bca617c5fb54cf69076fa4d5d9cfa3a681c81ef9d2` |
| P-C0R Frozen Request Config | `arpipe-pc0r-acquisition-pilot/reports/pc0r_request_configuration.json` | `06b1add2a4676b5eca09cf49e891481e52e1a47ae8f1cb4c6bf9d35fdb6481cd` |
| P-C0R Repeated Arm Log | `arpipe-pc0r-acquisition-pilot/reports/pc0r_attempt_log.csv` | `af8ea0c881595a9322fe32293608b305737776a1585d39246dff401f1cb83397` |
| P-C0R Client Comparison Log | `arpipe-pc0r-acquisition-pilot/reports/pc0r_client_comparison.csv` | `3f2d5a6f9a10fd49b2eed63d1c1eefdf73e2cc79c8d3db02f83ca4b82d9ba88c` |
| R1 Diagnostic Report | `arpipe-r1-fetch-telemetry/reports/r1_fetch_telemetry.md` | `edf26f03a433e1e344c956195c1cab605b519dc3aec62a4e142a0dbbf48a895c` |
| R1 Machine-Readable Summary | `arpipe-r1-fetch-telemetry/reports/r1_fetch_telemetry.json` | `10310bd9cce4f55b198a7e6f5777e7c86d3ecce029f068003e750623fc6d26ab` |
| R1 Raw Failure Telemetry | `arpipe-r1-fetch-telemetry/reports/r1_telemetry/r1_matrix_telemetry.jsonl` | `466dca2953cea16b698fe81dec2ef852634c4b6e5a476acb831033b941a90631` |
| R1 Generation Summary | `arpipe-r1-fetch-telemetry/reports/r1_telemetry/r1_generation_summary.json` | `92e2dc8e4a82eec021dd1c91684b9b04ab51a42367cf5a6099a8e200135dce05` |

---

## 2. Extraction & Quality Evidence (P-B3 / P-B4 / PM1 / PM2.1 / PM2.2 / PM3 / PM4)

| Evidence Role | File Path | Scope |
|---|---|---|
| P-B3 Legacy Font Audit | `arpipe-0.1.0/reports/legacy_font_corpus_measurement.md` | 37,917 pages, 2×2 matrix |
| P-B4 Script Telemetry Validation | `arpipe-0.1.0/reports/pb4_corpus_validation.json` | 194 documents, 0 behavioral drift |
| P-M1 Order QC Diagnostic | `arpipe-0.1.0/reports/pm1_per_page_orphan.md` | 84/194 hidden bad pages |
| P-M2.1 Page-Grain Orphan Scores | `arpipe-pm2.1-pagegrain/reports/pm2_pagegrain_native_vs_ocr.md` | 2,547 measured pages |
| P-M2.2 Threshold Sensitivity | `arpipe-pm2.2-sensitivity/reports/pm2_2_threshold_study.md` | Grid `[0.020, 0.060]`, `.040` exploratory |
| P-M3 Scan Quality Audit | `arpipe-pm3-scan-quality/reports/pm3_scan_quality.md` | 2,909 full-raster pages |
| P-M4 Annexure Heading Audit | `arpipe-pm4-annexure-audit/reports/annexure_audit.md` | 18 eligible fit documents |
