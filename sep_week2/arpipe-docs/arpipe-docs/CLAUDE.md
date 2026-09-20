# ARPipe — project rules for Claude

*Last updated 10 September 2026, after P0, P1, P16, P17, P16B, P18.*

## What this project is

ARPipe collects annual reports of Indian listed companies (FY2010–FY2025) and
extracts the **Management Discussion & Analysis (MD&A)** section from each one.

Output per company-year: `mda.txt`, `mda_blocks.json` (quarantined tables and
charts) and `mda.json` holding the evidence for why we believe it.

Downstream use: climate-risk and disclosure text analysis — bigram dictionary
counts and transformer embeddings. That means **paragraph order and sentence
integrity matter as much as coverage.** Layout-driven sentence breaks are close
to random with respect to content, so they attenuate any count-based measure
toward zero. In a thesis arguing an existing measure *understates* exposure,
attenuation from your own corpus is a confound a referee will find.

---

## How to run it

```powershell
cd arpipe-0.1.0
.\arpipe.ps1 <stage> ...          # wraps cd arpipe / PYTHONPATH=.. / venv python
```

`--out` and `--root` must be on the **same drive** until P19 lands — a
cross-drive `os.path.relpath` raises `ValueError`, which `link_pdf` does not
catch.

`extract` is idempotent and skips documents already in the manifest. **After a
code change, extract to a fresh `--out`** or the run looks like a no-op and
your fix looks broken.

---

## The one design idea that must never be broken

**Locate the MD&A section BEFORE running OCR. Then OCR only the pages inside
that span.**

The MD&A is about 4.3% of the pages — measured, not assumed.

Verified twice on real data: a run over 1,275 real pages found **65 pages
needing OCR and OCR'd zero of them**, because none fell inside a located span.

If a change would OCR pages outside the located span, that change is wrong.

---

## Second rule: page-level, never document-level

Never ask "is this document scanned?". Ask "can I read THIS PAGE?".

Jain Irrigation FY2024 has 445 pages, ~57 of them scanned, and zero of those
fell inside the MD&A span. A document-level router would have OCR'd 445 pages
or skipped the document entirely.

Five page classes, not two:

```
digital       good text layer            -> read it, free
scanned       no text, one big image     -> OCR
hybrid        some text + big image      -> read text, OCR the image
broken-text   text exists but is garbage -> OCR, discard the text layer
vector-text   letters drawn as shapes    -> OCR
```

`broken-text` is the dangerous one. Every tool returns something; the something
is junk. Test: junk-character ratio above 2% means the text layer is dead.

---

## Third rule: failures produce rows, never absences

Every failure writes a manifest row with a `reasons` list and tier `low`.

A missing row is invisible. A `low` row with a reason is a work item.
**A `low` row with no reason is only half a row.**

Never `try/except: pass`. Never skip a document silently.

---

## Fourth rule: agreement is the confidence measure

Five independent methods locate the section:

```
S1  PDF outline / bookmarks
S2  printed contents page (needs a folio->physical offset solver)
S3  typographic heading (font size + position)
S4  OCR-text heading (works on scans)
S5  Schedule V body cues (the workhorse)
```

When several agree, that agreement **is** the confidence.
`supporters == 0` can never be graded `high`. *(Still violated — bug 4.)*

---

## Fifth rule: green metrics are necessary, not sufficient

**Read the output text, not just the metrics about it.**

Four documents were graded `high` with score 0.99, `leaks: []`, and every
character-ratio band in range — and two of them had their paragraphs in the
wrong order. Word count, `alpha_ratio`, `digit_ratio`, `long_token_frac` and
`leaks` were all green throughout.

The bands in this file were fitted on those same four documents, so **by
construction they cannot flag any of the four.** They prove nothing until
re-fit against the labelled 300.

---

## Performance rule that costs 128×

Never call `page.get_text("rawdict")` on an image page. It copies the embedded
image bytes into Python.

```
rawdict on a 29-page scanned PDF              29.4 seconds
dict with TEXTFLAGS_TEXT + get_image_info      0.23 seconds
```

Identical output. Use the second one.

---

## Reading order — CONFIRMED CAUSE AND FIX

**This section replaces earlier speculation. P16's diagnostic settled it.**

