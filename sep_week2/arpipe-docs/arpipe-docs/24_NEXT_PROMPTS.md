# 24 — NEXT PROMPTS (P21–P24) AND THE REVISED ORDER

Written after P0, P1, P16, P17, P16B, P18 all ran.
`21_CLAUDE_CODE_PROMPTS.md` still holds for P19, P2–P7, P8, P20, P10–P15.
This file adds four new prompts and answers the open threshold decision.

---

## 24.1 — THE DECISION: leave Jain FY2025 at `low`, but change the reason

**Leave `ORPHAN_START_FRAC_MAX = 0.03` and the 2× hard-low line where they are.
Do not re-fit to 3×.**

### Why not re-fit

The 3×MAX option was proposed *because* it keeps Jain FY2025 at medium. That is
picking a threshold to get a grade you like, which is the thing CLAUDE.md
forbids in the "Do not" list. The fact that a principled-sounding argument
(basis changed, denominator shrank) points the same way does not launder it —
if the basis-change argument were the real driver you would re-fit against the
*gap*, and the gap says 0.03 is still fine: clean sits at 0.000–0.004,
shredded at 0.064–0.098, and 0.03 is still in empty space with ~8× headroom
over the worst clean value.

### Why `low` is substantively right, not just arithmetically right

47 orphan starts in ~730 paragraphs means roughly 6% of sentences are cut at a
paragraph boundary. Your downstream use is bigram dictionary counting
(Sautner's physical component is 51 bigrams; Li et al.'s dictionaries are the
same shape) and transformer embeddings. Both are adjacency-sensitive.

The breaks are layout-driven, not content-driven, so the error is close to
random with respect to what is being measured. **Random measurement error in
the text attenuates the estimate toward zero.** For a thesis whose argument is
that an existing measure *understates* physical-risk exposure, attenuation
introduced by your own corpus is an uncomfortable confound — a referee will ask
whether the null is yours or the measure's.

So: `low` is honest. Both Jain years stay out of the clean tier.

### But the reason code is wrong

P16B already fixed the ordering. The residual 0.064 is not scrambled reading
order — it is the source PDF being pre-shredded. Grading it
`order_scrambled` will send you back to `xy_cut` next month looking for a bug
that is not there.

It needs its own reason: `source_shredded`, with the producer recorded.

---

## 24.2 — THE THING NOBODY HAS LOOKED AT YET

```
Jain Irrigation  document.json  ->  "pdf_producer": "iLovePDF"
KRBL             document.json  ->  "pdf_producer": "Adobe PDF Library 11.0"
                                     "Microsoft® Word 2016"
```

**Both of your bad documents come from one producer, and it is a free web
compressor.**

Somebody — the company or its filing agent — dragged the annual report through
iLovePDF before uploading it to NSE. That is what shredded the text blocks to
near-per-line. It is not a property of Indian annual reports, or of two-column
layouts, or of your pipeline.

This changes the size of the problem, in one of two directions, and you do not
yet know which:

| If `iLovePDF`-class producers are | Then |
|---|---|
| rare (say <5% of filings) | This is a per-document quarantine flag, not a pipeline problem. Flag, try the other exchange, move on. |
| common (say >20%) | It is one of the largest quality issues in the corpus, it is invisible to every metric you have except `orphan_start_frac`, and it needs its own handling before the full crawl. |

You can answer this cheaply — `pdf_producer` is already in every
`document.json`. And there is a plausible free fix: **NSE and BSE often serve
different copies of the same report.** If BSE has an un-shredded Jain FY2025,
you re-fetch one file and the problem disappears.

That is P22, and I would run it before P19.

---

## 24.3 — REVISED ORDER

