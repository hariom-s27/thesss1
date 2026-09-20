# 26 — The Measurement Is Circular

**Read this before you trust 90.0% / 0.8267 IoU / 0.0% scrambled.**

Short version, in plain words:

> The pipeline is being graded against answers that the pipeline itself wrote.
> So the score mostly measures whether the pipeline agrees with itself.
> It does not yet measure whether the pipeline is right.

The engineering work in P25–P30 is good. The bugs found were real bugs. The fixes
look correct. **The problem is not the code. The problem is the scoreboard.**

---

## 1. What is actually wrong

### 1.1 The label file fills in its own answers

In `tools/seed_historical_labels.py`:

```python
t_info = known_truth.get(cid, (p_s, p_e, 'OK'))
t_s, t_e, r_code = t_info
```

Read that line slowly.

- `known_truth` is a small hand-written dictionary (about 20 companies).
- `cid` is the company being labelled.
- If the company **is not** in that dictionary, the "truth" becomes
  `(p_s, p_e, 'OK')` — and `p_s`, `p_e` are **the pipeline's own predicted start
  and end pages**.

So for every document that nobody hand-checked, the ground truth is defined as
"whatever the pipeline said." Those documents can never be wrong. They are
scored as correct by construction.

**This is the single line that makes the headline number meaningless.**

Think of it as a student marking their own exam: any question the teacher did
not personally check, the student writes "correct" next to.

### 1.2 The hand-written dictionary is smaller than it looks

Of the ~20 entries in `known_truth`, only about **6** were independently verified
by actually opening the PDF and reading it:

| Company | Span | Verified how |
|---|---|---|
| KRBL | 8–21 | read the PDF |
| Inter State Oil | 15 | read the PDF |
| SAIL | 29–36 | read the PDF |
| Modern Steels | 9–10 | read the PDF |
| (two entries) | `NO_MDA_IN_DOC` | read the PDF |

The other ~14 entries were not read by hand. At least two of them
(Coal India 120–137, Gujarat Cotex 13–13) are visibly identical to what the
pipeline predicted earlier — which means they were probably copied from pipeline
output into the "truth" dictionary. That is the same circularity, just done by
hand instead of by a default argument.

### 1.3 Four of the six verified ones are the training set

P25 (outline validation) and P27 (cross-reference suppression) were **developed
against** these exact documents. You looked at them, saw what broke, wrote a fix
for what you saw, and the fix now passes on them.

That is called **train-on-test**. A fix always passes on the document it was
written for. It tells you nothing about the next 4,886 companies.

So the honest count is:

- Documents that can grade the pipeline **and** were not used to build it: **2**.
- Two documents is not an evaluation set. It is an anecdote.

### 1.4 The 174 unmeasured documents

`live_dataset` holds **194** documents. About **20** are evaluable (and really
only 2 are clean). The reported **71.6% ok-rate** covers documents where 174 of
them have no independent answer to compare against.

That 71.6% is the pipeline's self-reported confidence, not its accuracy. They are
different things. A confident wrong span is still a wrong span.

---

## 2. The second problem: single-document patterns

Since P25, roughly **ten** new patterns, regexes and thresholds were added. Each
one was derived from **one** document that was misbehaving.

A rule fitted to one document does two things:

1. It fixes that document. (You can see this.)
2. It may break documents you have never looked at. (You **cannot** see this,
   because there is no set of documents capable of showing a false positive.)

Right now the project has no way to detect (2). Every new rule is a one-way bet.

### 2.1 The riskiest change

`is_cross_reference_pointer` was loosened to reject pointers
*"unconditionally... without arbitrary word-count restrictions."*

That guard is what protects Jain FY2025's legitimate opening:

```
ANNEXURE V
MANAGEMENT DISCUSSION AND ANALYSIS
```

A real MD&A start in Indian annual reports very often sits under an
`ANNEXURE <roman numeral>` label, because Schedule V material is attached as an
annexure to the Directors' Report. If the un-restricted rule now treats that as a
pointer rather than a start, the pipeline silently skips the real MD&A and lands
somewhere later. Nothing in the metrics would show this, because Jain's "truth"
is either absent or pipeline-derived.

### 2.2 The second riskiest change

`"To the Members of"` was added as a **terminator** heading.

But `"To the Members of"` is also the standard **opening line of the Directors'
Report** and of the **Independent Auditor's Report**. In many Indian annual
reports the Directors' Report comes *before* MD&A and the MD&A is annexed to it.
If that string appears on a page inside or just before the span, the end page
gets cut early — or the start gets pushed.

