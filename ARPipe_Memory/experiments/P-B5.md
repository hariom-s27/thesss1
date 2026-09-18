# P-B5 — OCR Bake-off on Legacy Font Stratum

**Status:** HISTORICALLY ESTABLISHED  
**Primary Reports:** [`reports/ocr_bakeoff/results_summary.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-0.1.0/reports/ocr_bakeoff/results_summary.md), [`legacy_font_comparison.md`](file:///D:/sem_iitk/sem9/thesis/sep_week1/arpipe-0.1.0/reports/ocr_bakeoff/legacy_font_comparison.md)  
**Sample Population:** `ocr_bakeoff_population.csv`, `ocr_bakeoff_development.csv`, `ocr_bakeoff_holdout.csv`

---

## 1. Experimental Question
Does rasterize-and-OCR recover useful text when the native PDF text layer contains legacy-font Devanagari encoded as Latin codepoints, and how do different OCR engines compare across CER, WER, and heading recognition?

---

## 2. Engines Evaluated
- `native_pdf` (PyMuPDF native extraction baseline)
- `tesseract` (Standard open-source OCR)
- `paddleocr_vl` (Multilingual visual layout OCR)
- `surya_2` (Document OCR engine)
- `gemini_flash_lite` (VLM multimodal OCR)

---

## 3. Scope & Operational Status
- **Status:** Scored per engine and stratum on development sample pages (`INE002E01010_2025_05da4154:p103`, `INE797F01020_2025_0931a7ab:p163`, `INE171A01029_2017_0eff7ba8:p71`).
- **Production Impact:** ZERO production engine changes or threshold recalibrations were made.
- **Reference Dependencies:** Formal WER/CER scoring against gold transcription remained pending reference completion. No engine was crowned production winner.

