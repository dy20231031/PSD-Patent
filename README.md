# PSD Patent Intelligence

Ontology-based Power Sliding Door patent analysis web application.

## Current version: v0.3 — Gemini Module 1 End-to-End MVP

The deployed Streamlit app can process a text-based patent PDF through:

`PDF → Raw Patent JSON → Context Router → PSD Ontology Extraction (Gemini) → Canonical Validation → Structured Patent JSON → Module 1 Explanation Report (Gemini)`

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

## Gemini LLM setup

Copy the values from `.streamlit/secrets.toml.example` into Streamlit Community Cloud **App settings → Secrets**. Never commit a real API key.

Default model: `gemini-3.7-flash` (configurable through `GEMINI_MODEL`).

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "gemini-3.7-flash"
GEMINI_REPORT_MODEL = "gemini-3.7-flash"
```

The app uses Google's official `google-genai` SDK with JSON-schema constrained output.

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
- Ontology extraction still needs real-patent mapping tests and later ontology refinement
