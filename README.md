# PSD Patent Intelligence

Ontology-based Power Sliding Door patent analysis web application.

## Current version: v0.6 — Module 2 Related Patent Analysis MVP

The Streamlit app now supports two input paths:

1. **Patent publication/grant number** → public Google Patents page retrieval
2. **Patent PDF upload** → embedded-text extraction

Both paths produce a Raw Patent JSON. When claims are successfully identified and Gemini is configured, the flow continues as:

`Raw Patent JSON → Context Router → PSD Ontology Extraction → Canonical Validation → Structured Patent JSON → Module 1 Explanation Report → Module 2 Related Patent Search / Ontology Reranking / Comparison`

### User-facing philosophy

The PSD Ontology is an internal reasoning/normalization layer. The default report does **not** expose vocabulary IDs. Instead, it explains what the patent solves, which elements are essential, how the elements interact, how the mechanism works, and what technical effects follow. The public deployment shows a clean explanation report. Raw/Structured JSON diagnostics are hidden by default; evidence remains available through a compact “분석 근거 보기” expander.

## Claim parser v0.4

PDF/text claim detection uses three stages:

- explicit `CLAIMS` / `CLAIMS (n)` / claim-heading detection
- embedded preamble detection such as `THE INVENTION CLAIMED IS`
- tail numbered-sequence fallback when headings are lost by PDF extraction

If zero claims are detected, Claim-based Ontology analysis is blocked rather than generating a misleading full report.

## Patent number retrieval

Examples:

- `US10774572B2`
- `US20190093412A1`
- `JP7604988B2`

The public `/en` page is requested from Google Patents. Claims are preferentially extracted from structured HTML.

## Knowledge Base

`knowledge/` contains the frozen JSON versions of:

- Core Taxonomy v1.4
- Claim Element Dictionary v1.3
- Function Vocabulary v1.2
- Relation Vocabulary v1.2
- State / Mode / Claim Constraint v1.1
- Problem Vocabulary v1.1
- Effect / Design Attribute v1.1
- Core Ontology v1.0

## Gemini setup

Store the real key only in Streamlit Community Cloud **App settings → Secrets**.

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "gemini-3.7-flash"
GEMINI_REPORT_MODEL = "gemini-3.7-flash"
SHOW_DEVELOPER_TOOLS = false
```

## Run / test

```bash
pip install -r requirements.txt
python -m pytest
streamlit run streamlit_app.py
```

## Current limitations

- OCR for image-only PDF: not implemented
- Public patent retrieval depends on an external Google Patents web page and may be affected by network/rate-limit/HTML changes
- Module 2 search uses the public Google Patents search/XHR interface as a best-effort external source and may break if that interface changes
- Module 2 MVP analyzes a limited candidate set to control latency/API usage; it is not a legal prior-art search
- Module 3: placeholder
- Ontology extraction still needs real-patent mapping tests and later ontology refinement


## Deployment UI v0.5

The default public UI is report-first:

- Patent number / PDF input
- Three-part core summary
- Patent basic information
- Core problem
- Independent-claim elements / relations / conditions
- Dependent-claim additions
- Operation principle
- Technical effects
- PSD technology classification
- Core technology summary
- Evidence expander

Implementation details such as Raw Patent JSON, Structured Patent JSON, parser diagnostics, ontology IDs, validation traces, and internal model status are hidden unless `SHOW_DEVELOPER_TOOLS = true`.


## Module 2 v0.6

The **관련 특허** tab is lazy-loaded so a normal Module 1 analysis does not spend extra API calls. When the user starts Module 2, the service:

1. builds up to three recall-oriented search queries from the target patent's Technology / Problem / Function / Claim Element / Relation facts,
2. searches public Google Patents candidates,
3. retrieves a limited set of candidate patent pages and independent claims,
4. performs one lightweight Gemini ontology-fingerprint batch,
5. reranks candidates with Relation 25%, Problem 20%, Function 20%, Technology 15%, Claim Element 15%, Architecture 5%, and
6. generates a user-facing Top-5 comparison report.

The relatedness score is a technical ontology-similarity signal only. It is not an infringement, novelty, validity, or freedom-to-operate opinion.
