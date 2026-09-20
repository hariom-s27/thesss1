# 21 — CLAUDE CODE PROMPTS

**What this file is:** copy-paste prompts for Claude Code. One prompt = one job.

**How to use it:**

```
1. Open a terminal in your arpipe folder
2. Run:  claude
3. Copy ONE prompt from below
4. Paste it
5. Wait. Read what it says. Check the acceptance test.
6. Only then move to the next prompt.
```

**Rules for yourself:**

- **One prompt at a time.** Never paste two. It will half-do both.
- **Read the diff before you accept it.** Claude Code shows you every change.
- **If a prompt fails, do not paste the next one.** Fix it first.
- **Say "no" freely.** If it wants to rewrite a file you like, tell it not to.

**Before anything:** put `CLAUDE.md` in your repo root, next to `README.md`.
Claude Code reads it automatically every session. It stops most of the
wandering.

---

## THE ORDER

The order changed after reading the actual extracted text. See
`23_EXTRACTED_TEXT_REVIEW.md`. **The reading-order bug now comes first**,
because it silently corrupts the deliverable and every existing quality metric
says it is fine.

```
  P0    Setup check              15 min    <- do this first
  P1    Look at my data          10 min
  ------------------------------------------ THE TEXT IS WRONG
  P16   Reading order diagnosis   45 min    <- START HERE after P0/P1
  P17   Order-quality metric      45 min
  P18   Quarantine the tables     45 min
  ------------------------------------------ the run-blockers
  P19   Link + path portability   30 min
  ------------------------------------------ the five original bugs
  P2    Bug 3: supporters gate    20 min
  P3    Bug 2: ISIN extraction    45 min
  P4    Bug 1: DVR collapsing     45 min
  P5    Bug 4: terminator shape   30 min
  P6    Bug 5: TOC offset         45 min
  P7    Minor fixes               30 min
  ------------------------------------------ verify
  P8    Re-run the 4 samples      20 min
  P20   Era rules on full doc     30 min
  ------------------------------------------ the real test
  P10   Wire the BSE master       45 min
  P11   Twenty old scanned docs   2-3 hours  <- FIRST REAL OCR TEST
  ------------------------------------------ make it measurable
  P12   Labelling tool            1 hour
  P13   Metric harness            1 hour
  P14   Preflight command         45 min
  P15   Wire the config file      45 min
```

P9 (the Jain ratio question) has been **answered** — see `23`, section 23.3.
No boundary bias. It became P20 instead.

---

# P0 — SETUP CHECK

```
Read README.md, CLAUDE.md and arpipe/ to understand this project.

Then check my environment and tell me what is missing. Specifically:

1. Is `tesseract` installed and on PATH? Which languages does it have?
   Run `tesseract --list-langs`.
2. Is `qpdf` installed?
3. Which Python packages from requirements.txt are missing in the active venv?
4. How much free disk is there where store/ lives?
5. Do the tests pass? Run them.
6. Can I create a symlink and a hardlink in this environment? Test both.
   (On Windows symlinks need Developer Mode or admin.)

Do NOT fix anything yet. Just give me a table:

  | thing | status | how I install it on my OS |

Tell me my OS first so the install commands are right.
```

**Expected finding:** tesseract and qpdf are missing. That is why `ocr_pages`
was 0 on all four documents — the OCR ladder has literally never run.

---

# P1 — LOOK AT MY DATA AND TELL ME WHAT TO DO

```
Read dataset/manifest.jsonl and every dataset/companies/*/*/mda.json.

Do not change any code. Just analyse and report.

Give me these six things:

1. A TABLE of every extraction:
   company | fy | total_pages | mda_pages | n_words | words_per_page |
   method | supporters | confidence | ocr_pages | leaks | ratio_cues

2. HEALTH BANDS. For each of these, give min / max / median and say whether
   any row is an outlier:
     words_per_page, alpha_ratio, digit_ratio, avg_word_len,
     long_token_frac, mda_pages_as_percent_of_total

3. CONTRADICTIONS. Find every row where the numbers disagree with each other.
   Examples:
     - confidence is "high" but supporters is 0
     - span_words in diag is very different from n_words
     - fy_end is 2020 or later but ratio_cues is 0
     - terminator_text is not shaped like a section heading
     - the winning method's candidate range in diag is far from the final span
     - mda_path or path is null on a successful extraction
   List every one, with the row it came from.

4. WHAT IS UNTESTED. Look at what page classes, years, exchanges, scripts and
   OCR rungs appear in the data. Tell me what has NEVER been exercised.

5. THE THREE MOST IMPORTANT THINGS TO FIX, ranked, with your reasoning.

6. THE NEXT TEST I SHOULD RUN, and why that one and not another.

Be blunt. If the run proves less than it looks like it proves, say so.
```

