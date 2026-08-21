# v0.6.1 — Module 1 Two-Call Optimization + Cache

## Goal
Keep the v0.6 deployment UI, Module 1 report format, PSD Ontology, canonical normalization, and Module 2 behavior unchanged while reducing normal Module 1 Gemini usage from about 4 calls to 2 calls.

## Changed pipeline

### Before — v0.6
1. Claim / Relation / Function / Constraint extraction
2. Problem / Effect extraction
3. Technology / Architecture classification
4. Module 1 explanation report

### After — v0.6.1
1. Integrated structured extraction
   - Independent/dependent claims
   - Claim Elements
   - Relations
   - Functions
   - States / Modes
   - Constraints
   - Problems
   - Effects
   - Technology
   - Architecture
2. Module 1 explanation report

The first call still receives separate claim context and specification context, and each section has explicit rules. Claim completeness is the highest priority. Technology classification is required to follow the mechanism extracted in the same response rather than making an unrelated classification guess.

## Quality safeguards
- Existing Context Router is retained.
- Existing frozen PSD vocabulary JSON is retained.
- Existing canonical normalization and validation code path is retained.
- Unknown concepts remain `unmapped_candidate`; nearest concepts are not forced.
- Problem/Effect domain inference is still prohibited by the extraction instructions.
- If the parser found an independent claim but the integrated extraction returns zero independent claims, Module 1 stops rather than generating a misleading report.
- If extracted and parsed independent-claim counts differ, a validation warning is recorded.
- Final report prompt/shape is unchanged from v0.6.

## Cache
Successful LLM explanation results are cached in memory for 6 hours using:
- normalized patent number or PDF SHA-256
- extraction model
- report model
- pipeline version

Expected Gemini calls:
- First successful Module 1 analysis: 2
- Same patent/PDF, same models, same running Streamlit process: 0
- After app reboot/redeploy or model change: 2 again

Fallback reports caused by a temporary report-model error are intentionally not cached, so a later retry can obtain the full report.

## Gemini 3.6 compatibility
`temperature=0.1` was removed from the Gemini request configuration. No report/UI behavior is changed by this adjustment.

## Module 2
Module 2 is unchanged in v0.6.1 and remains lazy-loaded. Its candidate analysis/report calls are separate from the two-call Module 1 budget.

## Validation
- pytest: 29 passed
- Python compileall: passed
- No Knowledge JSON files changed