```
DONE   P0   P1   P16   P17   P16B   P18

NEXT
  P21   Reason codes + record the measurement basis    30 min
  P22   pdf_producer investigation + re-fetch test     45 min   <- do this
  P23   strip_running_furniture order-independence     45 min
  P24   _column_cut unit test                          30 min
  P19   Paths, links, mda_path                         30 min
  P2    Bug: supporters gate                           20 min
  P3    Bug: ISIN extraction (cause confirmed)         30 min
  P4    Bug: DVR collapsing                            45 min
  P5    Bug: terminator heading shape                  30 min
  P6    Bug: TOC offset gate                           45 min
  P7    Minor fixes (cause confirmed)                  30 min
  P8    Re-run the 4, compare                          20 min
  P20   Era rules on full document                     30 min
  P10   BSE master                                     45 min
  P11   Twenty FY2010-2014 documents                   2-3 h    <- the real test
  P12   Labelling tool
  P13   Metric harness
  P14   Preflight
  P15   Config wiring
```

P21 and P24 are small and close open loops from P17/P18/P16B — do them while
the context is fresh. P22 can change how much of the rest matters.

---

# P21 — REASON CODES AND MEASUREMENT BASIS

```
Two loose ends from P17 and P18.

LOOSE END 1: a low grade caused by order quality writes no reason into the
manifest row. CLAUDE.md's third rule is "failures produce rows, never
absences" - but a row with tier=low and no reason is only half a row. Next
month I will not know why Jain was demoted.

Add a `reasons` list (not a single string - a document can fail two ways) to
every manifest row and to mda.json. Emit these codes:

    order_scrambled      orphan_start_frac over the gate AND the column
                         splitter did not fire on most span pages
    source_shredded      orphan_start_frac over the gate AND the column
                         splitter DID fire - i.e. ordering is as good as we
                         can make it and the residual is the source PDF.
                         Record pdf_producer alongside it.
    span_truncated       no cautionary-statement / disclaimer-shaped ending
                         found in the last ~15 lines
    identity_unproven    company_ok false
    year_unproven        year_ok false, or fy weight below the floor
    section_leak         leaks non-empty
    too_short / too_long
    ocr_budget_exhausted
    mda_not_located

Jain FY2024 and FY2025 must come out as `source_shredded`, NOT
`order_scrambled` - P16B already fixed their ordering, and mislabelling this
will send someone back into xy_cut looking for a bug that is not there.

LOOSE END 2: P18 changed what orphan_start_frac is measured on (prose only,
tables removed). A threshold is only valid on the basis it was fitted against,
and I now have scores in live_dataset/ from three different bases.

Record the basis in mda.json so a stored score is interpretable:

    "qc": {
      "orphan_start_frac": 0.064,
      "orphan_basis": "prose_only",        # or "prose_and_tables"
      "orphan_gate_version": "p17.1",
      "orphan_gate_max": 0.03
    }

Do NOT change the threshold value. 0.03 still sits in empty space between the
clean documents (0.000-0.004) and the shredded ones (0.064-0.098) on the new
basis, so it does not need re-fitting - it needs LABELLING so I can tell later
which basis a number came from.

Show me the diff. Then re-run extract to a fresh --out and print, for all four:
   company | fy | tier | reasons | orphan_start_frac | orphan_basis
```

**Acceptance test:** both Jain rows read `low` with `reasons:
["source_shredded"]` and `pdf_producer: "iLovePDF"` recorded. Neither says
`order_scrambled`.

---

# P22 — IS THE SHREDDING A JAIN PROBLEM OR A CORPUS PROBLEM?

**Run this before P19.** It can change how much the rest of the queue matters.