---

# P16 — READING ORDER: DIAGNOSE THE COLUMN BUG

**This is now the most important prompt in the file.**

```
BUG: The extracted MD&A text has its paragraphs in the WRONG ORDER. Two-column
pages are being interleaved. Every quality metric says the document is fine.

PROOF. In dataset/.../JAIN_IRRIGATION.../2025/mda.txt the file OPENS with:

    "formulation, while posing direct threats to agricultural
     productivity, inflation management, and long-term
     economic output."

That is a sentence FRAGMENT starting mid-sentence. Its first half appears far
later in the same file:

    "...the RBI emphasized that frequent weather shocks triggered by
     climate change present persistent challenges to monetary policy"

Second proof: the paragraph beginning "The global financial system displayed
continued resilience..." is spliced BETWEEN two obviously consecutive Jain
Irrigation paragraphs ("At Jain Irrigation Systems Ltd., we recognize..." and
"Our micro-irrigation systems-which include drip and sprinkler solutions...").

DIAGNOSE FIRST. Do not fix anything yet.

Step 1: For the MD&A page range of Jain Irrigation FY2025 (pages 103-124),
print for each page:
   - the column count triage detected
   - the number of text blocks and the number of text lines
   - the widest vertical whitespace gap found, as a FRACTION of page width
   - whether the XY-cut code path was actually entered (add a debug print)
   - the sequence of cuts XY-cut made (vertical/horizontal, at what x or y)

Step 2: Tell me which of these is true:
   (a) triage says 1 column on a visibly 2-column page
       -> column DETECTION is broken
   (b) triage says 2 columns but XY-cut is never called
       -> the code path is not wired
   (c) XY-cut is called but its first cut is horizontal, so the columns
       are never separated
       -> the cut-order logic is wrong
   (d) the gutter threshold is still 5% (academic) not 2.5% (Indian A4)
       -> one number, wrong domain
   (e) gaps are measured on BLOCK boxes not LINE boxes, so a 2-column page
       looks like 2 blocks with no gutter between them
       -> measure at line level

Step 3: Render page 104 of that PDF to PNG at 150 DPI and save it so I can
LOOK at the actual layout with my own eyes.

Show me the output of steps 1-3 and STOP.
```

**Acceptance test:** you see the detected column count and the real page image
side by side. The cause becomes obvious.

**Note:** the most likely answers are (d) and (e), and they often occur
together. `10_STEP8_CLEAN_TEXT.md` documents both: the academic 5% gutter
detected **0 of 28** two-column pages; 2.5% with a 120-bin line-level histogram
detected **24 of 28**.

---

# P17 — ADD AN ORDER-QUALITY METRIC

```
None of our QC metrics can detect wrong reading order. Word count, alpha_ratio,
digit_ratio, long_token_frac and leaks were ALL green on a document whose
paragraphs are scrambled. That is the gap.

Add an order-quality signal to verify.py:

1. ORPHAN STARTS.
   Walk the text paragraph by paragraph. Count a paragraph as an "orphan
   start" if:
      - it begins with a lowercase letter, a comma, or a closing bracket
      - AND the previous paragraph ended with a complete sentence (. ! ?)
   In correctly ordered prose this is near zero. In interleaved text it is
   high.

      orphan_start_frac = orphan_starts / total_paragraphs

2. DANGLING ENDS.
   Count paragraphs that end WITHOUT sentence-final punctuation and are not
   followed by an obvious continuation. Same idea, other direction.

3. Record both in mda.json under qc.

4. Add them to the grading rule:
      orphan_start_frac > threshold  ->  downgrade to medium
      orphan_start_frac > 2x threshold -> low

5. Do NOT invent the threshold. Compute both metrics on all four current
   documents and PRINT them. Then compute them on a paragraph-shuffled version
   of the same text as a synthetic "known bad" control. Show me both numbers
   and propose a threshold with your reasoning. I will pick it.

6. Add a unit test: text with correct order scores near 0; the same text with
   two paragraphs swapped scores clearly higher.

Show me the numbers before you set any threshold.
```

