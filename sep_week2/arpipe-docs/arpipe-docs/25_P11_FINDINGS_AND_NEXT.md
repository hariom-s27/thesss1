# 25 — WHAT P11 ACTUALLY FOUND, AND WHAT TO DO NEXT

Written after P0–P24 shipped, 152 tests green, and the P11 historical run
(20 documents, FY2010–2014) came back.

---

## 25.1 — THE DECISION: don't crawl, don't label yet

Two options were on the table. Both are wrong right now.

### Don't launch the full crawl

P11's own numbers say why. From the seeded ground truth in the P13 harness:

```
KRBL FY2014          true 8-21    predicted 0-0     WRONG_START
Inter State Oil 2011 true 15      predicted 10      WRONG_START
SAIL FY2011          true 29-36   predicted 26      WRONG_START
Modern Steels 2013   true 9-13    predicted 16      WRONG_START
```

**Four wrong starts out of the eleven historical documents that have an MD&A.**
That is roughly a **36% start-page error rate** on the FY2010–2014 era.

The target in `16_TWELVE_WEEK_PLAN.md` is **≥85% within ±1 page on scanned**.

A 40,000-document crawl at a 36% error rate means ~14,000 wrong spans, OCR
budget spent on the wrong pages, several days of wall-clock, and a full re-run
afterwards — because what's wrong is the *span*, not the *grade*. You cannot
patch a wrong page range after the fact.

### Don't label 300 documents yet either

The labelled set exists to **calibrate thresholds** and **measure**. It is not
a bug-discovery tool.

P11 already discovered the bugs. Labelling 300 documents first means spending a
week to be told, in metric form, the same three things you can read directly in
the P11 output today.

### What to do instead

**Fix the three bugs P11 found. They are logic bugs, not threshold bugs.**

That distinction is the whole argument. CLAUDE.md forbids tuning thresholds
against a handful of documents — correctly. But none of these three is a
threshold:

| Bug | Fix type | Needs the labelled 300? |
|---|---|---|
| Outline points at a cover page and wins anyway | **validation step** — does the bookmarked page contain prose? | No |
| Index sampler never looks at page 15 | **arithmetic bug** — deterministic blind spot | No |
| A cross-reference is matched as a section heading | **pattern addition** — a fixed list of phrases | No |

None of them is calibrated against anything. Fixing them is not overfitting.

Then: cap bands → label 300 → re-fit thresholds → crawl.

---

## 25.2 — BUG A: the outline wins while pointing at the cover

**KRBL FY2014 extracted 7 words.**

```
Annual Report 2013-14
KRBLo a
Become
Believe
```

That is the cover page.

### What happened

```
diag candidates:
  ['outline',    0,  0, 0.95]   <- WON. Bookmark "KRBL MDA" -> page 0
  ['heading',    8, 21, 0.894]  <- CORRECT. 14 pages of real MD&A
  ['body_score', 6, 25, 0.653]  <- also roughly correct
```

The outline method carries a base score of **0.95**. The heading method scored
**0.894** on the right answer. Outline won by 0.056 and the document became
garbage.

### This was a documented, known failure that was never implemented

`CLAUDE.md` and `08_STEP6_FIND_MDA.md` both say, of strategy S1:

> **Known failure:** the bookmark often points at the *divider* page, not the
> first page of text. Add a "walk forward until real prose starts" step.

That step was never added. P11 is the first time a real document exercised it.

### The fix is validation, not down-weighting

Do **not** lower `outline_base_score`. That is the threshold-tuning trap, and it
would break the cases where the outline is right (which is most of them —
outline is genuinely the most precise signal when it works).

Instead: **an outline candidate must prove its target page has MD&A in it.**

