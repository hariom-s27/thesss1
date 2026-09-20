# 07 — What The P33 Audit Found

P33 measured all 16 rules added since P25 across all 194 documents. It changed no
behaviour. It found **two real span bugs** that no metric had shown.

This is the audit doing exactly what it was built to do: a rule fitted to one
document was quietly damaging other documents, and nothing else could see it.

---

## Bug 1 — the cross-reference guard rejects real MD&A headings

**Fired on 88 of 194 documents (45.4%). 110 correct. 9 wrong.**

### What the rule is for

The Directors' Report says *"a report on MD&A **is annexed** hereto"*. That
mentions MD&A but is not MD&A. The guard rejects it. Correct — 110 times.

### What went wrong

The pattern list included:

```python
r"\b(?:is|are)\s+(?:enclosed|attached|annexed|given|presented|provided)\b"
```

But Indian MD&A sections very often **open** with a regulatory preamble:

> *"Pursuant to Regulation 34(2)(e) of SEBI LODR Regulations 2015, a Management
> Discussion and Analysis report **is given below**:- 1) OVERALL REVIEW..."*

`is given below` matched `is given`. So the guard rejected the heading on the
**genuine start page**.

The difference is direction: `is annexed` points *elsewhere*. `is given below`
points *here, immediately following*. One means "not here". The other means
"right here". They were being treated identically.

### The damage

| Document | Real start | What happened |
|---|---|---|
| Sar Auto FY2018 | p.9 | **started at p.12 — first 3 pages of MD&A lost** |
| Craftsman Automation FY2025 | p.16 | **started at p.15 — a Directors' Report page included** |
| Sar Auto FY2013/17/24/25 | — | heading suppressed, body-cue score recovered the right page |
| Craftsman FY2024 | p.27 | heading suppressed, body-cue recovered |
| Modern Steels FY2012 | p.5 | secondary candidate rejected |

Two documents got **genuinely wrong spans.** Six were saved by S5 (Schedule V
body cues) — which is a strong argument for having built five strategies instead
of one. The redundancy was load-bearing without anyone knowing.

### The fix (already applied)

The pattern was split, and a negative lookahead added:

```python
r"\b(?:is|are)\s+(?:enclosed|attached|annexed)\b",
r"\b(?:is|are)\s+(?:given|presented|provided)\b(?!\s*[:–—-]*\s*(?:below|hereunder|as\s+under|as\s+follows)\b)",
```

Now `is annexed` still rejects; `is given below` does not.

### The important observation

Note where this bug came from. `is_cross_reference_pointer` was the rule I had
flagged as "riskiest" in doc 26, on the theory that its unconditional form would
break Jain FY2025's `ANNEXURE V` opening.

**The theory was right that the rule was dangerous. It was wrong about which
documents.** Jain was fine. Sar Auto and Craftsman were not. This is the
difference between predicting a bug and measuring one — and it's why P33 was
specified as measure-only across the full corpus rather than a targeted check.

---

## Bug 2 — `"To the Members of"` as a terminator

**Fired on 13 of 194 documents (6.7%). 1 flagged.**

This was the other rule I'd flagged as risky, because `"To the Members of"` is
also the standard *opening* of both the Directors' Report and the Independent
Auditor's Report.

**Measured result: much safer than feared.** 12 of 13 firings were 11–45 pages
after the start — clearly the auditor's report, correctly ending the section.

The one flagged case, SJVN FY2017, turns out to be **correct behaviour**:

- p.126: `Annexure – I / MANAGEMENT DISCUSSION AND ANALYSIS` for SJVN's
  subsidiary, SJVN Thermal Private Limited
- p.126–127: the section (genuinely only 2 pages — it's a subsidiary's MD&A)
- p.128: `TO THE MEMBERS OF SJVN THERMAL PRIVATE LIMITED` — the subsidiary's
  auditor's report

The terminator found the true boundary. It only tripped the safety flag because
the section is unusually short.

**Conclusion: leave this rule alone.** The risk was real in theory and small in
practice. The `check_terminator_line` heading-shape gate (short line, top third
of page or blank space above, Title Case/bold) is doing its job.

This is the *other* value of an audit — it tells you which suspicions to drop, so
you don't spend a week hardening something that was already fine.

---

## The high-frequency rules: all benign

Five rules fired on >10% of the corpus. Every one checked out:

| Rule | Fires | Verdict |
|---|---|---|
| case-insensitive body cues | 159 (82%) | **Correct.** Reports write `INDUSTRY STRUCTURE`, `Industry Structure`, and `Industry structure`. All three are real. |
| cross-reference guard | 88 (45%) | The 9 false positives above; now fixed |
| TOC page suppression | 83 (43%) | **Correct.** Contents pages genuinely look like a pile of headings |
| multi-line heading join | 42 (22%) | **Correct.** Designers split titles across lines constantly |
| mid-page terminator inclusion | 20 (10%) | **Correct.** Sections end mid-page and the next one starts below |

The lesson: **a high fire count is not evidence of a bug.** These rules fire often
because the patterns they describe are common in real annual reports. The 10%
flag was a prompt to look, and looking is what resolved it.

---

## Rules that never fired at all

```
ten_year_summary_p27           0
refine_end_short_circuit       0
trim_span_pointer_rejections   0
report_on_fin_statements       0
```

Four rules with zero coverage. They aren't bugs, but they are **untested code**
carrying risk with no demonstrated benefit. Worth noting in the methodology as
dead weight, and worth re-checking once OCR is running and the FY2010–2014
documents actually flow through — that's the era they were written for.

---

## What this audit bought

- 2 genuinely wrong spans found and fixed
- 1 feared bug measured and cleared
- 5 high-frequency rules validated as correct
- 4 rules identified as never-exercised
- Proof that S5 body cues were silently rescuing 6 documents from a broken S3

None of this was visible in any accuracy number, before or after P31. **Aggregate
metrics cannot find this class of bug.** Only per-rule measurement across the full
corpus can.
