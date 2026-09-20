# 08 — Every Big Choice, And The Options We Rejected

For each decision: what we do, what else we could have done, and why.
This is the file you'll want when a supervisor asks *"why did you do it that way?"*

---

## 1. Locate MD&A first, then OCR — vs OCR everything

**We do:** find the span on free text / cheap signals, then OCR only those pages.

| Option | Cost for 78,000 docs | Verdict |
|---|---|---|
| OCR every page first, then search | 319 pages × 78,000 = ~25M pages | Rejected |
| **Locate first, OCR span only** | 13.5 pages × 78,000 = ~1M pages | **Chosen** |

**25× less OCR.** At Google DocAI prices (~$1,500/M pages) that's ~$37,500 vs
~$1,500. At self-hosted PaddleOCR (~$190/M) it's ~$4,750 vs ~$190.

**Cost of the choice:** you must locate the span *without* being able to read
scanned pages. That's why there are five strategies and an index-page sampler,
instead of one simple text search. The complexity in `segment.py` is the price
paid for this decision — and it's worth it.

---

## 2. Page-level triage — vs document-level

**We do:** classify every page individually.

**Why:** a 319-page report is routinely 300 digital pages plus 19 scanned
inserts. Document-level classification is wrong either way:
- Call it "scanned" → OCR 319 pages for no reason
- Call it "digital" → silently lose the 19 inserts (which are often the
  signed/scanned annexures — exactly where MD&A sometimes lives)

**Cost:** more metadata per document. Trivial. This was an easy call.

---

## 3. Five strategies + arbiter — vs one good method

**Rejected:** pick the best method, tune it hard.

**Why rejected:** with one method you get an answer and no confidence. You
cannot tell a right answer from a wrong one. With five independent methods,
**agreement itself is the confidence measure** (`supporters`).

**Vindicated in practice:** file 07 shows S5 body cues silently rescuing 6
documents when S3 headings were wrongly suppressed. A single-strategy pipeline
would have produced 8 wrong spans instead of 2, and reported no problem.

**Cost:** five times the code, five times the rules, five times the surface for
rules to interact badly. That cost is real — P33 exists because of it.

---

## 4. OCR ladder — vs one OCR engine

**We do:** three rungs, cheapest first, escalate only on bad quality.

| Rung | Engine | Cost/M pages | Devanagari? | Notes |
|---|---|---|---|---|
| 1 | Tesseract (local) | ~free | yes (`hin`) | Good on clean scans |
| 2 | PaddleOCR-VL (self-hosted) | ~$190 | yes | Good on hard layouts |
| 3 | Google DocAI / Gemini | ~$1,500 | yes | Last resort |
| — | AWS Textract | ~$12,000 | **NO** | **Rejected entirely** |

**Textract rejected for two independent reasons:** no Devanagari support (which
kills every bilingual PSU report), and ~8× the cost of DocAI.

**The escalation gate:** a page escalates if word count <40 or mean confidence
<0.72. Plus a **degeneracy guard** — reject output if it's >6× the anchor text
length, or has 8+ identical consecutive lines. That guard catches the classic
OCR failure where an engine hallucinates a repeating loop.

---

## 5. Gutter threshold 2.5% — vs the academic 5%

**We do:** 2.5% of page width, measured on **line** boxes.

**Why not 5%:** that default comes from academic-paper layout research (US
Letter, wide margins). Indian annual reports use an 18–30pt gutter on a 595pt
A4 page — that's 3–5%, so a 5% threshold misses many real two-column pages and
reads straight across, producing scrambled text.

**Why line boxes not block boxes:** block boxes often span both columns, which
hides the gutter entirely. This is a subtle one and it took a real diagnostic to
find.

**Related war story:** the original column bug was diagnosed *wrongly* first. The
early hypothesis was "the threshold is 5%, it should be 2.5%". It turned out the
threshold was already 2.5%. The real cause was a full-width running footer
collapsing `_gap_cut`'s widest interval to 0.0. The `CLAUDE.md` was rewritten
with the confirmed cause, because a rules file that gets read every session with
a wrong root cause in it is worse than no rules file at all.

---

## 6. `orphan_start_frac` — vs word count / ROUGE / eyeballing

**We do:** measure the fraction of paragraphs that begin mid-sentence.

**Rejected alternatives:**

| Option | Why rejected |
|---|---|
| Word count | Scrambled text has a perfectly normal word count. Sees nothing. |
| Manual reading | Doesn't scale past ~20 documents |
| ROUGE vs a reference | No reference text exists for Indian MD&A |

**The FinCriticalED finding backs this up:** a system scored **95.71 ROUGE-1**
while getting **54.05%** of monetary units wrong. Text-similarity metrics do not
measure whether the text is *correct*. They measure whether it looks similar.

`orphan_start_frac` is cheap, label-free, and — as file 06 explains — the only
metric in the project that was never circular.

---

## 7. Quarantine tables — vs keeping them inline

**We do:** push tables and chart labels into a separate `mda_blocks.json`.

**Why:** a flattened financial table produces text like
`Revenue 4,521 3,908 15.7 Margin 12.4 11.8`. For a bigram-counting climate
measure, that's pure noise — and worse, it inflates the denominator, which
*deflates* every CCExposure score by a variable amount depending on how
table-heavy the report is. That's a systematic bias correlated with company size.

**Cost:** you lose any climate information inside tables. Accepted — climate
discussion is prose.

---

## 8. Hold-out protocol — vs fitting on everything

**We do:** 2/3 fit, 1/3 holdout, stratified, seed recorded, holdout inspections
logged.

**Rejected:** fit thresholds on all labelled data and report the same number.

**Why rejected:** that's what produced the 90% in file 06. With ~10 rules fitted
per-document and no held-out set, every reported number is an in-sample number.

**Why stratified and not random:** the corpus has very different difficulty bands
(FY2010 scanned micro-cap vs FY2024 digital large-cap). An unstratified 1/3 split
can easily give a holdout with no scanned documents in it, which would make the
hardest case invisible.

**Why the holdout inspection log:** a holdout scored 50 times, with a rule tweak
between each, is not a holdout any more — it's a slow-motion training set.
`eval_holdout_log.csv` records the date and git commit of every holdout scoring,
so that drift is visible.

---

## 9. Re-fit a threshold to make a document pass — REJECTED

Covered in file 06, repeated here because it's the methodological core:

> A threshold moves because the data says its old value was in the wrong place.
> Never because moving it produces a grade you wanted.

---

## 10. Build vs reuse

| Component | Decision | Why |
|---|---|---|
| PDF text extraction | **Reuse** (pdfplumber / PyMuPDF) | Solved problem |
| OCR engines | **Reuse** (Tesseract, Paddle, DocAI) | Never write an OCR engine |
| Column detection | **Build** (`_column_cut`) | Off-the-shelf tuned for academic papers, not Indian A4 |
| MD&A location | **Build** | Nothing exists for Indian filings. This is the contribution. |
| Climate measure | **Reuse** (Sautner et al. dictionaries) | Reproducing a published measure is the point |
| Table extraction | **Defer** | Camelot/gmft exist; not needed while tables are quarantined |

**The rule applied throughout:** build only what is genuinely India-specific or
genuinely novel. Everything else is a dependency.