**Acceptance test:** you have one number that separates the good document from
the shuffled control. That number becomes the gate.

**Why this matters more than it looks:** without it, you cannot tell whether
P16's fix worked. You would be judging by eye on four documents. This gives you
a measurement that scales to 40,000.

---

# P18 — QUARANTINE TABLES AND CHARTS OUT OF THE PROSE

```
The extracted mda.txt files contain chart axis labels and table cells dumped as
loose numbers. Examples from the real output:

    350.00 / 300.00 / 250.00 / 283.68 / 200.00 / 267.90 / 276.37 / 279.00
    / 259.71 / 288.78 / 239.73 / 150.00 / 100.00 / 50.00 / 0.00
    / FY 18 / FY 19 / FY 20 / FY 21 / FY 22 / FY 24 / FY 23

    (note FY 24 before FY 23 - the chart labels are themselves out of order)

and:

    Particulars 31st Mar / 31st Mar / Change / absolute / Change / %
    / Employees / benefit / expenses / 3,525.13 / 3,218.21 / 306.92 / 9.54%

looks_like_tables reports FALSE on all four documents, and digit_ratio is
0.021-0.026, because a few hundred characters of table are diluted inside a
15,000-word section. A DOCUMENT-level digit ratio cannot find a table.

Do this:

1. Add PER-BLOCK detection. A text block is a table-or-chart block if:
      - digit ratio within the block > ~0.40
      - AND median words per line within the block < ~6
      - OR the block has 3+ consecutive lines that are numeric-only

2. Move those blocks OUT of mda.txt into a sidecar file:
      mda_blocks.json  ->  [{page, bbox, kind: "table"|"chart",
                             text, digit_ratio, n_lines}]

3. Record in mda.json:
      qc.blocks_quarantined     how many
      qc.words_quarantined      how many words left the prose

4. Recompute n_words on the PROSE ONLY, and say so in the field name or a note.
   Right now n_words counts number-soup as words, which inflates it.

5. Re-run on the four documents. Show me BEFORE and AFTER:
      n_words, digit_ratio, blocks_quarantined, words_quarantined
   and print the first 3 quarantined blocks so I can check you are not
   removing real prose.

Do NOT delete the blocks. Quarantine them. The mandated ratio table is a real
research variable and I want it later.
```

**Acceptance test:** `mda.txt` reads as continuous prose. The ratio table is
still available in `mda_blocks.json`.

**Why:** the downstream work is climate-language analysis. Loose numbers in the
middle of a sentence are pure noise for that, and they distort word counts,
digit ratios and every embedding.

---

# P19 — LINK AND PATH PORTABILITY

```
Two run-blocking problems found while actually running the pipeline.

PROBLEM 1: store.py uses os.symlink with a relative path. It fails with

    ValueError: path is on mount 'D:', start on mount 'C:'

when --out is on a different drive from store/. On Windows, symlinks also
require Developer Mode or admin rights, so even same-drive can fail.

Fix with a three-step fallback, and RECORD which one was used:

    try:    os.link(blob, dest)          # hardlink, free, same volume only
    except OSError:
        try:    os.symlink(blob, dest)   # needs privileges on Windows
        except (OSError, ValueError):
                shutil.copy2(blob, dest) # always works, costs disk

Write the outcome into document.json as  "link_mode": "hardlink"|"symlink"|"copy"
and log a one-line warning on copy. If 40,000 PDFs silently get COPIED instead
of linked, my disk usage doubles and I need to know why.

PROBLEM 2: blob paths in the manifest are relative to the current working
directory, not to the store root:

    "path": "live_store\\blobs\\47\\74\\4774...610.pdf"

This is why the pipeline only runs from arpipe/ with PYTHONPATH=.. set.

Fix:
  - store blob paths RELATIVE TO THE STORE ROOT, forward slashes
        "blobs/47/74/4774...610.pdf"
  - resolve against --root at read time
  - same for mda_path / path in mda.json: relative to the dataset root

Then add a test: run extract from a DIFFERENT working directory and confirm it
works.

Also: mda.json currently has "mda_path": null on a successful extraction, while
the earlier manifest had it populated. Find out why. Then drop the duplicate -
keep "path", delete "mda_path" - and assert the kept field is never null when
ok is true.
```