```
outline proposes pages [a, b]
    |
    v
does page a contain prose?
    word count >= ~120
    alpha_ratio in a sane band
    at least 1 Schedule V body cue on page a or a+1
    |
   YES --> accept, keep score 0.95
    |
   NO
    |
    v
walk forward from a, up to ~8 pages, until a page passes
    |
   found --> accept with the corrected start, score 0.95 - 0.05
    |
   not found --> INVALIDATE the outline candidate entirely.
                 It does not compete. It may not even support.
```

On KRBL FY2014 page 0 has 7 words. It fails on the first test. The outline
candidate is dropped, `heading` wins at 0.894, and you get 14 pages of MD&A
instead of a cover.

**Frequency estimate:** bookmarks appear in ~35–55% of post-2016 filings. If
even 10% of those point at a divider, that is 1,500–2,500 documents in the full
corpus reduced to a title page. Each one would pass QC as `too_short` → `low`,
so you would *see* it — but you would see 2,000 of them and have no idea why.

---

## 25.3 — BUG B: the index sampler has a deterministic blind spot

**Inter State Oil Carrier FY2011 extracted the Remuneration Committee
disclosure.**

The true MD&A is on page 15. The pipeline extracted pages 10–11 — a
cross-reference notice inside the Corporate Governance report.

### The arithmetic

The document is **100% scanned** (48 of 48 pages). With no text layer, the only
way to locate anything is to OCR a sample. The sampler takes:

```
page < FRONT_PAGES (14)   or   page % INDEX_STRIDE (6) == 0
```

So on a 48-page document it OCRs pages:

```
sampled:      0 1 2 3 4 5 6 7 8 9 10 11 12 13    18    24    30    36    42
never seen:                                 14 15 16 17  19 20 21 22 23  25 ...
```

**Page 15 is structurally invisible.** So is 14, 16, 17, 19, 20, 21, 22, 23, 25…

This is not a tuning problem. It is a gap in the sampling grid that no threshold
change closes — `front_pages` and `index_stride` are both now in config (P15),
and no value of either makes the grid cover everything.

### The fix, and its cost

For a **short, heavily-scanned** document, sample every page:

```
if n_pages <= 60 and frac_needing_ocr > 0.80:
        sample every page
else:
        keep front matter + stride, but sweep the offset:
        page % stride in (0, stride//2)     -> halves the blind spot
```

**Cost check, using P11's own measured 4.438 s/page:**

| Document | Current | Every page | Extra time |
|---|---|---|---|
| Inter State Oil, 48 pp | 18 pages, 80 s | 48 pages, 213 s | **+133 s** |
| Coal India, 234 pp | 65 pages, 318 s | 234 pages, 1,039 s | +721 s — too much, keep the stride |

133 extra seconds to get the right section instead of the Remuneration
Committee. On the population this matters for — small BSE-only companies with
short scanned filings, which is exactly the FY2010–2014 tail — that trade is
obviously worth taking.

The `<= 60 pages` bound is not a tuned threshold; it is a budget statement. Say
so in the comment.

---

## 25.4 — BUG C: a cross-reference is matched as the section heading

**SAIL FY2011 extracted 469 words about Vigilance.**

The matched "heading", on page 26 inside the Directors' Report, was:

```
MANAGEMENT DISCUSSION & ANALYSIS REPORT
The Management Discussion & Analysis Report covering the performance and
outlook of the Company is given separately in the Annual Report.
```

That is a **pointer to** the MD&A, not the MD&A. The real one is at pages
29–36. The span then terminated immediately on page 27's "CONSOLIDATED
FINANCIAL STATEMENTS", producing a single page of unrelated text.

### Why this is the most important of the three

**This pattern is near-universal in Indian annual reports.** The Directors'
Report routinely cross-references the MD&A, the Corporate Governance Report,
the BRSR and the auditor's report, because SEBI permits them to be presented as
annexures. Every filing that does this has a decoy heading sitting *earlier* in
the document than the real section — and "earlier" is exactly where a
first-match scan looks.