A string that both opens a section and ends another is a bad terminator. It needs
a positional condition (only terminate if it appears *after* the start page and
after at least N pages of body text), not a bare match.

---

## 3. What is fine — do not undo these

Two things deserve credit, and I want to be clear that this doc is not a blanket
"everything is broken."

1. **P28 (mojibake) was measured honestly.** You measured 52–67% mojibake ratios,
   0% false positives, found the cause (Type 1 subset fonts with no `/ToUnicode`
   CMap), and concluded **"don't change the threshold."** That is exactly the
   right shape of work. It is the model for how the other ten patterns should
   have been validated.

2. **The discovery crawl running in the background is harmless.** It is
   network-only. It produces no spans, so it cannot produce wrong spans. Its
   output (the URL index) is needed regardless of how the span logic ends up.
   **Leave it running.** The thing that must stay gated is `fetch` → `extract`,
   and that is already gated by the disk problem anyway.

---

## 4. What to do, in order

The rule for the next phase is one sentence:

> **No threshold is re-fitted, and no full extract is run, until there exists a
> set of hand-read documents that the pipeline has never been tuned against.**

Concretely:

1. **P31** — stop the label file from inventing answers (below).
2. **P32** — set up the hold-out split before labelling more (below).
3. **P33** — audit the ten single-document patterns for false positives (below).
4. Then label. Then fit on the fit-set. Then report on the hold-out. Then crawl.

---

## 5. The prompts

Copy these into Claude Code one at a time, in order. Each is one job.

---

### P31 — Remove the self-answering default from label seeding

```
In tools/seed_historical_labels.py there is this line:

    t_info = known_truth.get(cid, (p_s, p_e, 'OK'))

This defaults the ground truth to the pipeline's own prediction for any
company not in the known_truth dict. That makes every unlabelled document
score as correct by construction, which makes the headline accuracy number
meaningless.

Do these four things. Do not change any span-finding logic.

1. Remove the fallback. If cid is not in known_truth, the row must be
   written with truth_start = null, truth_end = null, and a new column
   label_status = "UNLABELLED". It must NOT be written with the pipeline's
   prediction.

2. Add a column `verified_by` to every known_truth entry, with one of
   exactly these values:
     - "read_pdf"        = a human opened the PDF and read the pages
     - "copied_from_run" = the span was taken from pipeline output
     - "unknown"         = provenance not recorded
   Go through the ~20 existing entries and set this honestly. If you
   cannot establish that a PDF was read by hand, the value is "unknown",
   not "read_pdf". Do not guess upward.

3. Change the evaluation harness (arpipe evaluate) so that rows with
   label_status = "UNLABELLED", or verified_by != "read_pdf", are
   EXCLUDED from accuracy, IoU and scrambled-rate. They must not count
   as passes and must not count as failures. They are simply not scored.

4. Re-run the evaluation and print a table with these rows:
     - total documents in live_dataset
     - documents with label_status = LABELLED
     - of those, documents with verified_by = "read_pdf"
     - of those, documents that were ALSO used to develop a fix
       (i.e. appear in the P25 or P27 development notes)
     - documents eligible for an honest score
       (= read_pdf AND not used in development)
   Then print exact-start accuracy, IoU and scrambled-rate computed over
   ONLY that last group, with the denominator shown explicitly.

Report the new numbers. Do not adjust anything to improve them. The
expected outcome is that the denominator is very small — that is the
correct result, not a bug. Tell me the number.
```

---

### P32 — Impose a hold-out protocol before labelling continues

```
Set up a train/test split for the labelling effort, before more labels are
created, so it cannot be contaminated later.

1. Take to_label.csv. Shuffle it with a FIXED seed (use seed 20260911 and
   record it in the file). Write two files:
     - labels_fit.csv   = first 2/3 of the shuffled rows
     - labels_holdout.csv = last 1/3

2. Write configs/eval_protocol.md stating, in plain language:
     - labels_fit.csv is the ONLY set that may be looked at when writing
       a new rule, choosing a threshold, or debugging a failure.
     - labels_holdout.csv may be scored but MUST NOT be inspected
       document-by-document. If a holdout document fails, you may record
       that it failed. You may not open it to find out why and then write
       a rule for it. Doing so moves it permanently into labels_fit.csv.
     - Any document used to develop a fix is moved to labels_fit.csv and
       marked contaminated = true, permanently.

3. Add a command `arpipe evaluate --split fit|holdout|both`. Default is
   `fit`. Scoring holdout must print a one-line warning naming the date
   and the git commit, and append that line to eval_holdout_log.csv, so
   there is a permanent record of how many times the holdout has been
   looked at. (A holdout scored fifty times is no longer a holdout.)

4. Move the currently-verified documents into the correct bucket:
   the four used to develop P25/P27 go to labels_fit.csv with
   contaminated = true.

Do not label anything yet. Just build the split and the protocol.
Show me the two file row counts and eval_protocol.md.
```

