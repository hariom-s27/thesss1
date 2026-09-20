# 02 — What MD&A Is, And Why It Is Hard To Find

## What is MD&A?

**Management Discussion and Analysis.** It is the section of an annual report
where management explains, in *prose*, what happened and what they expect.

Indian law requires it. **SEBI LODR Regulation 34(2)(e)**, and the contents are
specified in **Schedule V, Part B**. The mandated sub-headings are:

- Industry structure and developments
- Opportunities and threats
- Segment-wise or product-wise performance
- Outlook
- Risks and concerns
- Internal control systems and their adequacy
- Discussion on financial performance
- Material developments in human resources
- (since FY2020) the 8 mandated key financial ratios

**Why we want this section and not the whole report:** the rest of an annual
report is financial statements, auditor's reports, notes, shareholding tables —
numbers and legal boilerplate. Climate *discussion* lives in MD&A. If you score
the whole 319-page report, you dilute the signal with 300 pages of balance sheet.

---

## The size of the problem

Measured on real documents:

```
average annual report:    319 pages
average MD&A section:      13.5 pages
MD&A as % of document:      4.3%
```

**95.7% of every PDF is noise for our purposes.**

This single number drives the entire pipeline design. If MD&A were 80% of the
document, you'd just OCR everything and not care. At 4.3%, OCR-ing everything
means paying for and processing 22 pages of garbage for every 1 page you want.

---

## Why a computer cannot just search for "Management Discussion and Analysis"

This is the question everyone asks first. Here is why it fails.

### Problem 1: the phrase appears many times, mostly in the wrong places

In one real report, `Management Discussion and Analysis` appears on:

- page 3 — the table of contents
- page 12 — the Directors' Report, saying *"a report on MD&A is annexed hereto"*
- page 40 — the actual section
- page 88 — the Corporate Governance report, listing what's included
- page 250 — a cross-reference in the notes

Only **one** of these is the answer. A naive search picks the first, which is the
contents page — the most wrong answer available.

### Problem 2: the heading is written 20 different ways

Real variants we have hit:

```
MANAGEMENT DISCUSSION AND ANALYSIS
Management Discussion & Analysis
Management Discussions and Analysis      <- plural "Discussions"
MANAGEMENT DISCUSSION AND ANALYSIS REPORT
Management Discussion and Analysis Report
ANNEXURE V
MANAGEMENT DISCUSSION AND ANALYSIS       <- split across two lines
Annexure - 1 / Management Discussion and Analysis:
MD&A
```

The `ANNEXURE <roman numeral>` shape matters enormously in India, because
Schedule V material is legally *annexed to the Directors' Report*. So a large
fraction of genuine MD&A sections start under an annexure label, not under a
clean standalone heading.

### Problem 3: many PDFs have no text at all

An Indian annual report from FY2011 is often a **photocopy scanned to PDF**.
There is no text to search. It is a picture of text. You have to run OCR
(optical character recognition) to get characters out — and OCR is slow and
costs money.

We classify every page into five kinds:

| Kind | What it means |
|---|---|
| `digital` | Born-digital, text is right there. Easy. |
| `scanned` | A picture. Needs OCR. |
| `hybrid` | Some pages digital, some scanned, in one file. |
| `broken-text` | Has text, but the text is garbage (mojibake) |
| `vector-text` | Text drawn as shapes. Looks fine, extracts as nothing. |

### Problem 4: two-column layouts scramble the reading order

Most MD&A pages are two columns. If the PDF extractor reads left-to-right across
the whole page instead of down column 1 then down column 2, you get sentences
interleaved from two different paragraphs:

```
GLOBAL ECONOMY

formulation, while posing direct threats to agricultural
productivity, inflation management, and long-term
economic output.
```

...with the start of that sentence appearing 40 lines later. The text *looks*
fine to a word count. It is meaningless to a bigram counter. **This is the
failure that would silently destroy the climate measure** — because
`climate change` as a bigram only counts if those two words are actually adjacent.

### Problem 5: page numbers lie

The contents page says MD&A is on "page 45". But that's the *printed folio
number*. The PDF's page 45 is somewhere else, because the cover, inside cover,
and unnumbered front matter shift everything by 6, or 8, or 11 pages. You have to
solve for the offset.

### Problem 6: the section has to *end* somewhere

Finding the start is half the job. The end is usually where the next section
begins — Corporate Governance Report, Independent Auditor's Report, Business
Responsibility Report. But those headings are also written 20 ways, and some of
them (see file 07) also *open* other sections, which makes them dangerous to use
as an end-marker.

---

## Why this is a real research-engineering problem, not a scripting job

Any one of these is easy to hack around for one document. The difficulty is that
you need a method that works across:

- 4,886 companies, each with its own report designer
- 16 years, across three different regulatory regimes
- born-digital, scanned, hybrid, bilingual (Hindi + English) documents
- with no ground truth, because nobody has labelled Indian MD&A spans before

And you need to **know how often you are wrong**, which turns out to be the
hardest part of all. That is file 06.