**Acceptance test:** you can run `extract` from anywhere, output to any drive,
and `document.json` tells you whether it linked or copied.

---

# P2 — BUG 3: SUPPORTERS GATE

```
BUG: KRBL FY2025 was graded "high" confidence with supporters=0. Zero location
methods agreed with the winner. The whole design says agreement between
independent methods IS the confidence measure, so this grading is wrong.

Find the grading function and make the supporter count a HARD GATE:

  supporters >= 2  AND score >= 0.80  AND no leaks   -> high
  supporters == 1  AND score >= 0.60  AND <=1 leak   -> medium
  supporters == 0                                    -> medium at best,
                                                        low if score < 0.70

  Any leak, or identity unproven, or word count out of band -> low, always.

Requirements:
- The supporter count must reach the grading function. If it currently only
  lives in the diag dict, pass it through properly - do not parse it back out
  of a dict of strings.
- Record `supporters` as a top-level field in mda.json, not only inside diag.
- Add a unit test: supporters=0 with score=0.95 must NOT grade high.
- Add a second test: supporters=2, score=0.85, no leaks -> high.

Show me the diff before applying.
```

**Acceptance test:** re-running KRBL FY2025 gives `medium`, not `high`.

---

# P3 — BUG 2: ISIN WAS NEVER EXTRACTED

```
BUG: "isin_found" is null on all four extracted documents. Identity
verification is running on one leg (CIN) instead of two.

I do not yet know WHY. It could be:
  (a) the regex hardcodes "INE" and misses IN9 / INF / INC / IND
  (b) ISIN genuinely is not printed in these reports
  (c) the search only looks inside the MD&A span, and MD&A prose
      rarely quotes the ISIN

Step 1 - DIAGNOSE FIRST, do not fix yet.
  Write a throwaway script that opens the four PDFs in the blob store and
  searches the FULL text of every page for the pattern IN[A-Z0-9]{10}.
  Print: which pages matched, what the match was, and what the page heading
  looked like. Show me the output.

Step 2 - after I have seen that output, fix it:
  - widen the pattern to  \bIN[EF9CDA][0-9A-Z]{9}\b
  - search the front matter (first 20 pages), plus any page whose heading
    matches "Corporate Information" or "General Shareholder Information"
    or "Company Information" - NOT only the MD&A span
  - record where it was found:
        {"isin_found": "...", "isin_found_on_page": 3}
  - if several distinct ISINs appear, record all in "isins_seen": [...]
    and pick the one matching the company master

Step 3 - add a test asserting isin_found is not null for at least 3 of the 4
sample documents.

Do step 1 only. Stop and show me the output.
```

**Note:** a working ISIN check would have caught the DVR bug (P4) by itself.

---

# P4 — BUG 1: JAIN IRRIGATION IS UNDER ITS DVR ISIN

```
BUG: Jain Irrigation is stored as company_id IN9175A01010. That is the
differential-voting-rights line (NSE symbol JISLDVREQS), not the ordinary
equity line INE175A01038. Both lines point at the SAME annual report PDF.

Consequence: two rows per company-year in the final panel, so any regression
double-counts this company. CIN verification does not catch it, because
L29120MH1986PLC042028 is correct for both lines.

Fix in universe.py:

1. When several ISINs share a CIN, or share a normalised company name, collapse
   them into ONE row.
2. Preference order for the primary ISIN:  INE...  then IN9...  then INF...
3. Add columns:
       alternate_isins   pipe-separated, the ones we did not pick
       series_type       ordinary | dvr | partly_paid | other
4. NSE symbols ending in "DVR", "DVREQS" or containing "-RE" are strong
   signals for the non-ordinary line. Use them, but not alone.

Also add to the audit command:
  - assert one row per sha256 in the final manifest
  - assert one row per (cin, fy_end)
  - if either fails, print the offending rows

Add a test using real values:
  input:  INE175A01038 / JISLJALEQS / Jain Irrigation Systems Limited
          IN9175A01010 / JISLDVREQS / Jain Irrigation Systems Limited
  expect: ONE row, company_id = INE175A01038,
          alternate_isins contains IN9175A01010,
          series_type = ordinary

Show me the diff.
```