P5's heading-shape gate does not catch it, because the line **is** heading
shaped: short, own line, ALL CAPS, top of a block. The shape is right. The
*context* is wrong.

### The fix: a cross-reference phrase list

A heading is a decoy if, within roughly the next 30 words, the text contains
one of:

```
is given separately
is annexed
annexed hereto
forms part of this report
forms an integral part
appearing elsewhere in this
is provided elsewhere
set out in a separate section
is attached as Annexure
please refer to
as required under ... is given
```

When a heading match is followed by one of those, **do not start a span
there.** Record it as `cross_reference_suppressed` in diag and keep scanning.

Guard against the opposite error: a real MD&A section can legitimately *open*
with an annexure label (`ANNEXURE V / MANAGEMENT DISCUSSION AND ANALYSIS` —
Jain Irrigation does exactly this). The distinction is that Jain's heading is
followed by **prose about the business**, SAIL's by **a sentence about where to
find the report**. The phrase list catches that difference; a shape test cannot.

**Cheap corroborating test:** a genuine MD&A start page carries Schedule V body
cues within the next 2–3 pages. A cross-reference does not. Require at least one
cue in the window before accepting a heading as a start.

---

## 25.5 — A QUESTION THE RUN RAISES THAT NOBODY ASKED

**Coal India FY2012: 230 of 234 pages classified `broken_text`.**

```
Coal India Limited FY2012 | 234 pp | digital 3 | scanned 1 | broken 230
                          | frac_needing_ocr 0.9872
                          | 65 pages OCR'd, 318.2 seconds
```

A Coal India annual report is a professionally typeset PSU document. **98.7%
broken text layer is not plausible.** A genuinely broken document would not have
3 clean pages scattered in it either.

Far more likely: a font-encoding quirk — a subset-embedded font with a
non-standard `ToUnicode` map on the body face — that trips the 2% mojibake
threshold on every page that uses it.

### Why this matters more than one document

`broken_text` is the most expensive classification in the pipeline: it means
"throw the free text away and pay for OCR." If the detector over-fires, the OCR
bill is driven by false positives, and you would never notice, because the OCR
output looks fine.

At 40,000 documents, a mojibake detector that is too aggressive is plausibly the
**single largest OCR cost line in the project** — and it is invisible in every
metric you currently collect.

### The test is five minutes

```
1. Take one Coal India page flagged broken_text.
2. Dump page.get_text() raw. Print it.
3. LOOK AT IT.

   readable English  -> the 2% mojibake threshold is wrong, and you just
                        spent 318 seconds OCRing a readable document
   actual garbage    -> the detector is right, PSU typesetting of that era
                        really is that bad, and that is itself a finding
```

Then run the same check across all 20 P11 documents: what fraction of
`broken_text` pages, when you print them, are actually readable?

This is a measurement, not a fix. Do not touch the threshold until you have
looked.

---

## 25.6 — THE GAP P11 EXPOSED IN P16B

From the P11 report, and this is a sharp observation worth not losing:

```
docs with OCR'd pages:  mean orphan_start_frac = 0.0237
docs with 0 OCR pages:  mean orphan_start_frac = 0.0185

"raw Tesseract text lacks PyMuPDF block bounding-box geometry, preventing
 xy_cut column slicing"
```

**P16B's column fix does not apply to OCR'd pages at all.**

The entire reading-order infrastructure — `_column_cut`, the gutter histogram,
the centre-gap fallback, the furniture stripping, all 33 tests in
`test_column_cut.py` — operates on PyMuPDF block geometry. OCR'd pages arrive
as a flat string. They bypass all of it.

Which means the column-interleaving bug that consumed P16/P16B/P17/P18 **is
still fully present on scanned pages** — the pages that are most likely to be
two-column, in the era where scans live.

Both Coal India (0.031) and Inter State Oil (0.046) tripped `order_scrambled`
for exactly this reason.

### The fix is available and not large

`pytesseract.image_to_data(img, output_type=Output.DICT)` returns per-word
boxes:

```
left, top, width, height, block_num, par_num, line_num, conf, text
```

Group words by `(block_num, par_num)`, take the bounding box of each group, and
you have block geometry in the same shape `_column_cut` already consumes. Feed
it through the *existing* function. No new column logic, no new constants, and
all 33 existing tests still guard it.

This closes the last hole in the P16B work, and it has to happen before the
scanned era can be trusted at all.

---

## 25.7 — WHAT THE RUN GOT RIGHT (do not "fix" these)

Two P11 results look like failures and are correct behaviour:

```
Muller & Phipps FY2012   mda_not_located   0 mentions of MD&A in the PDF
K.Z. Leasing FY2010      mda_not_located   26-page compliance filing, no MD&A
```

**Small companies genuinely omit the MD&A.** SEBI's requirement has thresholds,
and a 26-page filing from a micro-cap NBFC may legitimately not carry one.

The pipeline looked, did not find it, and said so with a reason code. That is
rule 3 working exactly as designed. Both documents produced a row, not an
absence.

Resist any pressure to make these "succeed." A `mda_not_located` rate of
somewhere around 5–10% in the micro-cap tail is a real property of the corpus,
and a finding in itself.

Also working: **0 crashes across 20 documents**, including 9 ZIP archives,
100%-scanned PDFs, and a 234-page broken-text monster. The error handling holds.

---

## 25.8 — THE REVISED ORDER

```
NEXT
  P25   Outline validation (Bug A)           45 min
  P26   Index sampler blind spot (Bug B)     45 min
  P27   Cross-reference suppression (Bug C)  45 min
  P28   Mojibake reality check (measure)     30 min   <- may reshape the budget
  P29   OCR block geometry -> _column_cut    2 h      <- closes the P16B hole
  ------------------------------------------------ then measure
  P30   Cap bands (prerequisite for P12)     30 min
  P12b  Label 300, stratified                1 week   <- the highest-leverage week
  P13b  Re-fit every threshold against them  3 days
  ------------------------------------------------ then, and only then
  Full Stage 2 discovery crawl
```

Re-run P11's 20 documents after P25–P27 and compare. That is the acceptance
test: KRBL FY2014 should go from 7 words to ~14 pages, Inter State Oil from the
Remuneration Committee to page 15, SAIL from Vigilance to pages 29–36.

If those three move, the historical-era error rate drops from ~36% to something
worth measuring properly. **That is what makes the labelling week worth doing.**

---

# P25 — OUTLINE MUST PROVE ITS TARGET

```
BUG: KRBL FY2014 extracted 7 words - the cover page.

    diag candidates:
      ['outline',    0,  0, 0.95]   <- WON
      ['heading',    8, 21, 0.894]  <- the correct answer, 14 pages
      ['body_score', 6, 25, 0.653]

The PDF's bookmark "KRBL MDA" points at page 0. The outline method's base score
(0.95) beat the correct heading match (0.894) by 0.056, and the document became
a title page.

CLAUDE.md and 08_STEP6_FIND_MDA.md have both documented this failure from the
start ("the bookmark often points at the divider page, not the first page of
text - add a walk-forward step"). It was never implemented. P11 is the first
real document to hit it.

DO NOT lower outline_base_score. The outline is the most precise signal we have
when it is right, and down-weighting it would break the majority case. This is
a validation problem, not a scoring problem.

Fix in segment.py - an outline candidate must PROVE its target page:

  1. Given outline span [a, b], test page a for prose:
        word count >= 120
        alpha_ratio within the healthy band
        at least 1 Schedule V body cue on page a or a+1

  2. If it fails, walk forward from a (cap ~8 pages) until a page passes.
     If one does: accept with the corrected start, score reduced by ~0.05
     to record that we moved it.

  3. If nothing passes within the cap: INVALIDATE the outline candidate
     entirely. It must not win AND must not count as a supporter - a
     candidate that points at nothing is not independent evidence.

  4. Record in diag:
        "outline_validation": {"proposed_start": 0, "accepted_start": null,
                               "walked": 8, "outcome": "invalidated",
                               "reason": "no_prose_within_cap"}

Add tests:
  - outline -> page 0 with 7 words, heading -> pages 8-21 with real prose:
    heading must win, outline must be invalidated, supporters must NOT
    count the outline
  - outline -> a divider page, real prose on the next page: outline wins
    with the start corrected to a+1
  - outline -> a correct page: unchanged, score stays 0.95

Then re-run KRBL FY2014 from p11_store and show me the new span and the first
20 lines of mda.txt.
```