The bug was **not** the gutter threshold (already 2.5% at `textlayer.py:73`)
and **not** block-vs-line boxes as such.

`_gap_cut` looked for the widest empty interval between block x-extents. A
single **full-width block** — the running footer `"101 Statutory Report"`
(x62–577, 86% of a 595pt page), present on *every* page — drove the running
cursor to the right margin, so the widest interval was exactly **0.0** and
`_gap_cut` returned `None`. `xy_cut` then fell back to
`sorted(blocks, key=(y0, x0))` — the naive interleave it exists to prevent.

Measured on Jain FY2025: `widest_x_gap = 0.0000` and `vertical cut = None` on
**all 22** MD&A pages. Universal, not per-document — KRBL interleaved too, just
at paragraph granularity rather than mid-sentence.

**The fix (P16B, shipped):** `_column_cut` tries the projection histogram
first, then falls back to the widest gap between **block centres**. Full-width
blocks are held out of the split and re-inserted by `y0`. Two provisional
constants: `COLUMN_FULLWIDTH_FRAC = 0.60`, `COLUMN_CENTRE_GAP_FRAC = 0.14`.

**Note for anyone tempted to "just use `estimate_columns`":** it is not a
reliable oracle here. It returns 2 on only 4 of the 22 Jain MD&A pages and 1 on
the other 18 visually-two-column pages. The histogram path alone leaves Jain
interleaved — its gutter is 14.8pt on 595pt (2.49%), which is one histogram bin
short of `min_run` at every bin count.

A geometric cut can be wrong but can never *invent* text. A VLM can. For a
research corpus that difference matters — assert word conservation on every
layout.

---

## Order quality — the metric that catches what the others miss

`verify.order_quality(mda_text)`, added in P17.

```
orphan_start_frac   paragraph begins lowercase / , / ) AND the previous
                    paragraph either closed a sentence OR is heading-shaped
                    (the heading clause is what catches the
                     GLOBAL ECONOMY -> "formulation, while..." splice)
dangling_end_frac   recorded, not gated — too noisy until P18-style table
                    quarantine matures
```

Paragraphs are reconstructed first (join lines, break on blank line or closed
sentence) or per-line-shredded sources read as 100% orphans.

```
ORPHAN_START_FRAC_MAX = 0.03     > 0.03 caps at medium
                                 > 0.06 forces low
```

**PROVISIONAL. Re-fit against the labelled 300, not against four documents.**

Separation on the current basis (prose only, post-P18):

```
clean prose + both KRBL years    0.000 – 0.004
shredded (both Jain years)       0.064 – 0.098
```

The gate sits in empty space with ~8× headroom over the worst clean value.
**Do not re-fit it to change a specific document's grade** — that is fitting a
threshold to a desired outcome, whatever justification is attached.

**Known limit:** `orphan_start_frac` catches sentence-splitting interleave. It
reads 0.000 on KRBL even though KRBL's columns also interleaved, because KRBL's
paragraphs stay internally intact. Whole-paragraph reordering is milder for
downstream work and P16B fixed its root cause.

**Record the basis.** P18 changed what the metric measures (prose only, tables
removed). A stored score is uninterpretable without knowing which basis it used.

---

## The shredded-source problem

```
Jain Irrigation FY2024, FY2025   pdf_producer: "iLovePDF"
KRBL FY2024                      pdf_producer: "Adobe PDF Library 11.0"
KRBL FY2025                      pdf_producer: "Microsoft Word 2016"
```

Both problem documents share one producer, and it is a **free web compressor**.
The company or its filing agent ran the report through iLovePDF before
uploading to NSE, shredding text blocks to near-per-line. That is the entire
residual `orphan_start_frac` after P16B.

This is **not** a pipeline bug and **not** a property of Indian filings. It is a
bad copy of one PDF.

Consequences:

- Grade these `low` with reason `source_shredded`, never `order_scrambled` —
  the ordering is already as good as it can be made.
- Record `pdf_producer` alongside the reason.
- **Try the other exchange before writing any code.** NSE and BSE often serve
  different copies of the same report. A clean Jain FY2025 from BSE would make
  the whole problem a re-fetch.
- Count producer frequency across the corpus. Rare → a quarantine flag.
  Common → one of the largest quality issues in the dataset, invisible to every
  metric except `orphan_start_frac`.

