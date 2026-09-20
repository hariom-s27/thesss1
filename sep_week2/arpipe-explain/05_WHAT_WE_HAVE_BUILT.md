# 05 — What We Have Actually Built (Honest Status)

Date: 12 September 2026.

---

## Works, verified end to end

| Stage | Evidence |
|---|---|
| `universe` | 2,568 companies pulled from live NSE masters; symbol-change chaining works |
| `discover` | 12 candidate URLs for 2 companies from NSE + screener |
| `fetch` | 4/4 PDFs downloaded; SHA-256 dedup confirmed (`nlink` > 1); polite rate limiting; ZIP unwrap |
| `triage` | 1,275 pages profiled; 3 digital + 1 mixed; 5.1% flagged for OCR; pure object-model read, fast |
| `extract` (digital) | 4/4 reports → `mda.txt` + `mda.json`, all graded high; 5.2k–15.2k words each |
| `audit` | manifest summarisation works |
| tests | **170 passing** |

Real output exists: ~39k words of MD&A with full provenance.

The **digital happy path is solid.** That is the majority of post-2016 documents.

---

## Built but never run

### OCR (the big one)

`tesseract`, `qpdf`, Ghostscript and the Hindi language pack are **not installed
on the dev machine**. Consequences:

- Any fully scanned report → `mda_not_located`, total loss
- Any hybrid report where MD&A falls in a scanned band → 0 words, quarantined
- Four separate code paths (index-sample OCR, refine-end OCR, full-span OCR,
  front-matter fallback) are unreachable and untested
- Bilingual Hindi+English PSU reports have no path at all

Worse: when Tesseract is missing, `ocr.Escalator.run_page` **swallows the error
and returns an empty page.** So the failure is silent at the OCR layer and only
shows up later as "not located". The triage forecast of "5.1% of pages need OCR"
is currently 5.1% of nothing.

**This is the single largest untested surface in the project**, and it is exactly
the surface that covers FY2010–2015 — the years that make this a 16-year study
rather than a 10-year one.

### BSE discovery

Every row in `companies.csv` has an empty `bse_scrip` (2,571 of 2,571). It's only
populated from `universe --bse-json <file>`, which nothing supplies. So
`discover_bse` returns `[]` immediately. Net effect: **~3,000 BSE-only companies
are unreachable**, and NSE-listed companies have no fallback when NSE is missing
a year.

### LLM adjudication

`segment.from_llm` exists and accepts an injected `call_llm`, but the CLI never
builds one — it's always `call_llm=None`. There's no provider client and no
`--llm` flag. Dead code from the CLI's point of view.

### Table extraction

No `tables.py`. Tables are flagged and can down-grade confidence, but there's no
Camelot / gmft / TATR routing. Embedded data tables get flattened into the text.

### Cloud OCR rung

`boto3` absent, `TextractBackend` untested. (And Textract has no Devanagari
anyway — never route Hindi there.)

---

## Config not wired up

`configs/default.yaml` exists. Nothing reads it. `grep` finds zero references to
any YAML loader; `pyyaml` isn't installed. Every threshold is hard-coded in the
modules:

```
triage.py    120 char/page, 0.55 image area, 0.02 mojibake
ocr.py       40 words, 0.72 confidence
segment.py   0.55 / 0.70 score gates, 60-page cap
verify.py    88 / 72 name match, 0.03 orphan_start_frac
```

These were all hand-set and are supposed to be re-fitted against ~300 labelled
filings. **That labelling is the current bottleneck.**

---

## The evaluation situation — the important part

This changed dramatically in the last two days. Before:

```
Exact start accuracy   90.0%    <- meaningless, see file 06
IoU                    0.8267   <- meaningless
ok rate                71.6%    <- not accuracy at all
```

After removing the self-referential scoring (P31):

```
Documents evaluated              6
Exact start accuracy         83.3%
Start within 1 page          83.3%
Boundary IoU                0.8333
Order scrambled               0.0%
```

**Six documents.** That is the honest denominator. The number went *down* and the
sample went from 194 to 6 — and that is a good outcome, because the new number is
real and the old one wasn't.

Current labelling state:

```
labels.csv                20 rows    (6 read_pdf, 12 unknown, 2 copied_from_run)
labels_fit.csv            20 rows    (2 marked contaminated)
labels_holdout.csv         0 rows    (nothing labelled yet)
labels_fit_queue.csv      92 waiting
labels_holdout_queue.csv  45 waiting
```

---

## One-line summary

> Digital extraction works and is now honestly measured on a very small sample.
> OCR has never run. BSE is unreachable. The next real milestone is 300 hand
> labels, not more code.