**Acceptance test:** rebuild `companies.csv`. Jain appears once. Have it print
how many rows the collapse removed — that number is interesting on its own.

---

# P5 — BUG 4: THE TERMINATOR WAS A BODY WORD

```
BUG: KRBL FY2025 recorded terminator_text = "trademarks". That is a word in
body text, not a section heading.

Fix in segment.py. A terminator match must satisfy ALL of:
  - the line is short (<= 80 characters)
  - it is a whole line, not a substring inside a longer sentence
  - it sits in the top third of the page, OR has blank space above it
  - it is Title Case or ALL CAPS, OR is bold / larger than body font
    (on OCR'd pages fall back to the shape tests above)

Then:
- Show me the current terminator list. Remove any entry that is a common body
  word rather than a section heading.
- Record HOW the terminator was matched:
      "terminator_match": {"text": "...", "page": 40, "line_index": 2,
                           "shape_ok": true, "font_signal": "bold"}
- Add a test: "trademarks" mid-paragraph must NOT terminate a span.
  "Report on Corporate Governance" at the top of a page MUST terminate it.

Show me the current terminator list first, before changing anything.
```

---

# P6 — BUG 5: THE TOC METHOD WON WHILE BEING WRONG

```
BUG: On KRBL FY2025 the "toc" method won arbitration with candidate pages
26-28. The true answer was 33-39. On KRBL FY2024 the same method said 53-66
when the answer was 27-33 - off by 26 pages. Refine-and-trim rescued both, but
the method should not have won.

This is the folio-to-physical-page offset solver failing silently.

1. INSTRUMENT IT. Record in mda.json:
     "toc_offset": {"solved": 6, "confidence": 0.72, "samples_used": 31,
                    "modal_agreement": 0.68, "method": "margin_folio_mode"}
   If the solver did not run at all, say so explicitly rather than omitting
   the field.

2. GATE IT. If offset confidence is below a threshold, the toc candidate keeps
   its page range but its arbitration SCORE is cut hard, or it is excluded from
   winning outright. It can still act as a supporter.

3. MEASURE IT. Add a script that prints, per document:
     toc candidate range | final span | page error | offset confidence
   I want to see whether low offset confidence predicts high page error.

Do not tune the threshold by guessing. Set it so that on my four documents the
two bad KRBL cases would not have won, then tell me that threshold is
provisional and must be re-fit on the labelled 300.
```

---

# P7 — MINOR FIXES

```
Three small things:

1. diag.span_words says 515 while n_words says 5261, because span_words is
   computed before refinement. Rename it to "candidate_span_words" so nobody
   reads it as the final count. The pre-refinement number is diagnostically
   useful - keep it, just name it honestly.

2. Add these top-level fields to mda.json so I never have to dig into diag:
       supporters, method_candidates (full list with scores),
       total_pages, mda_page_count, words_per_page

3. Make the ratio-name patterns tolerant. KRBL's MD&A contains all 8 mandated
   ratios but ratio_cues reported 7. The likely miss:

       SEBI says:    "Debtors Turnover"
       KRBL writes:  "Debtor turnover ratio"    <- no 's'

   Make every ratio pattern tolerant of: singular/plural, an optional "ratio"
   suffix, case, hyphen-vs-space, and an optional "(%)".
   Then re-run and confirm KRBL scores 8, not 7.

Show me one diff for all three.
```

---

# P8 — RE-RUN THE FOUR SAMPLES AND COMPARE

```
Re-run extract on the same four documents already in the store.
Do not re-download anything.

Produce a BEFORE / AFTER comparison table:

  company | fy | old_span | new_span | old_conf | new_conf |
  old_method | new_method | old_supporters | new_supporters |
  isin_found | orphan_start_frac | blocks_quarantined

Tell me explicitly:
  - Did KRBL FY2025 move from high to medium?
  - Does Jain Irrigation now appear once instead of twice?
  - Is isin_found populated?
  - Did orphan_start_frac DROP after the reading-order fix?
  - Does KRBL now report 8 ratio_cues instead of 7?
  - Did any span change? If yes, is the new one better or worse - and how do
    you know?

Then print the FIRST 40 LINES of Jain Irrigation FY2025 mda.txt so I can read
it with my own eyes and confirm the paragraphs are now in order.

If anything got WORSE, stop and tell me. Do not paper over it.
```