```
FINDING: both problem documents share one pdf_producer.

    Jain Irrigation FY2024, FY2025   pdf_producer: "iLovePDF"
    KRBL FY2024                      pdf_producer: "Adobe PDF Library 11.0"
    KRBL FY2025                      pdf_producer: "Microsoft Word 2016"

iLovePDF is a free web compressor. Someone ran the filing through it before
uploading to NSE, and that is what shredded the text blocks to near-per-line -
which is the entire residual orphan_start_frac after P16B fixed the ordering.

I need to know whether this is rare or common before I decide how much
machinery it deserves.

STEP 1 - MEASURE IT ON WHAT I HAVE.
  Count pdf_producer across every document.json in live_store (and
  _prior_runs if the fields are there). Print a frequency table.
  Flag known web compressors / re-processors:
      iLovePDF, Iloveimg, Smallpdf, PDF24, online2pdf, Nitro, Foxit
      PhantomPDF, "PDFsam", "3-Heights", anything containing "compress"
  Four documents is a tiny sample - tell me that plainly. The point is to
  build the counter now so the real number falls out of P11 and the crawl.

STEP 2 - CORRELATE IT.
  For every extraction I have, print:
      pdf_producer | blocks_per_page | lines_per_block | orphan_start_frac
  I expect a shredded producer to show many small blocks and a high orphan
  rate. Confirm or refute. If block-density predicts orphan rate, that is a
  CHEAP pre-flight signal available at triage time, before any extraction.

STEP 3 - CAN I JUST GET A BETTER COPY? (the important one)
  NSE and BSE often serve different files for the same report. Try to fetch
  Jain Irrigation FY2025's annual report from BSE (scrip code 500219) and
  from screener.in.
  For each copy obtained, report:
      sha256 | n_bytes | pdf_producer | blocks on the MD&A opening page |
      orphan_start_frac if I extract from it

  If a clean copy exists, this whole problem is a re-fetch, not a code change.

STEP 4 - RECOMMEND.
  Based on 1-3, tell me which of these to build:
    (a) nothing - it is rare, the source_shredded reason code is enough
    (b) a producer blocklist that triggers a re-fetch from the other exchange
    (c) a block-merging pre-pass in textlayer that stitches shredded
        per-line blocks back into paragraphs before xy_cut
    (d) something else

  Argue for one. Say what would change your mind.

Do NOT build anything in this prompt. Measure, test the re-fetch, recommend.
```

**Acceptance test:** you know whether Jain is a one-off, and whether a clean
copy of that PDF exists somewhere free.

**Why this ordering:** if (b) works, option (c) — the block-merging pre-pass —
never has to be written. That is a meaningful amount of fiddly code avoided by
one afternoon of measurement.

---

# P23 — MAKE `strip_running_furniture` ORDER-INDEPENDENT

```
P16B exposed this: after the reading-order fix, KRBL word counts moved by -7
and +28. Not lost body text - running-header fragments ("Annual Report
2023-24", "Corporate Overview", "Statutory Reports") being stripped or kept
differently because strip_running_furniture keys on the FIRST TWO and LAST TWO
physical lines of each page, and reordering changes which lines those are.

That is a latent fragility, not a P16B regression. But it means my furniture
stripping silently depends on reading order, so any future ordering change
moves word counts again and I will not know whether it is furniture or body.

Fix: make furniture detection depend on GEOMETRY AND REPETITION, not on line
position in the emitted string.

  1. Collect candidate furniture from BLOCK GEOMETRY, before reading-order
     sort: blocks whose y0 is in the top ~8% or bottom ~8% of the page.
  2. Normalise each candidate (strip digits, collapse whitespace, lowercase).
  3. A normalised string appearing in that zone on >35% of the document's
     pages is furniture.
  4. Remove those blocks BEFORE xy_cut runs - which also removes the
     full-width footer that caused the P16 bug in the first place, so this is
     defence in depth on the same failure.
  5. Keep the existing string-level pass as a second line of defence for
     anything that slips through.

Requirements:
  - Do not remove a block just because it is at the top of the page. It must
    also REPEAT. A section heading appears at the top of one page, not thirty.
  - Record qc.furniture_blocks_removed and the distinct normalised strings
    removed, so I can eyeball what went.
  - Add a test: a heading that appears at the top of exactly one page survives;
    a header appearing on 30 of 40 pages is removed.

Then re-extract all four to a fresh --out and show me:
  company | fy | n_words before | n_words after | furniture_removed |
  orphan_start_frac before | after

I expect KRBL's word counts to become STABLE across ordering changes. If
n_words moves by more than ~1% on any document, stop and tell me why.
```