**Acceptance test:** KRBL FY2014 returns roughly pages 8–21, several thousand
words, not 7.

---

# P26 — THE SAMPLER NEVER LOOKS AT PAGE 15

```
BUG: Inter State Oil Carrier FY2011 extracted the Remuneration Committee
disclosure from the Corporate Governance report. The true MD&A is on page 15.

The document is 100% scanned (48/48 pages), so the only way to find anything is
to OCR a sample. The sampler takes:

    page < FRONT_PAGES (14)   or   page % INDEX_STRIDE (6) == 0

On a 48-page document that samples 0-13, 18, 24, 30, 36, 42 - and NEVER
14, 15, 16, 17, 19, 20, 21, 22, 23, 25...

Page 15 is structurally invisible. No value of front_pages or index_stride
closes this; it is a gap in the grid, not a threshold.

Fix in pipeline.py:

  1. For short, heavily-scanned documents, sample everything:

         if n_pages <= 60 and frac_needing_ocr > 0.80:
                 sample every page

     Cost, using P11's measured 4.438 s/page mean:
         48-page doc: 18 pages / 80 s  ->  48 pages / 213 s   (+133 s)
     That is the price of the right section instead of the wrong one.
     The 60-page bound is a BUDGET statement, not a tuned threshold -
     say so in the comment.

  2. For longer documents, sweep the offset so the blind spot halves:

         page % stride in (0, stride // 2)

  3. Record what was actually sampled:
         "index_sample": {"mode": "exhaustive"|"stride",
                          "pages_sampled": 48, "pages_total": 48,
                          "stride": null, "cost_pages": 48}

  4. Add a test asserting that for a 48-page doc at 100% scanned, page 15
     IS in the sampled set. That test fails on today's code.

Then re-run Inter State Oil Carrier FY2011 and show me the new span plus the
first 25 lines of mda.txt.
```

**Acceptance test:** the span moves to page 15 and the text is MD&A, not the
Remuneration Committee attendance table.

---

# P27 — A CROSS-REFERENCE IS NOT A SECTION HEADING

