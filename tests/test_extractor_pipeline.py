from engine.ontology.extractor import extract_structured_patent, generate_module1_report
from engine.ontology.loader import load_all_knowledge
from engine.patent.parser import parse_patent_text
from tests.test_patent_parser import SAMPLE_PATENT_TEXT


class FakeLLM:
    model = "fake-model"

    def __init__(self):
        self.calls = []

    def generate_json(self, *, schema_name, **kwargs):
        self.calls.append(schema_name)
        if schema_name == "psd_integrated_patent_extraction":
            return {
                "independent_claims": [
                    {
                        "claim_id": "C1",
                        "claim_number": 1,
                        "plain_summary": "스프링이 장력 풀리를 케이블 쪽으로 밀어 장력을 유지하는 구조이다.",
                        "claim_elements": [
                            {
                                "element_instance_id": "DriveCable_1",
                                "master_element_id": "CE-CAB-001",
                                "canonical_name": "Drive Cable",
                                "original_expression": "drive cable",
                                "element_type": "Component",
                                "instance_index": 1,
                                "role": None,
                                "position": None,
                                "attributes": [],
                                "normalization_status": "exact",
                                "evidence": {"source_section": "Claim", "claim_id": "C1", "evidence_text": "a drive cable", "evidence_level": "E1"},
                            },
                            {
                                "element_instance_id": "TensionPulley_1",
                                "master_element_id": "CE-PUL-004",
                                "canonical_name": "Tension Pulley",
                                "original_expression": "tension pulley",
                                "element_type": "Component",
                                "instance_index": 1,
                                "role": None,
                                "position": None,
                                "attributes": [],
                                "normalization_status": "exact",
                                "evidence": {"source_section": "Claim", "claim_id": "C1", "evidence_text": "a tension pulley", "evidence_level": "E1"},
                            },
                            {
                                "element_instance_id": "Spring_1",
                                "master_element_id": "CE-TEN-001",
                                "canonical_name": "Spring",
                                "original_expression": "spring",
                                "element_type": "Component",
                                "instance_index": 1,
                                "role": None,
                                "position": None,
                                "attributes": [],
                                "normalization_status": "exact",
                                "evidence": {"source_section": "Claim", "claim_id": "C1", "evidence_text": "a spring configured to bias", "evidence_level": "E1"},
                            },
                        ],
                        "relation_assertions": [
                            {
                                "relation_assertion_id": "RA-001",
                                "subject_instance_id": "Spring_1",
                                "relation_id": "R-MOT-05",
                                "canonical_relation": "biases",
                                "object_instance_id": "TensionPulley_1",
                                "object_set": [],
                                "attributes": [],
                                "normalization_status": "exact",
                                "evidence": {"source_section": "Claim", "claim_id": "C1", "evidence_text": "spring configured to bias the tension pulley", "evidence_level": "E1"},
                            }
                        ],
                        "function_assignments": [
                            {
                                "function_assignment_id": "FA-001",
                                "subject_instance_id": "TensionPulley_1",
                                "function_id": "F-FLX-09",
                                "canonical_function": "maintain_tension",
                                "target_instance_id": "DriveCable_1",
                                "normalization_status": "exact",
                                "evidence": {"source_section": "Claim", "claim_id": "C1", "evidence_text": "bias the tension pulley toward the drive cable", "evidence_level": "E2"},
                            }
                        ],
                        "state_assertions": [],
                        "mode_assertions": [],
                        "constraints": [],
                    }
                ],
                "dependent_claims": [
                    {
                        "claim_id": "C2",
                        "claim_number": 2,
                        "depends_on": [1],
                        "added_limitations": ["장력 풀리가 홀더에 이동 가능하게 지지됨"],
                        "evidence": [{"source_section": "Claim", "claim_id": "C2", "evidence_text": "tension pulley is movably supported by a holder", "evidence_level": "E1"}],
                    }
                ],
                "problems": [
                    {
                        "problem_assertion_id": "PA-001",
                        "problem_id": "P-FLX-01",
                        "canonical_problem": "tension_loss_or_slack",
                        "korean_name": "장력 저하 / 처짐",
                        "role": "primary",
                        "target_expressions": ["cable"],
                        "cause_expressions": ["repeated operation"],
                        "problem_status": "explicit",
                        "normalization_status": "exact",
                        "evidence": {"source_section": "Background", "claim_id": None, "evidence_text": "cable systems may develop slack after repeated operation", "evidence_level": "PE1"},
                    }
                ],
                "effects": [
                    {
                        "effect_assertion_id": "EA-001",
                        "effect_id": "E-FLX-01",
                        "canonical_effect": "stabilize_tension",
                        "korean_name": "장력 안정화",
                        "role": "primary",
                        "design_attribute_ids": ["DA-05"],
                        "effect_status": "explicit",
                        "normalization_status": "exact",
                        "evidence": {"source_section": "Summary", "claim_id": None, "evidence_text": "cable tension can be maintained", "evidence_level": "EE1"},
                    }
                ],
                "technology_assignments": [
                    {"technology_id": "T2.6", "technology_name": "Tension / Slack Management", "role": "primary", "rationale": "케이블 장력 보상 구조가 발명의 중심이다."}
                ],
                "architecture_assignments": [],
            }
        if schema_name == "psd_module1_explanation_report":
            return {
                "three_line_summary": {
                    "what_is_patent": "케이블 장력을 유지하는 PSD 구동 기술이다.",
                    "how_it_solves": "스프링이 장력 풀리를 케이블 쪽으로 밀어 길이 변화를 보상한다.",
                    "key_point": "스프링-장력 풀리-케이블의 작동 관계가 핵심이다.",
                },
                "core_problem": "반복 작동 후 케이블이 느슨해질 수 있는 문제를 해결한다.",
                "independent_claims": [
                    {
                        "claim_number": 1,
                        "plain_explanation": "스프링과 장력 풀리를 이용해 케이블에 장력을 유지하는 구조이다.",
                        "claim_elements": [
                            {"name": "Drive Cable", "original_expression": "drive cable", "explanation": "도어 구동력을 전달하는 케이블이다."}
                        ],
                        "relation_explanation": "스프링이 장력 풀리를 케이블 방향으로 밀어준다.",
                        "core_conditions": [],
                        "scope_note": "구성요소의 존재뿐 아니라 상호 작동관계가 함께 요구된다.",
                    }
                ],
                "dependent_claims": "청구항 2는 장력 풀리가 홀더에 이동 가능하게 지지되는 조건을 추가한다.",
                "operation_principle_steps": ["스프링이 장력 풀리를 케이블 방향으로 가압한다.", "장력 풀리가 케이블의 느슨함을 보상한다."],
                "technical_effects": "케이블 장력을 안정적으로 유지할 수 있다.",
                "technology_classification": "Tension / Slack Management 계열 기술이다.",
                "core_technology_summary": "케이블 길이 변화에 대응해 장력을 유지하는 기계적 보상 구조가 핵심이다.",
                "evidence_note": "세부 원문은 Evidence 탭에서 확인할 수 있다.",
            }
        raise AssertionError(schema_name)


def test_integrated_pipeline_uses_two_module1_llm_calls():
    raw = parse_patent_text(SAMPLE_PATENT_TEXT, filename="sample.pdf")
    kb = load_all_knowledge()
    llm = FakeLLM()

    structured, trace = extract_structured_patent(raw_patent=raw, knowledge_base=kb, llm=llm)
    assert structured["independent_claims"][0]["claim_elements"][0]["canonical_name"] == "Drive Cable"
    assert structured["problem_assertions"][0]["problem_id"] == "P-FLX-01"
    assert structured["technology_assignments"][0]["technology_id"] == "T2.6"
    assert trace["model"] == "fake-model"
    assert trace["pipeline"] == "integrated_2_call_module1"
    assert llm.calls == ["psd_integrated_patent_extraction"]

    report = generate_module1_report(structured_patent=structured, llm=llm)
    assert "케이블 장력" in report["three_line_summary"]["what_is_patent"]
    assert llm.calls == ["psd_integrated_patent_extraction", "psd_module1_explanation_report"]
