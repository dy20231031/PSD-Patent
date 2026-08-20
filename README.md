# PSD Patent Intelligence

Ontology-based Power Sliding Door patent analysis web application.

## Current version: v0.7 — Reliability + Visual Report UI

The public Streamlit app supports:

1. **Patent publication/grant number** → Google Patents public full text, claims, metadata, patent family ID, and available patent drawings
2. **Patent PDF upload** → embedded-text extraction

Main flow:

`Patent → Claim Validation → PSD Ontology Extraction → Evidence Grounding → Module 1 Explanation + Patent Figures → Module 2 Search / Family Dedup / PSD Filter / Ontology Reranking`

### Public report philosophy

The PSD Ontology remains an internal reasoning/normalization layer. The public page is report-first and does not expose ontology IDs or raw JSON. The report focuses on:

- what problem the patent addresses,
- which independent-claim elements are required,
- how the elements interact,
- how the mechanism works,
- what effects are actually supported by the specification,
- representative **real patent drawings**, and
- related public patents with technical differences.

A compact `분석 근거 보기` expander remains available for source-grounding checks.

## v0.7 reliability safeguards

- Gemini temporary errors (429 / 500 / 502 / 503 / 504 / high demand) → short exponential retry
- Primary model exhausted → automatic fallback model
- `claims = 0` **or** `independent_claims = 0` → Claim Ontology / full Module 1 blocked
- E4 / PE4 / EE4 and assertions without source evidence are removed before report generation
- successful patent-number analyses are cached in memory for 6 hours
- patent-number input normalization accepts common spaces/hyphens/punctuation variants

## Patent drawings

For patent-number input, Google Patents drawing assets are collected from the public patent result and stored as figure metadata (`FIG. N`, image URL, specification caption). The report chooses a small representative set using figure-description text + already-grounded Module 1 terms. It does **not** infer new patent facts from the pixels.

Drawing availability depends on the public source. PDF-only input does not currently segment drawings from PDF pages.

## Module 2 v0.7 quality filters

Module 2 keeps the v0.6 multi-query search and adds:

- exact Google Patents family-ID dedup when available,
- fallback priority-date/title family heuristic,
- duplicate-family removal among Top candidates,
- independent-claim requirement for candidate analysis,
- PSD relevance classifier (`high / medium / low`), with `low` candidates removed,
- public UI showing `기술 관련도 높음/중간/낮음` plus a secondary `구조 유사도 n/100`, instead of presenting the score as a probability,
- representative patent drawing in related-patent cards when available.

The similarity signal is engineering-oriented and is **not** an infringement, novelty, validity, or FTO opinion.

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
GEMINI_FALLBACK_MODEL = "gemini-3.6-flash"
GEMINI_MAX_RETRIES = 2
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
- PDF-upload path does not yet extract individual figure images
- Google Patents retrieval/search is an external best-effort dependency and can be affected by rate limits or HTML/XHR changes
- Module 2 analyzes a limited candidate set to control latency/API use; it is not a comprehensive legal prior-art search
- representative figure selection is caption/text based; multimodal pixel-level figure reasoning is not yet enabled
- Module 3 remains a placeholder
