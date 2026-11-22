# Climate-exposure replication: results summary

Rebuild of Sautner, van Lent, Vilkov & Zhang (2023, JF) as one pipeline (seeds -> discovery
-> dictionary -> scores Eq. 1-4 -> validation). Figures and tables: this folder.

**Corpus.** 1,508 earnings-call transcripts, 21 US firms,
2005-2026; 362 firm-years (21 firms) match the official scores on (ISIN, year).

**Replication (authors' dictionary, full corpus; fig 1, table 1).**
- ExxonMobil 2024 CCExposure = 0.004575, 79.6% of the official 0.00575 (mean of 4 quarterly
  PDFs; our transcript excerpts are shorter than the authors').
- Firm-year correlation with the official scores (Pearson r / Spearman rho):
  cc_expo 0.983 / 0.942;
  op 0.980 / 0.915;
  rg 0.891 / 0.847;
  ph 0.711 / 0.660.
  Physical exposure is rare (few non-zero firm-years), so it is the noisiest.
- Sentiment tracks (cc_pos r = 0.967) but runs lower (median ratio
  0.71): the Loughran-McDonald words are not lemmatized,
  so lemmatized transcript words miss some of them.

**Risk (fig 5).** The paper never publishes its risk word list. Of three candidates the
curated list fits best (cc_risk r = 0.681); regulatory and physical
risk are not recovered by any list.

| Pearson vs official | narrow | curated | lm_unc |
|---|---|---|---|
| cc_risk | 0.599 | 0.681 | 0.630 |
| op_risk | 0.584 | 0.668 | 0.622 |
| rg_risk | 0.111 | 0.112 | 0.192 |

**Discovery (fig 2; 200-transcript sample, 149 matched firm-years, 21 firms).**
The classifiers find genuinely climate-heavy sentences (T holds 27x more authors'
bigrams per sentence than the rest of S), but on the sample most discovered dictionaries
barely beat the 50 seeds: seeds only rho = 0.672, authors' dictionary
0.838, our best variant (D2) 0.771.
Spearman rho with 95% bootstrap CIs (1,000 resamples of firm-years) and gain vs S0:

| variant | rho [95% CI] | gain vs S0 [95% CI] |
|---|---|---|
| S0 | 0.672 [0.553, 0.757] | +0.000 [+0.000, +0.000] |
| A | 0.689 [0.566, 0.779] | +0.017 [-0.096, +0.131] |
| B | 0.681 [0.549, 0.780] | +0.010 [-0.097, +0.109] |
| B2 | 0.679 [0.552, 0.775] | +0.007 [-0.099, +0.115] |
| D2 | 0.771 [0.682, 0.836] | +0.099 [+0.037, +0.172] |
| authors | 0.838 [0.757, 0.894] | +0.166 [+0.081, +0.255] |

Interpretation: besides the authors' dictionary, D2 beats seeds only with a CI that excludes zero, but stays below the authors'. Discovery needs corpus scale (the authors trained on ~60k climate
sentences from the full call universe; we have ~2k in R from 21 firms).

**Vocabulary shift (fig 3).** 41.8% of climate (T) sentences are from 2021 or later.
Bigrams such as net zero, carbon capture, energy transition and scope emission are central to
recent calls but absent from the authors' pre-2021 dictionary.

**Deviations from the paper.**
- LinearSVC + probability calibration instead of kernel SVC.
- Ratio-matched training sample (S sample = 1.667 x |R|, the paper's 100k/60k ratio).
- No stemming (spaCy lemmas only).
- IPCC rough library = AR5 (SYR, WG1, WG2 Part A, WG3) + SR1.5.
- Normal text N = NLTK Gutenberg, Reuters and Brown corpora.
- Rough-library cleaning: citation lines, digit tokens and token validity filters.
- Firm filter (candidate bigram must appear in T sentences of >= 3 firms) for a 21-firm corpus.

**Data note.** HON is matched on its old ISIN US4385161066; exchanges now list US4385162056.

**Next steps.** Topic dictionaries (opportunity / regulatory / physical); validation suite
(paper Table VI); Indian MD&A text via arpipe.
