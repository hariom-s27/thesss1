# 10 — What To Do Next, In Order

The ordered list. Nothing here is optional, and the order matters.

---

## Right now

**Leave the discovery crawl running.** Network-only, produces no spans, output
needed regardless. It blocks nothing.

**Do not run `fetch` on the full universe.** Blocked by disk (81 GB vs ~1 TB) and
by the fact that thresholds are uncalibrated. Both get fixed below.

---

## Step 1 — Decide the storage policy (1 hour, do before anything downloads)

Pick one, from file 09:

- **Recommended:** extract → keep MD&A span pages + full provenance + SHA-256 +
  source URL → **discard the source PDF**. Re-fetchable on demand, ~50 GB instead
  of ~1 TB.
- Alternative: external 1 TB drive, keep everything.

Make this decision *before* the crawl. Changing it halfway gives you two
incompatible stores.

---

## Step 2 — Install and test the OCR path (half a day)

```
tesseract + tesseract-ocr-hin
qpdf
ghostscript / pdftoppm
```

Then run end-to-end on `C_scanned.pdf`, `D_hybrid.pdf`, `E_bilingual.pdf`.

**Also add a loud startup check.** Right now a missing Tesseract silently returns
empty pages, which looks like "this document has no MD&A" hours later. If OCR is
needed and the binary is absent, fail immediately with a clear message.

This unblocks FY2010–2015 — roughly a third of the study period.

---

## Step 3 — Label 300 documents (the bottleneck — days, not hours)

Current state:

```
labels_fit.csv            20 done      (2 contaminated)
labels_fit_queue.csv      92 waiting
labels_holdout_queue.csv  45 waiting
```

You need ~200 in fit and ~100 in holdout. That's ~280 more.

**Rules while labelling:**

- Label from `labels_fit_queue.csv` **first**. Leave the holdout queue alone.
- Set `verified_by = read_pdf` only if you actually opened the PDF and read the
  pages. Never guess upward.
- If a fix gets written against a document, mark it `contaminated = true` and it
  stays in fit permanently.
- **Never open a holdout document to find out why it failed.** That converts it
  into a fit document.

This is boring and it is the single highest-value work left. Every number in the
thesis rests on it.

**A practical suggestion:** label in stratified batches of ~25 (mix of eras and
doc kinds) rather than 300 in a row. After each batch, re-run `arpipe evaluate
--split fit` and watch whether accuracy is stable. If batch 4 suddenly drops, you
have found a document class the pipeline doesn't handle — which is useful *now*,
not after 300.

---

## Step 4 — Fit thresholds on the fit set only

The hard-coded constants (file 05) get re-fitted:

```
triage.py    120 char/page, 0.55 image area, 0.02 mojibake
ocr.py       40 words, 0.72 confidence
segment.py   0.55 / 0.70 score gates, 60-page cap
verify.py    88 / 72 name match
```

And wire `configs/default.yaml` up so they stop being hard-coded. `pyyaml` isn't
even installed yet.

**Do not touch `ORPHAN_START_FRAC_MAX = 0.03`** unless the 300-document
distribution genuinely says it's in the wrong place. It currently sits in empty
space with ~8× headroom, and it is the one honest metric you have.

---

## Step 5 — Score the holdout ONCE

```
arpipe evaluate --split holdout
```

Record the number. Write it in the thesis. **Do not tune anything afterwards.**

If it's bad, that is a finding, not a failure — it tells you the fit set wasn't
representative, which is itself worth reporting.

`eval_holdout_log.csv` records every holdout scoring with date and git commit.
Keep that count low. A holdout scored 20 times is a training set.

---

## Step 6 — Re-run P33 as a regression check

Every time a rule changes, re-run the per-rule fire-count sweep and diff against
the previous run. A rule whose fire count jumps from 12 to 900 has silently
changed meaning.

Make this a standing job, not a one-off. It is the only thing that catches
rule-interaction bugs (file 07).

---

## Step 7 — Staged crawl

From file 09 — do **not** jump straight to the full universe:

| Stage | N | Gate to pass before proceeding |
|---|---|---|
| B | 1,000 | Failure taxonomy stable; no new failure class in the last 200 |
| C | 10,000 | `orphan_start_frac` distribution unchanged vs Stage B |
| D | 78,000 | Nothing new in C |

---

## Step 8 — Connect the two halves

This is the step that makes it a thesis rather than two repos.

Feed the extracted MD&A corpus into the `thesis` repo's CCExposure scorer. Then
run, on Indian MD&A text, the same validation battery that repo already
implements on US transcripts:

- **Placebo test** — score documents that should have no climate signal
- **Split-half reliability** — does the measure agree with itself on half the data?
- **Permutation test** — scramble word order; the score must drop
- **Bootstrap CIs**, firm-clustered

**The permutation test matters doubly here.** Scrambled columns (file 02,
problem 4) produce text that is *already* word-order-scrambled. If your corpus
has scrambled documents in it, the permutation test's null and your real data
converge — and the test loses power. So `orphan_start_frac` is not just a text
quality metric; it is a precondition for the inference in the second half of the
thesis being valid.

That connection is worth stating explicitly in the methodology. It's the
strongest justification you have for why so much effort went into reading order.

---

## The one-page summary

```
NOW      leave discovery running; don't fetch
STEP 1   decide storage policy          (1 hour)
STEP 2   install + test OCR             (half day)
STEP 3   label 300 documents            (DAYS - the bottleneck)
STEP 4   fit thresholds on fit set      (1 day)
STEP 5   score holdout ONCE             (1 hour)
STEP 6   P33 sweep as regression check  (standing)
STEP 7   crawl 1k -> 10k -> 78k         (weeks)
STEP 8   feed corpus to CCExposure      (the thesis)
```

Steps 1, 2, 4, 5 are hours. Step 3 is days and cannot be skipped or automated —
it is what converts this from "a pipeline that runs" into "a pipeline with a
defensible number attached to it."