```
BUG: SAIL FY2011 extracted 469 words about Vigilance. The matched heading, on
page 26 inside the Directors' Report, was:

    MANAGEMENT DISCUSSION & ANALYSIS REPORT
    The Management Discussion & Analysis Report covering the performance and
    outlook of the Company is given separately in the Annual Report.

That is a POINTER to the MD&A, not the MD&A. The real section is pages 29-36.
The span then hit "CONSOLIDATED FINANCIAL STATEMENTS" on page 27 and terminated
after one page.

P5's heading-shape gate cannot catch this - the line IS heading shaped (short,
own line, ALL CAPS, top of block). The shape is right; the CONTEXT is wrong.

This pattern is near-universal in Indian filings. SEBI permits MD&A, Corporate
Governance and BRSR to be presented as annexures, so the Directors' Report
routinely cross-references them - which plants a decoy heading EARLIER in the
document than the real section, exactly where a first-match scan looks.

Fix in patterns.py + segment.py:

  1. Add a cross-reference phrase list:

        is given separately          forms part of this report
        is annexed                   forms an integral part
        annexed hereto               appearing elsewhere in this
        is provided elsewhere        set out in a separate section
        is attached as Annexure      please refer to

  2. A heading match is SUPPRESSED as a cross-reference if one of those
     appears within ~30 words after it. Do not start a span there.
     Record it: "cross_reference_suppressed": [{"page": 26, "phrase":
     "is given separately", "heading": "MANAGEMENT DISCUSSION & ANALYSIS
     REPORT"}]

  3. GUARD AGAINST THE OPPOSITE ERROR. A real MD&A can legitimately open with
     an annexure label - Jain Irrigation FY2025 starts with
     "ANNEXURE V / MANAGEMENT DISCUSSION AND ANALYSIS". The difference is what
     FOLLOWS: Jain's heading is followed by prose about the business, SAIL's by
     a sentence about where to find the report. Only suppress on the phrase
     list, never on the word "Annexure" alone.

  4. Corroborate: require at least one Schedule V body cue within 2-3 pages of
     a candidate start before accepting it. A cross-reference has none.

Add tests using the REAL strings:
  - SAIL's exact two lines -> suppressed, no span starts at page 26
  - Jain's "ANNEXURE V / MANAGEMENT DISCUSSION AND ANALYSIS" followed by
    "GLOBAL ECONOMY / As per its latest assessment..." -> NOT suppressed
  - a bare "Management Discussion and Analysis" heading followed by business
    prose -> NOT suppressed

Then re-run SAIL FY2011 and show me the new span and the first 25 lines.
```

**Acceptance test:** SAIL lands on roughly pages 29–36 with several thousand
words, and Jain Irrigation FY2025 is unchanged.

---

# P28 — IS COAL INDIA REALLY BROKEN? (measure only)

```
QUESTION, not a bug - yet.

Coal India FY2012 triaged as 230 of 234 pages `broken_text`, frac_needing_ocr
0.9872. We OCR'd 65 pages and spent 318 seconds on it.

A Coal India annual report is a professionally typeset PSU document. 98.7%
broken text layer is not plausible, and a genuinely broken file would not have
3 clean pages scattered through it. A subset-embedded font with a non-standard
ToUnicode map would produce exactly this pattern.

This matters far beyond one document. `broken_text` is the most expensive
classification we have - it means "throw the free text away and pay for OCR."
If the 2% mojibake threshold over-fires, the OCR bill is driven by false
positives, and nothing in our metrics would show it, because the OCR output
looks fine.

DO NOT change any threshold in this prompt. Measure.

  1. Take 5 Coal India pages flagged broken_text. Dump page.get_text() RAW,
     unmodified, and PRINT IT so I can read it with my own eyes.

  2. For each, print the computed mojibake ratio and which characters drove it.

  3. Across all 20 P11 documents, report:
        total pages flagged broken_text
        their mojibake ratios (min / median / max)
        for a random 20 of them: is the raw text readable English? y/n
        what fraction of broken_text flags look like FALSE POSITIVES

  4. Check the font angle: for a flagged page, list the embedded fonts and
     whether each has a ToUnicode CMap. If the flagged pages share one font
     that lacks ToUnicode, that is the mechanism.

  5. Report the cost of being wrong:
        OCR pages spent on documents that are >80% broken_text
        x 4.438 s/page = wasted seconds
        extrapolated to 40,000 documents at the observed broken_text rate

Then tell me which is true:
  (a) the text is readable -> the threshold is wrong and we are burning OCR
      budget on readable documents
  (b) the text is genuinely garbage -> the detector is right, and PSU
      typesetting of that era is a real corpus property worth recording

Argue for one. Do not fix anything.
```

**Acceptance test:** you have read raw text from a flagged page with your own
eyes and know which of (a) or (b) is true.

---

# P29 — GIVE OCR'd PAGES BLOCK GEOMETRY

