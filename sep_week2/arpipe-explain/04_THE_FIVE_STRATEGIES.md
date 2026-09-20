# 04 — The Five Ways We Look For MD&A

## Why five and not one

Because no single method works on all documents, and — more importantly —
**because agreement between independent methods is how we measure confidence.**

If one method says "page 40" we have no idea if it's right. If three methods that
work in completely different ways all independently say "page 40", it is almost
certainly page 40. We call the count of agreeing methods `supporters`.

> `supporters` is not a nice-to-have. It is the confidence measure.

This is the same logic as triangulation in surveying: one bearing gives you a
line, three bearings give you a point.

---

## S1 — Outline / bookmarks

**Idea:** many PDFs have a built-in navigation tree (the sidebar bookmarks).
If one says "Management Discussion and Analysis" and points at page 40, believe it.

**Pros:** exact, free, instant.
**Cons:** many Indian reports have no outline, or have a decorative one that
points at a section *divider* page — a page with a title and a photo and no prose.

**The P25 fix:** don't trust the outline blindly. Validate that the target page
actually contains prose (≥120 words, alpha ratio 0.60–0.92, body cues present).
If it's a divider, walk forward up to 8 pages to find the real start.

**Measured:** fires on 12 of 194 documents (6.2%); walked forward on 4.

---

## S2 — Contents page

**Idea:** find the table of contents, read "Management Discussion and Analysis ... 45".

**Cons:** 45 is the *printed folio* number, not the PDF page. You must solve for
the offset — which you do by taking several contents entries, finding those
pages, and looking for a consistent shift.

**Pros:** works even when there are no bookmarks.
**Cons:** fails when front matter is inconsistently numbered, and section-divider
pages are common targets here too.

---

## S3 — Typographic heading

**Idea:** look for text that *looks like a heading* — bold, larger font, short
line, at the top of a page or with white space above it — and whose words match
an MD&A pattern.

**This is the workhorse.** Most successful extractions come from here.

**The traps, all of which we hit:**
- Plural: `Management Discussions and Analysis` (P28 fix)
- Split across lines: `ANNEXURE V` on one line, the title on the next — needs
  multi-line concatenation (fires on 42 docs, 21.6%)
- Contents pages look like a pile of headings — suppress pages with ≥3 terminator
  matches (fires on 83 docs, 42.8%)
- The Directors' Report *mentions* MD&A — needs the cross-reference guard (below)

---

## S4 — OCR-text heading

Same as S3, but on OCR'd text, for scanned documents. Needs OCR block geometry
(P29) so that column-cutting still works on OCR output — otherwise scanned
two-column pages come out interleaved.

**Untested**, because Tesseract isn't installed on the dev machine.

---

## S5 — Schedule V body cues

**Idea:** forget the heading. Look for the *mandated sub-headings* — "Industry
structure and developments", "Opportunities and threats", "Risks and concerns".
If a page has several of these, it IS the MD&A, whatever it's titled.

**Pros:** the most robust fallback. Works when the heading is missing, misspelled,
in an image, or the document is a scan.

**This is also the fallback that has been quietly saving us** — see file 07. When
the heading strategy was wrongly suppressed on 8 documents, the body-cue score
recovered the right page on 6 of them.

**Measured:** case-insensitive body cues fire on 159 of 194 docs (82%). That high
number is correct and healthy — real reports write these headings in every
case style.

---

## The cross-reference guard

A special rule that sits across S1/S3/S5: `is_cross_reference_pointer`.

**The problem it solves:** the Directors' Report says

> *"A report on Management Discussion and Analysis **is annexed** hereto and
> forms part of this Report."*

That mentions MD&A but is not MD&A. Without a guard, the pipeline starts there —
20 pages too early, in the middle of the Directors' Report.

**How it works:** look at the candidate heading plus the following 80 words. If
that text contains a pointer phrase (`is annexed`, `forms part of this Report`,
`separately given`, `a separate section on`), reject the candidate.

**Measured:** fires on 88 of 194 documents. **110 of those were correct** — real
pointers correctly rejected. **9 were wrong** — and that is file 07.

---

## The arbiter

All five run. Then:

1. Collect every proposed span.
2. Count how many independent strategies agree (`supporters`).
3. Prefer higher `supporters`. Break ties by body-cue score.
4. Refine the end using terminator headings.
5. Grade: high / medium / low, using supporters + span length + order quality.

**Important caveat:** the grade bands were fitted on four documents and are
therefore partly circular too. Treat a grade as "worth looking at", not as proof.
