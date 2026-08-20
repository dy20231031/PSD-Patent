# v0.7 Reliability + Visual Report UI Implementation Report

## Implemented

### 1. Gemini reliability
- transient 429/500/502/503/504/high-demand detection
- short exponential retry with jitter
- configurable fallback model
- configuration: `GEMINI_FALLBACK_MODEL`, `GEMINI_MAX_RETRIES`

### 2. Claim safety
- full analysis blocked when no claims are detected
- full analysis also blocked when claims exist but no independent claim can be identified

### 3. Evidence grounding
- Claim facts require E1/E2 evidence text
- Problems require PE1/PE2/PE3
- Effects require EE1/EE2/EE3
- inference-only E4/PE4/EE4 facts are removed before report generation

### 4. Patent-number input / family handling
- common number formatting normalization retained
- Google Patents Family ID extracted when present
- Module 2 excludes the target family and duplicate candidate families
- priority-date + title similarity remains fallback family detection

### 5. Module 2 quality
- three diversified query paths retained (technology/structure, problem/function, relation/element)
- candidate independent-claim validation
- PSD relevance high/medium/low classifier
- low-relevance candidates filtered before reranking
- public relatedness displayed as qualitative level plus `n/100`, not probability `%`

### 6. Actual patent drawings
- Google Patents / patentimages drawing URLs extracted from the patent page
- FIG number and brief specification caption attached when available
- representative figures selected using grounded report terms + FIG captions
- Module 1 shows up to 3 representative drawings
- Module 2 cards show a candidate representative drawing when available

### 7. Deployment UI
- redesigned hero/input/report hierarchy
- responsive summary cards
- compact analysis-quality chips
- numbered report section headers
- claim cards / operation-step cards
- figure gallery
- simplified Module 2 relatedness presentation
- developer JSON remains opt-in only

### 8. Cache
- successful patent-number Module 1 LLM reports cached in memory for 6 hours to reduce repeated Gemini usage

## Validation
- Python compilation: PASS
- pytest: 33 passed
- no real Gemini call executed during build
- Google Patents figure support is covered by HTML fixture tests; external availability still depends on Google Patents at runtime

## Known limitation
`st.image()` displays remote patent drawing URLs. If Google changes the patent page or image host policy, figure extraction/rendering may require an adapter update. PDF-only uploads do not yet segment figures.
