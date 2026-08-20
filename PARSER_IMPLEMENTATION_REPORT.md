# PDF Patent Parser v0.1 - Implementation Report

## Goal

Streamlit에서 업로드된 공개 특허 PDF를 읽어 Ontology/LLM 분석 전 단계의 `Raw Patent JSON`을 생성한다.

## Pipeline

```text
PDF upload
  -> pypdf embedded-text extraction
  -> text normalization
  -> metadata heuristic extraction
  -> patent section detection
  -> claim segmentation
  -> independent/dependent classification
  -> dependency extraction
  -> Pydantic RawPatent validation
  -> Streamlit preview + JSON download
```

## Raw Patent JSON

주요 필드:

- `schema_version`
- `source`: page count, text character count, extraction method, warnings
- `metadata`: publication number, title, applicant, filename, PDF metadata
- `abstract`
- `background`
- `summary`
- `figure_description`
- `description`
- `claims[]`: claim id/number/type/depends_on/text
- `parser_diagnostics`
- `raw_text`

## Supported heuristics

- English / Korean / Japanese common patent section headings
- English numbered claims (`1.`), `Claim N`, Korean `청구항 N` / `제N항`, Japanese `請求項N`
- English `according to claim N`, `of claim N`
- Korean `청구항 N에 있어서`, `제N항에 있어서`
- Japanese `請求項Nに記載`
- simple claim ranges such as `claims 1 to 3`

## Limitations

- v0.1 does **not** perform OCR. Scanned/image-only PDFs return a warning.
- Patent-office PDF layouts vary. Metadata and section detection are heuristic and must be refined with real PSD patents.
- Claim dependency detection is structural/linguistic heuristics, not a legal claim parser.
- Patent-number-only retrieval is not yet connected.
- Ontology mapping and LLM extraction are not yet connected.

## Validation

- Python compile check
- 8 pytest tests
- English section/claim parsing test
- Korean dependent-claim parsing test
- blank/image-only style PDF warning test
- existing Knowledge Base validation tests

## Next step

Connect `engine/patent/context_router.py` to the Raw Patent JSON so each Ontology extraction task receives only the required sections.
