from __future__ import annotations

from engine.modules.module1 import build_module1_placeholder
from engine.modules.module2 import build_module2_placeholder
from engine.modules.module3 import build_module3_placeholder


def analyze_patent(patent_number: str | None, uploaded_file_name: str | None) -> dict:
    """MVP service entry point.

    현재는 UI/프로젝트 구조 검증용 placeholder 결과를 반환한다.
    다음 단계에서 Patent Parser → Context Router → Ontology Mapper → LLM을 연결한다.
    """
    display_id = patent_number or uploaded_file_name or "Uploaded Patent"

    return {
        "title": f"{display_id} · PSD Patent Analysis",
        "patent_number": display_id,
        "primary_technology": "Ontology mapping pending",
        "status": "MVP",
        "overview": (
            "이 화면은 PSD Patent Intelligence의 배포 가능한 기본 골격입니다. "
            "다음 단계에서 현재 확정한 PSD Vocabulary/Ontology JSON을 연결합니다."
        ),
        "module1": build_module1_placeholder(display_id),
        "module2": build_module2_placeholder(),
        "module3": build_module3_placeholder(),
        "evidence": [
            {
                "label": "Evidence 연결 예시",
                "source": "Claim / Specification",
                "text": "실제 분석 엔진 연결 후 원문 근거가 이 영역에 표시됩니다.",
            }
        ],
    }