---

## Repo layout

```
arpipe/
  cli.py         entry point, one command per stage
  models.py      dataclasses that move between stages
  universe.py    company master, ISIN keying, symbol chaining
  discover.py    NSE / BSE / screener adapters -> candidate URLs
  fetch.py       download, ZIP unwrap, qpdf repair, hash store
  triage.py      five page classes, script, columns, gutter_bands()
  textlayer.py   _column_cut, xy_cut, de-hyphenation, furniture stripping,
                 extract_prose_and_tables
  ocr.py         the ladder + quality gate + degeneracy guard   (NEVER RUN)
  segment.py     five location methods, arbiter, refine, trim
  patterns.py    all regexes (headings, terminators, cues, CIN, ISIN, FY)
  verify.py      identity, year, era rules, section QC, order_quality, grading
  store.py       output tree, manifests, resumability
  pipeline.py    the locate-then-OCR ordering
arpipe.ps1       run wrapper (stopgap until P19)
```

---

## Stages — each is a separate command, never merged

```
universe    build the company master
discover    find report URLs           ~17-36 hours, start it early
fetch       download PDFs              2-5 days
triage      classify every page        THE BUDGET GATE
extract     locate + OCR + verify + write
audit       dedup, coverage, quality
```

Different bottlenecks — network, disk, CPU, GPU. Coupling them makes the GPU
wait behind a politeness delay. Every stage resumable and idempotent.

---

## Known state — 10 September 2026

### Shipped

- **P16B** — `_column_cut`. Jain FY2025 now opens on a complete sentence; the
  `"formulation, while posing..."` fragment is gone. Split fired 19/22 and
  15/18 on Jain, 7/7 on both KRBL. `xy_cut` proven word-conserving on all four.
- **P17** — `order_quality`, gate at 0.03/0.06, 4 tests.
- **P18** — `extract_prose_and_tables`, sidecar `mda_blocks.json`, prose-only
  `n_words` and `digit_ratio`. 33 tests pass.
- 2,571-company NSE master; 4 real extractions; blob hashes verified intact;
  hardlinks work on D:.

### Open bugs

| # | Bug | Cause | Status |
|---|---|---|---|
| 4 | `supporters` ignored in grading | — | KRBL FY2025 `high` at supporters 0; Jain FY2024 `high` at 1 |
| 5 | ISIN never extracted | **confirmed** `ISIN_RE = \bINE[0-9A-Z]{9}\b` at `patterns.py:120` cannot match `IN9175A01010` | P3 |
| 6 | DVR ISIN not collapsed | Jain under `IN9175A01010`, not `INE175A01038` | P4 |
| 7 | Terminator matched body word `"trademarks"` | no heading-shape test | P5; KRBL FY2025 span is truncated as a result |
| 8 | TOC wins while wrong | folio-offset solver fails silently | P6; 26–28 vs 33–39, and 53–66 vs 27–33 |
| 9 | Cross-drive `ValueError` | `except OSError` misses it, `store.py:53` | P19; dormant while both paths on D: |
| 10 | Blob paths cwd-relative, backslashes | — | P19; `live_dataset/manifest.jsonl` still records `_demo_out\...` after the folder rename |
| 11 | `mda_path: null` | **confirmed** `pipeline.py:188` sets it *after* `write_year` serialised `mda.json` at `:186` | P19 |
| 12 | `ratio_cues` 7 not 8 | **confirmed** `MANDATED_RATIOS` are literal substrings at `patterns.py:104`; `"debtors turnover"` ≠ `"Debtor turnover ratio"` | P7 |
| 13 | `configs/default.yaml` read by nothing | PyYAML not installed | P15 |
| 14 | `fetch._repair` malformed qpdf command | `"--replace-input" if False else out` at `fetch.py:90` | P7/P19 |
| 15 | `discover --use-bse` is a no-op | `action="store_true", default=True`, `cli.py:218` | P10 |
| 16 | `strip_running_furniture` is order-dependent | keys on first/last two *emitted* lines | P23; caused the KRBL ±(7,28) word wobble |
| 17 | `_column_cut` has no unit test | — | P24; most important function, zero coverage |
| 18 | Order-quality `low` writes no reason code | — | P21 |

