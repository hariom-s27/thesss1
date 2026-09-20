# 01 — What We Are Actually Building

## The research question, in one sentence

> Indian companies talk about climate risk in their annual reports.
> Can we measure *how much*, for every listed company, for 15 years?

To answer that you need two things. You have one. You are building the other.

---

## Thing 1: the measuring instrument (repo `thesis`) — DONE

This repo reproduces **CCExposure** from Sautner, van Lent, Vilkov & Zhang (2023,
*Journal of Finance*).

**How the measure works, simply:**

You have a dictionary of climate-related two-word phrases ("bigrams") — things
like `renewable energy`, `carbon emission`, `climate change`. You take a
transcript. You count how many of those phrases appear. You divide by the total
number of phrases.

```
CCExposure = (climate bigrams found) / (total bigrams in document)
```

That's it. That's the core. Everything else in the repo is *checking that this
simple thing is trustworthy*:

| Phase | What it checks |
|---|---|
| 1 | Does our number match the authors' published number? (validated against ExxonMobil) |
| 2 | Sentiment (positive/negative) and Risk framing |
| 3–4 | TF-IDF weighting — do rare climate words matter more? |
| 5 | Replicate the authors' own validation tests |
| 6 | Run their validation logic on *our* data |
| 7 | Placebo test, split-half reliability, Paris Agreement 2015 event study |
| 8 | Bootstrap confidence intervals, permutation test |
| audit | Show exactly which bigrams matched — open the black box |

The **placebo test** and the **permutation test** are the important ones. A
placebo test scores documents that should have *no* climate signal; if they score
high, your measure is picking up noise. A permutation test scrambles word order;
if the score doesn't drop, your measure isn't reading language, it's reading
word-frequency. These are the tests that make a measure defensible in a viva.

**Status: this half works and is validated.**

---

## Thing 2: the data supply (repo `arpipe`) — 80% built

The measure above eats **text**. For US companies, earnings-call transcripts are
easy to buy. For Indian companies, they are not — and the richer climate
discussion is in **annual reports**, specifically the **MD&A section**.

So ARPipe's job:

```
4,886 Indian listed companies
        x
16 years (FY2010 - FY2025)
        =
~78,000 annual report PDFs
        |
        v
   extract MD&A from each
        |
        v
   a clean text corpus
        |
        v
   feed it to the CCExposure measure
```

**That is the whole thesis contribution.** Nobody has this corpus. Building it
correctly *is* the novel work.

---

## Why the two halves need each other

- Without `thesis`, ARPipe is just a PDF scraper — no research question.
- Without `arpipe`, `thesis` is a reproduction of someone else's US paper — no
  new contribution.

Together: *a validated climate-exposure measure, applied to a new corpus that
did not previously exist, for a market (India) where climate-physical-risk
exposure is high and disclosure research is thin.*

---

## Simple analogy

Think of it like a blood test.

- **`thesis`** is the **test kit**. You've bought it, calibrated it against a
  known sample, and proved it gives the right reading.
- **`arpipe`** is the **blood draw**. You need to collect 78,000 clean samples.
  If the samples are contaminated — wrong section of the report, scrambled text,
  missing pages — the test kit gives you a confident, precise, **wrong** number.

The test kit is finished. You are still building the needle.

And this is exactly why the ARPipe accuracy number matters so much: a bad MD&A
extraction doesn't make the measure *fail loudly*. It makes it produce a clean,
plausible, publishable number that is wrong. That is the worst kind of error.