```
GAP: P16B's column fix does not apply to OCR'd pages at all.

    docs with OCR'd pages:  mean orphan_start_frac = 0.0237
    docs with 0 OCR pages:  mean orphan_start_frac = 0.0185

_column_cut, the gutter histogram, the centre-gap fallback, the geometry-based
furniture stripping and all 33 tests in test_column_cut.py operate on PyMuPDF
block geometry. OCR'd pages arrive as a flat string and bypass every one of
them.

So the column-interleaving bug that P16/P16B/P17/P18 were built to fix is still
FULLY PRESENT on scanned pages - which are the most likely to be two-column, in
the era where scans live. Coal India (0.031) and Inter State Oil (0.046) both
tripped order_scrambled for this reason.

Fix in ocr.py:

  1. Switch the Tesseract call to
        pytesseract.image_to_data(img, output_type=Output.DICT)
     which returns per-word: left, top, width, height, block_num, par_num,
     line_num, conf, text

  2. Group words by (block_num, par_num). Take each group's bounding box.
     Scale from render DPI back to PDF points so the coordinates match what
     _column_cut expects from PyMuPDF.

  3. Emit blocks in the SAME shape textlayer already consumes, and pass them
     through the EXISTING _column_cut. Write no new column logic and add no
     new constants - the 33 existing tests then guard the OCR path too.

  4. Keep the flat-string path as a fallback if image_to_data fails, and
     record which path ran:
        "ocr_geometry": "blocks" | "flat"

  5. Report before/after orphan_start_frac on the four P11 documents that
     used OCR:
        Coal India FY2012, Inter State Oil FY2011,
        TCS FY2010, KRBL FY2014

Then show me the first 25 lines of Inter State Oil FY2011's mda.txt before and
after, so I can see the column order with my own eyes.
```

**Acceptance test:** `orphan_start_frac` on the OCR'd documents drops toward the
born-digital band, and Coal India / Inter State Oil stop tripping
`order_scrambled`.

**Note:** run this *after* P26, or Inter State Oil will still be extracting the
wrong pages and the comparison will be meaningless.

---

# P30 — CAP BANDS (and one caveat)

```
companies.csv has 4,886 companies and an empty cap_band column. The stratified
sampler (P12), the evaluation harness (P13) and every per-stratum audit report
need it.

Attach AMFI market-cap classification:
    rank 1-100    large
    rank 101-250  mid
    rank 251-500  small
    rank 501+     micro

TWO THINGS TO GET RIGHT:

1. NAME THE COLUMN `cap_band_current`, not `cap_band`.
   AMFI's list is CURRENT (2026) market cap. Our corpus spans FY2010-2025. A
   company that is large-cap today may have been small in 2012. For stratifying
   a SAMPLE that is fine - we are balancing coverage, not making an economic
   claim - but the name must not imply a time-varying measure we do not have.
   Document the limitation in a comment and in the audit report header.

2. EXPECT A LOPSIDED DISTRIBUTION AND REPORT IT.
   AMFI classifies the top 500. That leaves ~4,400 of 4,886 as `micro`.
   Print the actual counts per band. The stratified sampler will have a huge
   micro bucket and small large/mid buckets - so `sample-for-labelling` must
   sample PROPORTIONALLY WITHIN a floor (e.g. at least 20 per band), not
   equally, or the labelled 300 will be 75 large-caps and misrepresent the
   corpus.

Then re-run `sample-for-labelling --n 300` and show me the cell-fill table:
how many it got in each era x cap_band x doc_kind cell, and which cells it
could not fill.
```

**Acceptance test:** the cell-fill table exists and you know which strata the
corpus cannot supply. Those empty cells are a finding, not a failure.

---

## 25.9 — THE ONE-LINE VERSION

> **Don't crawl — the historical era has a ~36% start-page error rate. Don't
> label yet — P11 already found the three bugs causing it, and all three are
> logic, not thresholds. Fix P25–P27, check the Coal India mojibake question,
> close the OCR reading-order hole, then label, then crawl.**
