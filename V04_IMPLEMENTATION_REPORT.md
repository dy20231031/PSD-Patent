# PSD Patent Intelligence v0.4
## Claim Parser Stabilization + Patent Number Retrieval

### 1. What changed

#### A. Stronger claim detection for PDF/text input
The parser now uses three stages instead of relying on a single `CLAIMS` heading:

1. **Explicit claims heading**
   - `CLAIMS`
   - `CLAIMS (8)`
   - `WHAT IS CLAIMED IS`
   - `THE INVENTION CLAIMED IS`
   - `WHAT WE CLAIM IS`
   - `WE CLAIM`, `I CLAIM`
2. **Embedded claim preamble**
   - detects the same phrases even when PDF line extraction breaks the heading format
3. **Tail numbered-sequence fallback**
   - scans the latter part of the document for a consecutive `1., 2., 3.` claim-like block
   - scores claim drafting terms and dependency cues to reduce false positives

Claim dependency parsing continues to support forms such as:
- `according to claim 1`
- `of claim 1`
- `claims 1 to 4`
- Korean/Japanese basic dependency cues

The Raw Patent JSON now records parser diagnostics including:
- detection strategy
- heading/preamble
- start character position
- candidate marker count
- claims preview
- independent/dependent claim counts

#### B. Patent-number direct retrieval
A new `engine/patent/retriever.py` retrieves the public patent page from Google Patents using a publication/grant number such as:

- `US10774572B2`
- `US20190093412A1`
- `JP7604988B2`
- `EP...`

The app requests the `/en` version and extracts:
- publication number
- title
- assignee/applicant when available
- inventors when available
- abstract
- description
- claims
- basic date/status metadata when available

For Google Patents HTML, claims are read from the structured `section[itemprop="claims"]` markup rather than PDF regex when possible. This is expected to be more stable than PDF claim extraction for patent-number input.

#### C. Safety gate for zero claims
If `claim_count == 0`, the app no longer says Ontology Claim Analysis completed. It stops the Claim Element / Relation / Constraint pipeline and does not create a full Module 1 report.

#### D. UI
- Patent number is now a real input method, not only a hint.
- PDF still takes precedence if both patent number and PDF are supplied.
- Overview shows source provider / source URL for online retrieval.
- Raw Patent JSON tab shows Claim Parser Diagnostics and a claim-text preview.

### 2. Dependencies
Added:

```text
beautifulsoup4>=4.12,<5
```

Existing `requests` is used for public patent retrieval.

### 3. Test result

```text
23 passed
```

The test suite covers:
- explicit CLAIMS parsing
- `CLAIMS (n)` headings
- `THE INVENTION CLAIMED IS` preamble
- tail numbered-claim fallback
- Korean basic dependency parsing
- Google Patents structured HTML claims
- patent-number URL construction
- zero-claim safety gate
- existing Ontology/Gemini pipeline tests

### 4. Important limitation
Google Patents is an external public web source. Retrieval can temporarily fail because of network errors, HTTP rate limits, or future HTML changes. PDF upload remains the fallback input path.