**Acceptance test:** re-running with reading order forced off and forced on
gives the same `n_words` on all four documents. Today it does not.

---

# P24 — A UNIT TEST FOR `_column_cut`

```
_column_cut is now the single most important function in the pipeline - it is
what P16B added, it is what stops the corpus being scrambled, and it has no
dedicated test. It also carries two new provisional constants
(COLUMN_FULLWIDTH_FRAC = 0.60, COLUMN_CENTRE_GAP_FRAC = 0.14) that nothing
pins down.

Write synthetic-block tests. No PDFs - build the block lists directly, so the
tests are fast and the failure mode is obvious.

Cases that must pass:

  1. clean two-column          left blocks x[56,288], right x[303,540],
                               595pt page -> splits, left-then-right order
  2. THE JAIN CASE             same, PLUS a full-width footer block
                               x[62,577] (86% of width)
                               -> must STILL split. This is the exact
                                  regression P16B fixed - if this test ever
                                  fails, the corpus is silently scrambled again
  3. genuine single column     one column of blocks x[56,540]
                               -> must NOT split
  4. narrow gutter             14.8pt gutter on a 595pt page (Jain's real
                               measurement, 2.49%) -> must split via the
                               centre-gap fallback, since the histogram path
                               returns nothing at this width
  5. shredded blocks           two columns but ~40 tiny per-line blocks
                               instead of 6 paragraph blocks
                               -> must still split (this is what iLovePDF
                                  produces)
  6. full-width heading only   a title block spanning the page above two
                               columns -> heading first, then left, then right
  7. three columns             -> either splits correctly or declines to
                                  split, but must NOT interleave
  8. word conservation         for every case above: the multiset of words in
                               equals the multiset out. xy_cut must never
                               add or drop a token.

Case 8 is the one that matters most - assert it on all seven layouts, not just
one.

Also add a boundary test for each provisional constant: a block at 0.59 vs
0.61 of body width, and a centre gap at 0.13 vs 0.15, so that if someone
re-fits those numbers later the test tells them what behaviour they changed.
```

**Acceptance test:** case 2 fails if you revert P16B. That is the whole point —
a test that fails when the bug comes back.

---

# WHAT I WOULD NOT DO YET

| Tempting | Why not yet |
|---|---|
| Build the block-merging pre-pass for shredded PDFs | P22 may show a clean copy exists on BSE. Do not write the hard fix before checking for the easy one. |
| Re-fit `ORPHAN_START_FRAC_MAX` | It is doing its job. Re-fit it against the labelled 300 (P12/P13), not against four documents — twice. |
| Fix the stranded `Particulars 31st Mar` table headers | Same root cause as the shredding. P22 first. |
| Chase KRBL's paragraph-level interleave | `orphan_start_frac` reads 0.000 on it because its paragraphs stay intact. P16B improved it visibly. It is the mild version of a fixed bug. |
| Anything at 40k scale | Still the same answer. Twenty FY2010-2014 documents first. |

---

# ONE CORRECTION TO THE RECORD

The P1 audit said of Jain FY2025: *"the fragment's sentence-head is not
findable anywhere in the file by search — this looks like text lost, not merely
reordered."*

That was wrong, and P16's diagnostic corrected it: the head is at lines
112–113, split across a newline (`climate change\npresent persistent`), which
is why a naive search missed it. `23_EXTRACTED_TEXT_REVIEW.md` had it right —
reordered, not lost.

Worth noting because "text is being dropped" and "text is being reordered" call
for completely different investigations, and the first one is much scarier. It
was the second.