### Never exercised on real data

- **The entire OCR ladder.** `ocr_pages: 0` everywhere. tesseract, qpdf and the
  `hin` pack are all missing. `ocr.py:340` swallows Tesseract errors, so
  failure surfaces only as "not located" / LOW. Zero of 33 tests touch it.
- broken-text, vector-text, scanned, hybrid pages
- bilingual documents; any Devanagari
- anything before FY2016 — so **every era rule is untested**
- ZIP unwrap, qpdf repair, empty-password handling
- BSE and screener.in adapters; ~3,000 BSE-only small caps
- S1 outline, S2 contents-offset, S4 OCR-heading, S5 body cues have never
  cleanly won a real extraction
- the entire `medium` / `low` grading band, until P17 produced the first two
- name similarity below 100; any verification downgrade

---

## The benchmark is circular — do not quote the accuracy number

`tools/seed_historical_labels.py` contains:

```python
t_info = known_truth.get(cid, (p_s, p_e, 'OK'))
```

For any company not in the hand-written `known_truth` dict, ground truth
defaults to **the pipeline's own prediction**. Those documents cannot fail.
This makes the reported exact-start accuracy (90.0%) and IoU (0.8267)
**self-referential**. Of ~20 `known_truth` entries, ~6 were read by hand, and
4 of those 6 are the documents P25/P27 were developed against (train-on-test).
Honest evaluable count: about **2**.

`ok_rate` (71.6%) is a **confidence** rate, not accuracy. Rename it
`high_confidence_rate` — it reads as correctness in every table it appears in.

The one honest metric is **scrambled rate (0.0%)**: `orphan_start_frac` is
computed from text shape, not from labels, so it cannot be circular.

Fix order: P31 (remove the defaulting fallback, add `verified_by`),
P32 (fit/holdout split + protocol), P33 (false-positive audit of the ~10
single-document patterns). See `26_THE_MEASUREMENT_IS_CIRCULAR.md`.

**No threshold is re-fitted and no full extract is run until a hand-read set
exists that the pipeline has never been tuned against.**

### Two patterns under suspicion

- `is_cross_reference_pointer` is now **unconditional**. It guards Jain FY2025's
  legitimate `ANNEXURE V / MANAGEMENT DISCUSSION AND ANALYSIS` opening — a
  standard Indian shape, since Schedule V material is annexed to the Directors'
  Report. Un-restricted rejection may silently skip real MD&A starts.
- `"To the Members of"` as a terminator is also the standard **opening** of the
  Directors' Report and the Independent Auditor's Report. Needs a positional
  condition (only after start page + N pages of body), not a bare match.

---

## Health bands — circular, use with care

Fitted on the same four documents they are used to check, so they cannot flag
any of them. Every band has one of the four pinned to its min or max.

```
words per page      690.7 – 807.7
alpha_ratio         0.788 – 0.798
digit_ratio         0.015 – 0.020   (prose-only, post-P18)
avg_word_len         5.71 – 5.99
long_token_frac       0.0 on all four   (dead metric, no signal yet)
mda as % of pages    2.16% – 6.27%
orphan_start_frac   0.000 – 0.004 clean · 0.064 – 0.098 shredded
```

Re-fit against the labelled 300 (P12/P13). Until then treat drift as a prompt
to look, not as evidence.

---

## Rules for changes

### Do

- One change at a time, with a diff I can read
- Add a test for every fix, using real values from the four sample documents
- Assert **word conservation** on any change to `textlayer`
- Extract to a fresh `--out` after a code change (extract is idempotent)
- Move thresholds into config; never invent new hardcoded constants
- Mark any new constant `PROVISIONAL — re-fit against the labelled 300`
- Log **where** a value came from, not just the value
- Write `low`-tier rows with **reason codes** when something fails
- **Read the extracted text**, not only the metrics about it
- Say when something is unverified

### Do not

- Refactor unrelated code "while you are here"
- Add `try/except` that swallows a failure
- **Tune a threshold so a specific document gets the grade you want** — this
  includes principled-sounding re-fits that happen to produce the desired
  outcome