**Acceptance test:** the Jain FY2025 text no longer opens with the fragment
`"formulation, while posing direct threats to..."`. It opens with a complete
sentence.

---

# P20 — ERA RULES MUST RUN ON THE FULL DOCUMENT

```
FINDING, not a bug. Jain Irrigation FY2024 and FY2025 both report
ratio_cues = 0, while KRBL reports 7. All four are post-FY2020, so all four
should carry the mandated key financial ratios.

I checked the extracted text. Jain's MD&A ends correctly at its Cautionary
Statement, and its financial section has 14 tables - none of which is the
mandated ratio table. So the span is CORRECT and the ratios are genuinely
outside the MD&A, probably in the Board's Report.

Conclusion: ratio_cues is not a reliable ERA signal when computed on the span.

Change:
1. Era rules (the FY>=2020 test from the ratio table, FY>=2023 from BRSR,
   FY>=2016 from Ind AS, etc.) must run over the FULL DOCUMENT text, not the
   extracted span.
2. Keep ratio_cues on the span as a SEGMENTATION signal (S5 body cue) - it is
   still useful there.
3. Record both separately:
       qc.ratio_cues_in_span
       verification.era_signals_in_document

4. Verify on Jain: search the whole PDF for the 8 ratio names and tell me which
   page they are on, if any. If they are in the Board's Report, note it. If
   they are genuinely absent, that is a disclosure finding worth recording in
   the manifest as a note.
```

---

# P10 — WIRE THE BSE MASTER

```
The company master is NSE only: 2,571 companies. BSE has about 5,900 listings,
and the BSE-only tail is roughly 3,000 small and micro caps - exactly the
population most likely to have SCANNED reports, the case we most need to test.

1. Add BSE master ingestion to universe.py. Show me FIRST what the response
   looks like - print the raw JSON structure before writing a parser against
   it. Do not write a parser against a shape you have not seen.

2. Merge with the NSE master on ISIN. A company on both exchanges gets one row
   with exchange = "both".

3. Verify the BSE annual-report endpoint actually works:
       https://api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w?scripcode=NNNNNN
   with Referer and Origin headers set to bseindia.com.
   Try three BSE-only small caps. Show me the raw response. If the shape
   differs from what discover.py expects, fix discover.py to match reality, not
   the other way round.

4. Report: new total company count, how many BSE-only, how many both.
```

**Acceptance test:** you can download one annual report for one BSE-only
company. That is the whole test.

---

# P11 — THE FIRST REAL OCR TEST

```
This is the first real test of the OCR path. Nothing so far has exercised it -
ocr_pages was 0 on all four documents, and 65 pages that NEEDED OCR were
correctly skipped because they fell outside the MD&A spans.

1. From reports.jsonl (or run discover on 30 companies), pick 20 documents
   from FY2010 to FY2014. Spread them: some large cap, some small cap, some
   PSU if you can find one (PSUs are the bilingual case). Prefer BSE-only
   companies for at least 5.

2. Fetch them. Log what happens with:
      - ZIP archives (NSE pre-2016 rows are often .zip)
      - PDFs that need qpdf repair
      - empty-password encryption

3. Run triage on all 20. Give me the page-class table:
      document | total_pages | digital | scanned | hybrid | broken | vector |
      blank | bilingual | frac_needing_ocr

4. Run extract on all 20.

5. Report, honestly:
      - How many spans were found at all?
      - How many OCR pages used per document?
      - Which OCR rung handled each page? Did rung 1 ever fail up to rung 2?
      - Did the degeneracy guard ever fire?
      - How long did a scanned page take, in seconds?
      - orphan_start_frac distribution - is reading order worse on OCR'd text?
      - Confidence tier distribution
      - Anything that crashed

6. Pick the 3 WORST results and show me the extracted TEXT so I can see with my
   own eyes what bad output looks like.

Do not tune anything to make the numbers look better. I want the raw truth.
```

