# PSD Patent Intelligence

Power Sliding Door(PSD) 공개 특허를 **PSD Core Ontology 기반으로 분석**하고,
Module 1(특허 분석), Module 2(관련특허 분석), Module 3(Technology Intelligence) 보고서를 생성하기 위한 웹 프로젝트입니다.

## 현재 상태

**MVP Project Skeleton**

- Streamlit Web UI: 완료
- Module 1/2/3 화면: placeholder 완료
- PSD Ontology/Knowledge 폴더 구조: 완료
- Structured Patent Schema: 기본 뼈대 완료
- 실제 특허 Parser: 다음 단계
- Vocabulary/Ontology JSON 변환: 다음 단계
- LLM 연결: 다음 단계
- Related Patent Retrieval: 다음 단계

## 프로젝트 구조

```text
PSD-Patent-Intelligence/
├─ streamlit_app.py
├─ requirements.txt
├─ .streamlit/
├─ engine/
│  ├─ app_service.py
│  ├─ schemas.py
│  ├─ patent/
│  ├─ ontology/
│  ├─ modules/
│  ├─ retrieval/
│  └─ reports/
├─ knowledge/
├─ sample_data/
└─ tests/
```


## GitHub 업로드 시 주의

이 프로젝트는 폴더 구조가 중요합니다. GitHub 일반 `Upload files`에서 여러 폴더의 파일을 한 번에 선택하면 파일이 평탄화되어 `__init__ (1).py`처럼 이름이 바뀔 수 있습니다.

**브라우저만 사용할 경우 `GitHub Codespaces + ZIP 압축 해제` 방식을 권장합니다.** 자세한 단계는 `GITHUB_UPLOAD_GUIDE.md`를 참고하세요.

## Streamlit Community Cloud 배포

1. 이 폴더를 GitHub Repository에 업로드합니다.
2. Streamlit Community Cloud에서 `Create app`을 선택합니다.
3. Repository와 branch를 선택합니다.
4. Main file path를 `streamlit_app.py`로 지정합니다.
5. Deploy합니다.
6. LLM API를 연결한 뒤에는 API Key를 코드에 넣지 말고 Streamlit Secrets에 저장합니다.

## 다음 구현 단계

1. 확정된 PSD Vocabulary/Ontology를 JSON Knowledge Base로 변환
2. Structured Patent Output Schema 확정
3. 특허번호/PDF → Patent Parser 연결
4. Context Router 구현
5. Ontology Extraction / Normalization 구현
6. Module 1 실제 Report Generator 연결
7. Module 2 Related Patent Retrieval 연결
8. Module 3 Technology Intelligence 연결

## 설계 원칙

- LLM이 특허를 바로 자유요약하지 않음
- `Patent → Structured Patent Representation → Report` 순서를 유지
- Claim Fact는 Evidence/Provenance와 함께 저장
- PSD Ontology의 canonical ID와 원문 표현을 함께 보존
- Domain inference(E4/PE4/EE4)는 Patent Fact로 출력하지 않음


## Knowledge Base status

The starter now includes a populated, machine-readable PSD knowledge base generated from the frozen knowledge engineering documents.

| Axis | Version | Count |
|---|---:|---:|
| Technology taxonomy | v1.4 | 73 technology nodes |
| Architecture values | v1.4 | 18 values |
| Claim Elements | v1.3 | 144 |
| Functions | v1.2 | 69 |
| Relations | v1.2 | 46 |
| State dimensions / modes | v1.1 | 10 / 4 |
| Claim Constraint types | v1.1 | 12 |
| Problems | v1.1 | 47 |
| Effects / Design Attributes | v1.1 | 65 / 20 |
| Core Ontology | v1.0 | 15 validation rules |

Run `pytest -q` to validate the project and knowledge base.