- Skip documents that fail
- Write a new OCR engine (use PaddleOCR-VL / MinerU2.5 / Tesseract)
- Build a web UI where a CSV would do
- Process the full corpus to "test at scale" — 20 documents from FY2010–2014
  first
- Conclude a document is fine because its metrics are green
- Write the hard fix before checking whether an easy one exists (e.g. a
  block-merging pre-pass before trying a re-fetch from the other exchange)

---

## OCR ladder — the rules (still unexercised)

```
rung 1   Tesseract                       free, CPU, English pages
rung 2   PaddleOCR-VL                    self-hosted, ~$190 per million pages
rung 3   Google Document AI or Gemini    ~$1,500/M, the 2-5% residue
```

**AWS Textract:** English, German, French, Spanish, Italian, Portuguese only.
**No Devanagari.** ~8× a self-hosted 1B model. Rung 3 only, never default.

**Quality gate between every rung.** Escalate on: word count far below page
area, mean confidence under 0.72, high non-alphanumeric ratio, tokens over 30
characters, or degeneracy.

**Degeneracy guard on every VLM output:**

```
output longer than 6x the anchor text   -> reject, escalate
8 or more identical consecutive lines   -> reject, escalate
```

A published Devanagari benchmark found one model producing output up to **71×**
the reference length on 2–3% of samples. Not optional.

**Document anchoring:** paste the PDF's own partial text into the VLM prompt as
a hint. Measurably reduces invented numbers.

**Token log-probabilities are not visual confidence.** A model's confidence in
`₹1,480.00` measures how likely that string is as *language*, not whether the
pixels say it.

---

## Numbers must carry provenance, not a score

FinCriticalED (859 financial pages, 9,481 annotated facts) found MinerU2.5 at
**95.71 ROUGE-1 but 54.05% monetary-unit accuracy**.

For any extracted figure record:

```
value, currency, unit (lakh/crore/million/'000), period, entity,
page, bbox, engine, validated_against
```

**The Indian unit trap:** the same table can be ₹ lakh, ₹ crore, ₹ million or
₹ '000, printed once in small type. Wrong unit = 10× to 100× error.
**Reject any table where no unit can be found. Do not guess.**

---

## Verification — prove it from inside the document

```
CIN     [LU] + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits
        L29120MH1986PLC042028  (Jain, Maharashtra, 1986)
        L01111DL1993PLC052845  (KRBL, Delhi, 1993)

ISIN    IN[EF9CD] + 9 alphanumerics
        INE = ordinary company line;  IN9 = additional series, often DVR

Name    fuzzy after stripping suffixes, vs canonical + all former names
        >=88 accept, 72-88 flag, <72 reject

Year    "year ended 31st March, 2015" = 5 · "2014-15" = 3
        "as at 31 March 2015" = 2      · "FY2015" = 2
        total weight below 15 -> thinly attested -> downgrade
```

**Era rules run over the FULL DOCUMENT, not the extracted span.** Confirmed
necessary: Jain's MD&A ends correctly at its Cautionary Statement and carries
14 financial tables, none of them the mandated ratio table — the ratios sit
outside the MD&A, so `ratio_cues` on the span is not a valid era signal.

```
8 mandated financial ratios present  -> FY >= 2020
BRSR present                         -> FY >= 2023
"Ind AS"                             -> FY >= 2016
"Companies Act, 2013" / CSR          -> FY >= 2015
Business Responsibility Report       -> FY >= 2013
```

Match the ratio names **tolerantly** — singular/plural, case, optional "ratio"
suffix, hyphen-vs-space, optional "(%)".

---

## Grading

```
supporters >= 2  AND score >= 0.80  AND no leaks          -> high
supporters == 1  AND score >= 0.60  AND <=1 leak          -> medium
supporters == 0                                           -> medium at best
                                                             (low if < 0.70)

any leak, identity unproven, year unproven, word count out of band,
or orphan_start_frac > 0.03                               -> medium
orphan_start_frac > 0.06                                  -> low
```

Every `low` and `medium` carries a `reasons` list. Targets: high ≥ 75%,
low ≤ 6%.

---

## When you are unsure

Say so. Write the uncertainty into the manifest as a reason code and grade the
row `low`.

A wrong row that looks confident is worse than a `low` row that says "I do not
know". At 40,000 documents, silent errors are the only errors that matter.
