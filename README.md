# PSD Patent Intelligence

Ontology-based Power Sliding Door patent analysis web application.

## Current version: v0.2 — Module 1 End-to-End MVP

The deployed Streamlit app can now process a text-based patent PDF through:

`PDF → Raw Patent JSON → Context Router → PSD Ontology Extraction → Canonical Validation → Structured Patent JSON → Module 1 Explanation Report`

### User-facing philosophy

The PSD Ontology is an internal reasoning/normalization layer. The default report does **not** expose vocabulary IDs. Instead, it explains what the patent solves, which elements are essential, how the elements interact, how the mechanism works, and what technical effects follow. The Structured Analysis and Evidence tabs remain available for verification.

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

## LLM setup

Copy the values from `.streamlit/secrets.toml.example` into Streamlit Community Cloud **App settings → Secrets**. Never commit a real API key.

Default model: `gpt-5.6-luna` (configurable through `OPENAI_MODEL`).

## Run locally / Codespaces

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Tests:

```bash
python -m pytest
```

## Current limitations

- Patent-number automatic retrieval: not connected yet
- OCR for image-only PDF: not implemented
- Module 2: placeholder
- Module 3: placeholder
- Ontology extraction needs real-patent mapping tests and later v1.1 refinement
