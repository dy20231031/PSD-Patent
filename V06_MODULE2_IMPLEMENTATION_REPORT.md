# PSD Patent Intelligence v0.6 — Module 2 Related Patent Analysis MVP

## 구현 범위

v0.5의 배포용 Module 1 위에 관련특허 분석을 추가했다.

`Module 1 Structured Patent → Related Search Query → Public Candidate Search → Candidate Patent Retrieval → Lightweight Ontology Fingerprint → Ontology Similarity Reranking → Top 5 → Explanation Comparison`

## 검색

- 현재 공개 검색원: Google Patents public search interface/XHR (best-effort)
- 최대 3개의 recall-oriented query를 Target Ontology에서 생성
- 입력 특허 자체 제외
- 동일 priority date + 매우 유사한 title은 simple family 가능성이 높아 후보에서 제외
- 검색 단계는 recall을 우선하고 최종 precision은 Ontology reranking에서 확보

## Candidate 분석

검색 후보 전체에 긴 Module 1 보고서를 생성하지 않는다.

- 후보 원문/청구항을 최대 8건만 상세 조회
- Abstract + Independent Claims + 짧은 Description excerpt 사용
- Gemini batch 1회로 Candidate Ontology Fingerprint 생성
- Frozen PSD Vocabulary에 존재하지 않는 ID는 코드에서 제거

Fingerprint axes:
- Technology
- Architecture
- Problem
- Function
- Claim Element
- Relation

## Ontology 관련도

MVP 가중치:
- Relation 25%
- Problem 20%
- Function 20%
- Technology 15%
- Claim Element 15%
- Architecture 5%

Target에 존재하지 않는 축은 점수 분모에서 제외하여 재정규화한다.

## Top 5 설명 보고서

사용자 화면에는 내부 ID 대신 다음을 보여준다.

- 공개번호 / 특허명 / 출원인 / 공개일
- 관련도 점수
- 관련 특허 선정 이유
- 관련 특허의 해결 방식
- 공통 기술 과제
- 공통점
- 차이점
- 기술적 발전·변형 요소
- 공개 특허 원문 링크
- 종합 비교

## 실행 방식

Module 2는 비용/속도 때문에 lazy execution이다.
Module 1 완료 후 `관련 특허` 탭에서 사용자가 `관련 특허 분석 시작`을 눌렀을 때만 검색/LLM 호출을 수행한다.

## 제한사항

- Google Patents public search interface는 공식 지원 API가 아니므로 응답 구조/접근 정책이 변경될 수 있다.
- 검색 결과는 법적 선행기술 조사나 침해판단을 대체하지 않는다.
- Candidate fingerprint는 경량 분석이므로 Top 5 선정 후의 설명 역시 기술 비교용 MVP이다.
- 실제 PSD 특허 여러 건으로 query/weight/candidate count 튜닝이 필요하다.
