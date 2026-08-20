# Module 1 v0.3 Gemini Migration Report

## Scope

This version migrates the v0.2 Module 1 LLM layer from OpenAI to the Google Gemini Developer API while preserving the PSD Ontology pipeline and user-facing report design.

## Changes

- Replaced `openai` dependency with official `google-genai` SDK.
- Added `engine/llm/gemini_client.py`.
- Default extraction/report model: `gemini-3.7-flash`.
- Gemini JSON-schema constrained outputs are used for Claim, Problem/Effect, Technology, and Module 1 report generation.
- Streamlit Secrets keys changed to `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_REPORT_MODEL`.
- Removed OpenAI-specific client and UI messages.
- The PSD Vocabulary/Ontology, canonical validation, Evidence UI, Raw Patent JSON and explanation-report philosophy are unchanged.

## Security

A real Gemini API key must exist only in Streamlit Community Cloud Secrets (or local untracked secrets), never in GitHub.

## Verification

Provider calls are covered with a mocked Gemini SDK so unit tests do not require a real API key. Real online model calls must be smoke-tested after the key is configured in the deployed app.
