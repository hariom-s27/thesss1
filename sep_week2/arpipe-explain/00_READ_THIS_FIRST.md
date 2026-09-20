# 00 — Read This First

This folder answers four questions, in very simple English:

1. **What are we actually building?** (and why)
2. **What have we finished so far?** (honestly)
3. **Why did we choose this way and not another way?** (options, with reasons)
4. **How do we go from 20 files to 10,000 files?**

One file per topic. Read them in order. Each file is short.

| File | What it answers |
|---|---|
| `01_WHAT_WE_ARE_BUILDING.md` | The whole thesis in one page. Both repos. |
| `02_WHY_MDA_AND_WHY_HARD.md` | What MD&A is. Why a computer cannot just "find" it. |
| `03_HOW_THE_PIPELINE_WORKS.md` | The ten steps, each in two sentences. |
| `04_THE_FIVE_STRATEGIES.md` | The five ways we look for MD&A, and why five. |
| `05_WHAT_WE_HAVE_BUILT.md` | Real status today. What works, what doesn't. |
| `06_THE_CIRCULAR_SCORE_STORY.md` | The big mistake we found and fixed. The most important file. |
| `07_WHAT_THE_AUDIT_FOUND.md` | P33 results. Two real bugs. |
| `08_OPTIONS_WE_DID_NOT_TAKE.md` | Every big choice, the options, why we picked ours. |
| `09_SCALING_TO_10K.md` | 20 files → 10,000 files. Cost, time, what breaks. |
| `10_WHAT_TO_DO_NEXT.md` | The ordered list. What to run, in what order. |

---

## The 60-second version

You are building **two halves of one thesis**:

- **Repo `thesis`** — the *measure*. It reads company earnings-call transcripts
  and scores how much they talk about climate. This reproduces a published
  finance paper (Sautner et al. 2023) and then extends it. **This half works.**

- **Repo `arpipe`** — the *data*. It collects Indian annual reports and pulls out
  the MD&A section, so the measure can be applied to Indian companies instead of
  US ones. **This half is 80% built and just had its scoreboard fixed.**

The thesis contribution is: *take a climate-exposure measure built for US
earnings calls, and apply it to Indian annual-report MD&A text, which nobody has
a clean corpus for.* ARPipe is how you get that corpus.

**Where we are right now:** ARPipe works end-to-end on normal PDFs. We just
discovered the accuracy score was measuring itself (circular), fixed the
measurement, and got an honest number: **83.3% on 6 documents**. Six is too few.
The next job is labelling ~300 documents properly so the number means something.
