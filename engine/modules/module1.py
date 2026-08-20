from __future__ import annotations


def build_module1_placeholder(patent_id: str) -> dict:
    return {
        "basic_info": {
            "publication_number": patent_id,
            "title": "실제 Patent Parser 연결 예정",
            "applicant": "-",
        },
        "core_problem": "Problem Vocabulary 기반 분석 결과가 표시될 영역입니다.",
        "claim_elements": [
            {"Claim Element": "-", "Canonical Element": "-", "Evidence": "-"}
        ],
        "relations": [
            {"Subject": "-", "Relation": "-", "Object": "-", "Evidence": "-"}
        ],
        "dependent_claims": "Dependent Claim 추가 제한사항 추출 예정",
        "operation_principle": "Function + Relation + State/Constraint 기반 생성 예정",
        "effects": "Effect Vocabulary 기반 분석 결과가 표시될 영역입니다.",
        "technology_classification": "PSD Core Taxonomy 기반 multi-label 분류 예정",
        "summary": "Structured Patent Representation을 바탕으로 생성 예정",
    }
