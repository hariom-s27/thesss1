# 06 — The Circular Score: The Most Important File Here

If you read only one file, read this one. It is the thing that would have
destroyed the thesis quietly.

---

## What happened

The pipeline reported:

```
Exact start accuracy   90.0%   (target 85%)  EXCEEDED
Boundary IoU           0.8267
Scrambled              0.0%
ok rate on 194 docs    71.6%
```

Everything looked finished. It wasn't. **The pipeline was grading its own exam.**

---

## The one line that caused it

In `tools/seed_historical_labels.py`:

```python
t_info = known_truth.get(cid, (p_s, p_e, 'OK'))
```

Read it slowly.

- `known_truth` = a small hand-written dictionary of correct answers (~20 companies)
- `cid` = the company we're labelling
- `.get(cid, default)` = "look it up; if it's not there, use the default"
- the default is `(p_s, p_e, 'OK')` — and **`p_s`, `p_e` are the pipeline's own
  predicted start and end pages**

So: for every company nobody had hand-checked, the "correct answer" was defined
as *whatever the pipeline said*. Those documents **could not fail.** They were
scored correct by construction.

### The analogy

A student sits an exam. The teacher has personally checked 20 questions. For
every other question, the marking rule is: *"whatever the student wrote is the
right answer."*

The student scores 90%. The 90% tells you nothing about the student.

---

## It was worse than one bad line

Three layers of contamination, stacked:

### Layer 1 — the auto-pass default (above)

174 of 194 documents auto-passed.

### Layer 2 — the hand-written dictionary wasn't all hand-written

Of the ~20 `known_truth` entries, when we added an honest `verified_by` column:

```
read_pdf         6    <- someone actually opened the PDF and read it
unknown         12    <- provenance not recorded
copied_from_run  2    <- the "truth" was copied from pipeline output
```

So 14 of 20 "ground truth" entries were not verified ground truth.

### Layer 3 — train-on-test

Of the 6 genuinely read documents, **2 are the exact documents that rules were
written against**:

- **SAIL FY2011** — the document P27's `is_cross_reference_pointer` was built for
- **KRBL FY2014** — the document P25's outline prose-validation was built for

A fix always passes on the document it was written for. That's not evidence.

**Honest evaluable count: 4 documents.** (The evaluation harness found 6 rows it
could score; 2 of those are contaminated.)

---

## Why this is dangerous rather than just embarrassing

Go back to file 01. The MD&A text feeds a **bigram-counting climate measure**.

If the span is wrong — say it starts 3 pages late, or includes 5 pages of the
Directors' Report — the measure doesn't crash. It doesn't return an error. It
returns a **clean, precise, plausible CCExposure score that is wrong**.

You then run regressions on 78,000 of those. You get significant coefficients.
You write a thesis. And the underlying text was the wrong section.

There is no downstream check that catches this. **The only place it can be caught
is here.** That is why the scoreboard matters more than the code.

---

## The one metric that was never circular

```
Order scrambled: 0.0%
```

This one is real. Here's why.

`orphan_start_frac` is computed from **the shape of the text itself** — what
fraction of paragraphs begin mid-sentence (lowercase, or a comma, or an open
bracket) when the previous paragraph had already closed properly. It never looks
at a label. There is nothing for it to be circular *with*.

```
clean documents:      0.000 - 0.004
shredded documents:   0.064 - 0.098
threshold:            0.03        <- sits in empty space, ~8x headroom
```

Keep this metric prominent in the thesis. It is the one number that was honest
from the start, and it happens to measure the failure that would most damage the
climate score (scrambled columns break bigram adjacency).

---

## A moment worth recording: the threshold that wasn't re-fitted

At one point the suggestion came up to re-fit `ORPHAN_START_FRAC_MAX` from 0.03
to 3× higher, so that one document (Jain FY2025) would stay graded `medium`
instead of dropping to `low`.

That was declined, and the reason matters more than the decision:

> The option was proposed **because it produced a desired grade.** That is the
> forbidden move. You do not move a threshold to make a document pass; you move
> a threshold because the data says the old value was in the wrong place.

0.03 sits in empty space between the clean cluster and the shredded cluster. It
was correct. It stayed.

**This is the standard the whole project should be held to**, and it is worth
saying in the thesis methodology section explicitly.

---

## What was done about it

Three prompts, all run:

**P31 — remove the auto-pass.** Unlabelled documents now get
`label_status = UNLABELLED` and `true_start = null`. They are *excluded* from
scoring — they count as neither pass nor fail. Added the `verified_by` column and
filled it in honestly.

Result: 194 → 6 evaluable documents. Accuracy 90.0% → **83.3%**.

**P32 — build the hold-out split before labelling more.** `to_label.csv` shuffled
with a recorded seed, split 2/3 fit / 1/3 holdout, **stratified by (era, cap band,
doc kind)** so both halves have the same mix of hard and easy documents.

This one caught something I hadn't anticipated. 17 of the 20 already-labelled P11
documents were *also* sitting in `to_label.csv` — because `to_label.csv` samples
from the same store and has no idea what's already labelled. In the first version
of the split, 5 already-labelled documents, including contaminated SAIL FY2011,
**leaked into the holdout queue.** That was caught and corrected, and the fix is
documented in `eval_protocol.md`. A holdout containing a document you tuned
against is not a holdout.

**P33 — audit every rule added since P25 for false positives.** Measure only, no
behaviour changed. It found two real bugs. That's file 07.

---

## The honest sentence for a supervisor

> Span-location correctness is currently validated on 4 uncontaminated documents
> at 83.3% exact-start accuracy — a sample too small to draw conclusions from.
> Reading-order quality is validated across all 194 documents at 0% scrambled,
> measured from text structure and independent of labels. A stratified hold-out
> protocol is in place; threshold calibration is deliberately blocked until 300
> documents are hand-labelled.

That sentence survives a viva. "90% accuracy" would not have.
