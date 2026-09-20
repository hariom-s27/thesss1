# 03 — How The Pipeline Works, Step By Step

Ten steps. Each one in plain words, then what it actually does.

```
  1 universe    get the list of companies
  2 discover    find the PDF links
  3 fetch       download the PDFs
  4 triage      classify every page (digital? scanned?)
  5 textlayer   read the free text out of digital pages
  6 segment     FIND THE MD&A  <- the hard part
  7 ocr         OCR only the pages inside the span
  8 clean       fix the text
  9 verify      check it's the right company, right year, not scrambled
 10 store       write it down with provenance
```

The **big idea** of the whole design is in the order of steps 6 and 7:

> **Locate the MD&A *before* OCR. Then OCR only the 13 pages you need, not 319.**

That one decision is what makes 78,000 documents affordable instead of
impossible. Everything else follows from it.

---

## Step 1 — `universe`: who are the companies?

Pull the NSE equity master list. Chain symbol changes (companies rename; a 2011
filing is under the old symbol). Output: `companies.csv`.

**Status:** works. 2,568 companies pulled live. BSE-only companies (~3,000) are
not reachable yet — see file 05.

## Step 2 — `discover`: where are the PDFs?

For each company and year, ask NSE's annual-report API, and `screener.in` as a
backup, for the PDF URL. Output: a manifest of candidate links.

**Status:** works for NSE + screener. BSE source is inert (no scrip codes).

## Step 3 — `fetch`: download

Download politely (rate-limited per host). Unwrap ZIPs. Repair broken PDFs with
`qpdf`. Deduplicate by SHA-256 — the same PDF filed on two exchanges is stored
once and hardlinked.

**Status:** works. Dedup confirmed.

## Step 4 — `triage`: classify every page

Read the PDF's internal structure (no rendering — fast). For each page decide:
digital / scanned / hybrid / broken-text / vector-text. Count characters per
page, image area fraction, mojibake ratio.

**Why page-level and not document-level:** a 319-page report is routinely 300
digital pages plus 19 scanned inserts. Calling the whole document "scanned"
would send it all to OCR for no reason. Calling it "digital" would silently lose
the inserts.

**Status:** works. 1,275 pages profiled in a test run; 5.1% flagged for OCR.

## Step 5 — `textlayer`: pull the free text

For digital pages, get the text out — with correct reading order. This is where
`_column_cut` lives (the two-column fix). Uses an XY-cut: find the vertical
white gutter, split the page into columns, read each column top to bottom.

**Key tuning:** gutter threshold is **2.5%** of page width, not the academic
default of 5%. Indian A4 reports use an 18–30pt gutter on a 595pt page. And we
measure gaps on **line** boxes, not block boxes — block boxes hide the gutter.

## Step 6 — `segment`: find the MD&A

Five independent strategies, then an arbiter picks. **This is the whole game.**
See file 04.

## Step 7 — `ocr`: read the pictures

Only for pages inside the located span. A three-rung ladder — cheapest first,
escalate only if quality is bad. See file 08 for the cost comparison.

**Status:** code exists, but Tesseract isn't installed on the dev machine, so
this path has never run. Biggest untested area.

## Step 8 — `clean`: fix the text

De-hyphenate across line breaks, drop repeated running headers/footers, remove
page numbers, normalise whitespace. Quarantine tables and chart labels into a
separate `mda_blocks.json` so they don't pollute the prose.

**Why quarantine tables:** a financial table flattened into text produces things
like `Revenue 4,521 3,908 15.7` — which adds nonsense bigrams to the climate
score.

## Step 9 — `verify`: is this right?

Three separate checks:

1. **Right company?** Match CIN (21-char structured ID), ISIN (`INE`+9), and
   fuzzy company name. Score ≥88 accept, 72–88 flag, <72 reject.
2. **Right year?** Weighted evidence from era rules — a ratio table means
   FY≥2020, BRSR means FY≥2023, Ind AS means FY≥2016, CSR/Companies Act 2013
   means FY≥2015, BRR means FY≥2013. Run over the **whole document**, not the
   span.
3. **Is the text readable?** `orphan_start_frac` — the fraction of paragraphs
   that begin mid-sentence (lowercase, or a comma, or an open bracket) when the
   previous paragraph had already closed. High value = scrambled reading order.

**`orphan_start_frac` is the most important metric in the project** and file 06
explains why: it is the only one that isn't circular.

## Step 10 — `store`: write it down

Per document: `mda.txt` (the prose), `mda.json` (the span + method + confidence),
`document.json` (full provenance — source URL, SHA-256, page classes, which
strategy won, what OCR rung was used). Plus a manifest row.

**Why so much provenance:** in a viva, "where did this number come from" must be
answerable for any single document, three months later.
