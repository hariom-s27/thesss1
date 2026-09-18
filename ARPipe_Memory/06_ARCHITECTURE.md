# ARPipe — Architecture

PDF → discovery → download/hash → page triage → native extraction → MD&A segmentation → OCR only needed pages → cleanup/reading order → re-trim → identity/year verification → provenance storage

## Locator hierarchy
S1 bookmarks/outline
S2 printed TOC folio mapping
S3 typographic heading
S4 OCR/text heading
S5 Schedule-V/body cues
arbiter

## Quality boundaries
Keep separate:
1. scan/input quality
2. OCR quality
3. extraction correctness
4. section-boundary correctness
5. downstream thesis measurement

## R1 telemetry
Schema `r1-v1`; one record per actual attempt; redacted URL; optional URL SHA-256; attempt number; failure layer/type; terminal state; retry exhaustion; status/latency where available; non-blocking writer.