---

### P33 — False-positive audit of the single-document patterns

```
Since P25, roughly ten patterns / regexes / thresholds were added, each
derived from one document. None has been checked for false positives,
because no set of documents exists that could show one.

Do a measure-only audit. Change NO behaviour in this prompt.

1. List every pattern, regex, threshold or heuristic added to
   arpipe/segment.py and arpipe/verify.py since P25. For each, record in
   a table: the rule, the file and line, the single document it was
   derived from, and what it rejects or accepts.

2. For each rule, run it across ALL 194 documents in live_dataset and
   count how many times it fires. Print rule name, fire count, and the
   list of company IDs it fired on.

3. Flag for manual review any rule that fires on more than 10% of
   documents. A rule written for one weird document that fires on 20+
   documents is either a much more general rule than intended, or a
   false-positive generator. Either way I need to know.

4. Two specific rules need extra treatment:

   (a) is_cross_reference_pointer, now unconditional. Print every
       document where it rejected a candidate heading, with the heading
       text and page number. I specifically want to see whether it
       rejects headings of the form:
           ANNEXURE <roman numeral>
           MANAGEMENT DISCUSSION AND ANALYSIS
       because that is a legitimate MD&A start in Indian annual reports
       (Schedule V material is annexed to the Directors' Report), and
       Jain FY2025 is exactly this shape.

   (b) "To the Members of" as a terminator. This string is also the
       standard opening of the Directors' Report and of the Independent
       Auditor's Report. Print every document where it fired as a
       terminator, with the page number and the predicted start page.
       Flag any case where it fired within 3 pages of the start page.

5. Write the findings to reports/pattern_audit.md. Recommend nothing yet.
   Just show me the counts and the two lists.
```

---

## 6. What the corrected picture probably looks like

I expect P31 to report something in this range:

| Number | Reported now | Probable honest value |
|---|---|---|
| Exact start accuracy | 90.0% | unknown, denominator ≈ 2 |
| IoU | 0.8267 | unknown, denominator ≈ 2 |
| Scrambled rate | 0.0% | probably genuinely low — this one is measured on text shape, not on labels, so it is the most trustworthy of the three |
| ok-rate on live_dataset | 71.6% | this is a **confidence** rate, not accuracy — rename it |

Note that **scrambled-rate is the one honest metric you already have.**
`orphan_start_frac` is computed from the text itself, not from a label, so it
cannot be circular. 0.0% scrambled is a real result. Keep that metric prominent.

The rename in the last row matters. `ok_rate` reads like accuracy in every table
it appears in. Call it `high_confidence_rate` so nobody — including you in three
months — reads it as correctness.

---

## 7. The honest status line for the thesis

If you need one sentence for a supervisor meeting:

> Span-location correctness is currently **unvalidated**: the evaluation set is
> partly pipeline-generated and partly the same documents the rules were written
> against. Reading-order quality **is** validated (0% scrambled across 194
> documents, measured from text structure, independent of labels). A hold-out
> labelling protocol is being put in place before thresholds are calibrated.

That is a better sentence than "90% accuracy," because it is true, and because
nobody can take it apart in the viva.

---

## 8. Order of operations from here

```
1. P31   remove self-answering labels        (small, do today)
2. P32   hold-out split + protocol           (small, do today)
3. P33   false-positive audit                (measure only, no changes)
4.       read P33 output, decide which of the ten rules to tighten
5.       label 300 documents by hand into labels_fit / labels_holdout
6.       re-fit thresholds against labels_fit ONLY
7.       score labels_holdout ONCE, record it, do not tune afterwards
8.       resolve the 81 GB vs ~1 TB disk problem
9.       full fetch -> triage -> extract -> audit
```

Steps 1–3 are hours, not days. Step 5 is the expensive one, and it is the one
that actually buys you a thesis-defensible number.

**Leave the discovery crawl running throughout.** It blocks nothing and it is
needed at step 9.
