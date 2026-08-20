# PSD Patent Intelligence v0.5 — Deployment Report UI

## Goal
Keep the ontology and structured patent representation as a strict internal analysis layer while showing public users only a clear, explanation-oriented patent report.

## Public UI
- Patent number input or PDF upload
- Human-readable analysis progress
- Patent title / number / applicant / primary PSD technology
- Three-part summary: what / how / key point
- Module 1 report sections 1–8
- Compact source-evidence expander
- Report-data download

## Hidden by default
- Raw Patent JSON
- Structured Patent JSON
- Parser diagnostics
- Canonical IDs
- Mapping validation details
- Internal model status / traces

These can be temporarily enabled for the owner with Streamlit Secret:

```toml
SHOW_DEVELOPER_TOOLS = true
```

For public deployment keep it false.

## Analysis behavior
No analysis logic was weakened for the cleaner UI. Patent parsing, claim extraction, context routing, ontology extraction, canonical normalization, validation, evidence grounding, and explanation generation continue to run in the backend.