**Expect this to hurt.** FY2010-2014 is where every untested code path lives at
once: ZIPs, broken PDFs, scans, broken-text pages, bilingual PSUs.

---

# P12 — THE LABELLING TOOL

```
I need to hand-label 300 documents with the true MD&A start and end page.
Build me the smallest tool that makes that fast.

- CLI: `python -m arpipe.cli label --pdf <path> --out labels.csv`
- For a given PDF, print for each page of interest: the page number and the
  first 5 non-empty lines
- Show the pipeline's PROPOSED span, so I am correcting not starting fresh
- I type: true_start, true_end, and a reason code
- Reason codes: OK, WRONG_START, WRONG_END, BOTH, NOT_FOUND, NO_MDA_IN_DOC,
                ORDER_SCRAMBLED
- Appends to labels.csv and resumes - never re-ask a document I already did
- Columns: sha256, company_id, cin, fy_end, doc_kind, cap_band, exchange,
           total_pages, proposed_start, proposed_end, true_start, true_end,
           reason_code, labeller, labelled_at

Also add:
  `python -m arpipe.cli sample-for-labelling --n 300 --out to_label.csv`
picking a STRATIFIED sample across:
    era      : 2010-2013 / 2014-2018 / 2019-2025
    cap band : large / mid / small / micro
    doc kind : digital / mixed / scanned
and reporting how many it got per cell, flagging any cell it could not fill.

Plain text in the terminal. No web UI. Speed matters more than looks.
```

**Note the extra reason code:** `ORDER_SCRAMBLED`. Now that we know reading
order can fail on a span with perfectly correct boundaries, the labeller needs
a way to say "right pages, wrong text."

---

# P13 — THE METRIC HARNESS

```
Build the scoring harness that runs the pipeline against labels.csv.

  `python -m arpipe.cli evaluate --labels labels.csv --out eval_report.md`

Metrics, OVERALL and PER STRATUM (era x cap band x doc kind):

  1. exact_start_accuracy
  2. start_within_1_page          the number that decides usability
  3. start_within_2_pages
  4. boundary_iou
  5. Pk
  6. WindowDiff
  7. per_method_precision         one row per S1..S5
  8. supporter_calibration        for supporters=0,1,2,3+ what fraction was
                                  within 1 page. Tells me whether the
                                  agreement bonus is actually calibrated.
  9. tier_precision               of the "high" tier, how many were correct
 10. order_quality                mean orphan_start_frac per stratum, and the
                                  fraction of documents flagged ORDER_SCRAMBLED

Output eval_report.md as markdown tables I can paste into a doc.

Also print, in plain words, the THREE strata with the worst scores and your
guess at why.

Targets:
  born-digital: >= 95% within 1 page
  scanned:      >= 85% within 1 page
  low tier:     <= 6% of documents
  order:        orphan_start_frac below the P17 threshold on >= 95%
```

---

# P14 — THE PREFLIGHT COMMAND

```
Add `python -m arpipe.cli preflight`. It checks everything a long run needs,
BEFORE the run, and refuses to proceed on any failure.

Checks:
  - tesseract on PATH + which languages (warn if 'hin' missing)
  - qpdf on PATH
  - every package in requirements.txt importable, with version
  - free disk where store/ lives (fail under 1 TB; make it a flag)
  - CAN WE HARDLINK? CAN WE SYMLINK? test both, report which, warn if the
    answer is "copy only" because that doubles disk
  - --out and --root are on the SAME volume (warn if not)
  - NSE reachable and cookies obtainable
  - BSE reachable with the right headers
  - write permission on store/ and dataset/
  - if --vlm-url set: endpoint reachable, model responds to a 1-page test
  - GPU present and VRAM, if a GPU rung is configured

Green/red table. Exit non-zero on any red.
Add --fix-hints to print the install command for my OS for anything missing.
```

---

# P15 — WIRE THE CONFIG FILE

