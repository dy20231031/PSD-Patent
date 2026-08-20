# PSD Patent Intelligence v0.2 — Module 1 End-to-End MVP

## Included pipeline

1. PDF upload / embedded-text parser
2. Raw Patent JSON
3. Context Router
4. OpenAI Responses API + Structured Outputs
5. Claim Element / Relation / Function / State / Mode / Constraint extraction
6. Problem / Effect extraction
7. Technology / Architecture assignment
8. Frozen JSON Knowledge Base post-normalization
9. `unmapped_candidate` preservation (no forced nearest mapping)
10. Structured Patent JSON
11. Explanation-oriented Korean Module 1 report
12. Evidence UI

## Knowledge versions

- PSD Core Taxonomy v1.4
- Claim Element Dictionary v1.3
- Function Vocabulary v1.2
- Relation Vocabulary v1.2
- State / Mode / Constraint v1.1
- Problem Vocabulary v1.1
- Effect / Design Attribute v1.1
- PSD Core Ontology v1.0

## LLM configuration

The application reads these Streamlit secrets:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5.6-luna"
OPENAI_REPORT_MODEL = "gpt-5.6-luna"
```

No API key is committed to GitHub. Without an API key, PDF parsing and Raw Patent JSON remain available.

## Evidence policy

- Claim extraction: E1 / E2 only
- Problem: PE1–PE3
- Effect: EE1–EE3
- E4 / PE4 / EE4 domain inference is not accepted as report Patent Fact
- Original expressions and evidence snippets are preserved alongside canonical terms

## Current limitations

- Patent-number automatic retrieval is not yet connected.
- Image-only/scanned PDFs are not OCRed.
- Parser heading heuristics may require per-office tuning.
- Module 2/3 remain placeholders.
- Module 1 quality must be tested on real PSD patents before ontology v1.1 freeze.
