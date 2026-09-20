# 09 — Going From 20 Files To 10,000 (And 78,000)

You asked how we take this to ~10k files. Here is the honest answer: **the code
mostly scales; the things that break are storage, the OCR path, and trust.**

---

## The arithmetic

| Scale | Documents | Pages (@319 avg) | MD&A pages (@13.5) |
|---|---|---|---|
| Today | 194 | ~62,000 | ~2,600 |
| Your 10k target | 10,000 | ~3.2M | ~135,000 |
| Full universe | ~78,000 | ~25M | ~1.05M |

The "locate first, OCR second" design (file 08 §1) is what makes the right-hand
column affordable. Everything below assumes it.

---

## What scales fine

**Discovery.** Network-bound, resumable with `--resume`, no span logic. It is
already running in the background across all 4,886 companies and it is safe to
leave running — it produces no spans, so it cannot produce wrong spans, and its
output (the URL index) is needed no matter how the span logic ends up.

**Fetch.** Rate-limited per host, SHA-256 dedup with hardlinks. The dedup matters
more at scale than it looks: the same PDF filed on both NSE and BSE stores once.

**Triage.** Pure object-model read, no rendering. Fast and linear.

**Extract (digital).** Linear in pages. The happy path.

---

## What breaks, in order of severity

### 1. Disk — blocking right now

```
available:  81 GB
needed:     ~1 TB
```

At ~2–15 MB per annual report PDF, 78,000 documents is 300 GB–1 TB before any
intermediate artefacts. **This is the current hard blocker on `fetch`.**

Options, cheapest first:

| Option | Notes |
|---|---|
| **Stream-and-discard** | Fetch → triage → extract → keep MD&A pages + hashes, delete the source PDF | Cheapest. But you lose re-processability — if you fix a bug later, you must re-download everything. |
| **Keep span pages only** | Render/keep the 13.5 located pages, drop the rest | Middle ground. Re-processable for span *refinement*, not for span *relocation*. |
| **External drive** | ~1 TB | Simplest. Slow I/O. |
| **Cloud object storage** | S3/GCS at ~$20/TB/month | Best if the crawl runs over weeks |

**Recommendation: keep span pages + full provenance, discard source PDFs after
extraction, but keep the SHA-256 and URL so any document can be re-fetched
on demand.** That gives re-processability without 1 TB resident.

This decision is worth making *before* the crawl, not during — changing it
halfway means two incompatible stores.

### 2. OCR has never run — the real risk

File 05 covers this. At 20 documents you can ignore it. At 10,000 you cannot:
roughly the entire FY2010–2015 band is scanned or hybrid.

And the failure is **silent**: missing Tesseract returns an empty page, which
surfaces much later as `mda_not_located`. At scale that looks like "these old
documents just don't have MD&A" rather than "OCR isn't installed".

**Before any large crawl:** install `tesseract` + `tesseract-ocr-hin`, `qpdf`,
Ghostscript, and run end-to-end on the scanned/hybrid/bilingual fixtures.
Then add a **loud** startup check — if OCR is needed and the binary is missing,
fail immediately rather than silently returning empty pages.

### 3. Trust does not scale — the real bottleneck

This is the one that matters most and is easiest to forget.

At 20 documents you can read every output. At 10,000 you cannot read any of them.
**Your only contact with correctness is the metrics** — which is exactly why file
06 matters. A pipeline you cannot verify is a pipeline whose errors you will
publish.

What you need before the crawl, not after:

- 300 hand labels, split fit/holdout (in progress: 20 done, 137 queued)
- Thresholds fitted on the fit set only
- One holdout score, recorded, not tuned against
- `orphan_start_frac` monitored on **every** document as a continuous canary

### 4. Rules interacting at scale

P33 found a rule fitted to one document breaking two others. At 194 documents
that's findable. At 10,000, with 16+ rules, interactions multiply.

**Mitigation: make P33 a standing job, not a one-off.** Every time a rule is
added, re-run the per-rule fire-count sweep and diff it against the previous run.
A rule whose fire count jumps from 12 to 900 has changed meaning.

### 5. Long-tail document weirdness

At 194 documents / 36 companies you have seen a narrow slice. At 10,000 you will
meet: password-protected PDFs, 0-byte downloads, HTML pages served as `.pdf`,
reports for the wrong year, merged multi-year filings, Tamil/Gujarati/Bengali
sections, 2,000-page conglomerate reports, and files that crash the parser.

**Design rule: every failure must be recorded and skipped, never fatal.** A crawl
that dies on document 4,312 after six hours is worse than one that records 200
failures and finishes.

---

## Suggested staged rollout

Do not go 194 → 78,000. Go in steps where each step can still be inspected.

| Stage | N | Purpose | Gate to pass |
|---|---|---|---|
| **A** | 300 | Hand-label, fit thresholds, score holdout once | Holdout accuracy known and stated |
| **B** | 1,000 | First real crawl. Stratified across era/cap/kind. | Failure taxonomy stable; no new failure class in the last 200 |
| **C** | 10,000 | Your target. | `orphan_start_frac` distribution unchanged vs Stage B |
| **D** | 78,000 | Full universe | Nothing new in C |

**The gate between B and C is the important one.** If Stage B throws up a failure
class you've never seen, Stage C will throw up 10× as many and you'll be
debugging with no ability to read the outputs.

---

## Cost at each stage (OCR only)

Assuming ~13.5 MD&A pages per document, and that ~25% of pages need OCR
(higher in early years, near zero post-2018):

| Stage | Docs | OCR pages | Tesseract | PaddleOCR (~$190/M) | DocAI (~$1,500/M) |
|---|---|---|---|---|---|
| A | 300 | ~1,000 | free | $0.19 | $1.50 |
| B | 1,000 | ~3,400 | free | $0.65 | $5 |
| C | 10,000 | ~34,000 | free | $6.50 | $51 |
| D | 78,000 | ~263,000 | free | $50 | $395 |

**OCR cost is not the constraint.** Even routing everything to DocAI, the full
universe is under $400. Disk, compute time, and your attention are the real costs.

This is worth internalising: the ladder exists to protect *quality* (escalate
when Tesseract does badly), not primarily to save money. The money was never the
problem once you decided to locate before OCR-ing.

---

## Wall-clock estimate

Dominated by polite rate limiting, not compute.

- Discovery: already running, days
- Fetch at ~1 doc/sec/host with politeness: ~78,000 sec ≈ **22 hours minimum**,
  realistically several days with retries and multiple hosts
- Triage + extract: ~2–10 sec/doc single-threaded → parallelise across cores
- OCR: the slow part, but only 13.5 pages/doc

**Plan for a full crawl in weeks, not hours**, and make it fully resumable. It
already is (`--resume`), which was a good early decision.