```
configs/default.yaml exists and the code ignores it. A config file that lies is
worse than no config file.

1. Make every command load it, precedence:
       CLI flag  >  env var  >  config file  >  code default

2. Every hardcoded threshold in triage.py, segment.py, ocr.py and verify.py
   must come from the config. List every constant you moved.
   This MUST include the gutter fraction and the histogram bin count - those
   are the two numbers behind the reading-order bug.

3. Add --print-config that dumps the FULLY RESOLVED config, showing where each
   value came from.

4. Write the resolved config into the manifest of every run, so any result can
   be reproduced.

5. Add a comment above every threshold saying it is provisional until re-fit
   against the labelled 300.

Do not change any value. Only move them.
```

---

# BONUS PROMPTS — USE ANY TIME

## When something breaks

```
This failed: [paste the error]

Do not fix it yet. First tell me:
  1. What exactly failed, in one sentence
  2. Whether it is a bug in our code, a bad input document, or an environment
     problem
  3. How many of my documents this would affect if it is systematic
  4. Two possible fixes, with the trade-off between them

Then wait for me to pick.
```

## Read the actual output, not the metrics

```
Open dataset/.../mda.txt for [company] [year] and READ IT.

Do not look at the metrics. Read the text as a human would and tell me:
  1. Does the first paragraph start with a complete sentence?
  2. Does any paragraph start mid-sentence, or with a lowercase word?
  3. Do consecutive paragraphs follow each other logically, or does an
     unrelated one interrupt?
  4. Are there loose numbers with no surrounding sentence?
  5. Does it end at a natural end (Cautionary Statement / Disclaimer),
     or mid-thought?
  6. Would you be happy handing this to a researcher?

Quote the specific lines that support each answer.
```

**Use this one often.** It is how the reading-order bug was found — not by any
metric, by reading the text.

## When you want an honest review

```
Read [file].

Play the sceptic. Do not tell me it looks good. Tell me:
  - which functions have no test
  - which thresholds are hardcoded and where they should live
  - which failure modes are swallowed instead of reported
  - which code path has never run on real data
  - what would break first if I ran this on 40,000 documents

Rank them by how much damage they would do at scale.
```

## Before a long run

```
I am about to run [stage] on [N] documents. It will take [T] hours.

Walk through what could go wrong and tell me:
  1. What is not resumable - if it dies at hour 6, what do I lose?
  2. What is not idempotent - what breaks if I run it twice?
  3. What could silently produce wrong output instead of crashing?
  4. What should I log now that I will wish I had logged later?

Then make the smallest changes that fix 1 and 2. Leave 3 and 4 as a list.
```

## After any run

```
Compare dataset/manifest.jsonl against the previous run's manifest.

Tell me:
  - which rows changed and how
  - whether anything got worse
  - whether any new failure reason appeared
  - whether the health bands moved outside:
        words_per_page   691-808
        alpha_ratio      0.788-0.798
        digit_ratio      0.021-0.026
        long_token_frac  0.0

Those bands came from four known-good documents. Treat drift as suspicious.
BUT REMEMBER: all four of those documents passed every band while at least one
had scrambled paragraph order. Green bands are necessary, not sufficient.
```

---

# THINGS TO SAY "NO" TO

| It offers | Say |
|---|---|
| "Let me refactor the whole module while I am here" | No. One change at a time. I need to know what broke what. |
| "I will add a try/except so it does not crash" | No. A swallowed failure is worse than a crash. Make it a `low` tier row with a reason code. |
| "I will tune the threshold so the test passes" | No. Thresholds get re-fit against the labelled 300, not against four documents. |
| "I will skip the documents that fail" | No. Every failure gets a row with a reason. A missing row is invisible. |
| "Let me add a nice web UI for review" | No. A CSV is faster to build and faster to use. |
| "I will write a new OCR engine" | No. Use PaddleOCR-VL / MinerU / Tesseract. |
| "Let me process all 40,000 now to test at scale" | No. Twenty documents from 2010-2014 first. |
| "The metrics all look green, so it is working" | No. Read the text. That is how the reading-order bug was found. |

---

# THE ONE-LINE VERSION

> **Paste P0. Then P1. Then P16 — because the extracted text has its
> paragraphs in the wrong order and every quality metric says it is fine.
> Fix that, add a metric that can see it (P17), quarantine the tables (P18),
> then work the five original bugs. Only then run twenty documents from
> FY2010-2014, because until that runs the OCR ladder has never executed.**
