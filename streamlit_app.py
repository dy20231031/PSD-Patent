import json

import streamlit as st

from engine.app_service import analyze_patent
from engine.patent.parser import PatentParseError

st.set_page_config(
    page_title="PSD Patent Intelligence",
    page_icon="📘",
    layout="wide",
)

st.title("PSD Patent Intelligence")
st.caption("Power Sliding Door 특허를 Ontology로 구조화하고, 사람이 이해하기 쉬운 설명 보고서로 변환합니다.")


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


api_key = _secret("OPENAI_API_KEY")
openai_model = _secret("OPENAI_MODEL", "gpt-5.6-luna")
report_model = _secret("OPENAI_REPORT_MODEL", openai_model)

with st.sidebar:
    st.header("Patent Input")
    patent_number = st.text_input(
        "특허번호 (선택)",
        placeholder="예: JP7604988B2",
        help="PDF와 함께 입력하면 publication number 힌트로 사용합니다. 특허번호 자동 조회는 아직 연결되지 않았습니다.",
    )
    uploaded_file = st.file_uploader(
        "특허 PDF 업로드",
        type=["pdf"],
        help="텍스트형 PDF 권장. 스캔/이미지형 PDF OCR은 아직 지원하지 않습니다.",
    )
    st.divider()
    st.markdown("**Analysis Engine**")
    if api_key:
        st.success(f"LLM configured · {openai_model}")
        st.caption("PDF Parser + PSD Ontology Extraction + Module 1 Explanation")
    else:
        st.warning("OpenAI API Key 미설정")
        st.caption("현재는 PDF Parser까지만 동작합니다. Streamlit Secrets에 OPENAI_API_KEY를 설정하면 Module 1 분석이 활성화됩니다.")
    analyze_clicked = st.button("특허 분석 시작", type="primary", use_container_width=True)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if analyze_clicked:
    if not patent_number and uploaded_file is None:
        st.warning("특허번호를 입력하거나 PDF를 업로드해 주세요.")
    else:
        try:
            with st.status("PSD 특허 분석 중...", expanded=True) as status:
                uploaded_bytes = uploaded_file.getvalue() if uploaded_file is not None else None
                if uploaded_bytes is not None:
                    st.write("1. PDF text extraction 및 Patent Parser")
                    st.write("2. Metadata / Abstract / Claims / Description 구조화")
                    if api_key:
                        st.write("3. Context Router")
                        st.write("4. PSD Ontology Extraction 및 Canonical Vocabulary 정규화")
                        st.write("5. Structured Patent JSON 검증")
                        st.write("6. 이해하기 쉬운 Module 1 설명 보고서 생성")
                    else:
                        st.write("3. LLM 분석은 API Key 설정 후 활성화")

                result = analyze_patent(
                    patent_number=patent_number.strip() or None,
                    uploaded_file_name=uploaded_file.name if uploaded_file else None,
                    uploaded_file_bytes=uploaded_bytes,
                    openai_api_key=api_key,
                    openai_model=openai_model,
                    report_model=report_model,
                )
                st.session_state.analysis_result = result
                if result.get("analysis_error"):
                    status.update(label="PDF 파싱 완료 · LLM 분석 오류", state="error")
                else:
                    status.update(label="분석 완료", state="complete")
        except PatentParseError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)

result = st.session_state.analysis_result

if result is None:
    st.info(
        "왼쪽에서 특허 PDF를 업로드한 뒤 ‘특허 분석 시작’을 눌러 주세요. "
        "API Key가 설정되어 있으면 Ontology 기반 Module 1 보고서까지 생성합니다."
    )
else:
    st.subheader(result["title"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Patent", result["patent_number"])
    c2.metric("Primary Technology", result["primary_technology"])
    c3.metric("Status", result["status"])

    if result.get("analysis_error"):
        st.error(result["analysis_error"])

    tabs = st.tabs([
        "Overview",
        "Module 1 · Patent Analysis",
        "Structured Analysis",
        "Raw Patent JSON",
        "Evidence",
        "Module 2 · Related Patents",
        "Module 3 · Technology Intelligence",
    ])

    with tabs[0]:
        st.markdown(result["overview"])
        raw_patent = result.get("raw_patent")
        if raw_patent:
            source = raw_patent.get("source", {})
            diagnostics = raw_patent.get("parser_diagnostics", {})
            metadata = raw_patent.get("metadata", {})
            st.markdown("### Parser 결과")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Pages", source.get("page_count") or 0)
            m2.metric("Characters", f"{source.get('text_char_count') or 0:,}")
            m3.metric("Claims", diagnostics.get("claim_count", 0))
            m4.metric("Independent Claims", diagnostics.get("independent_claim_count", 0))
            st.markdown("### 추출된 기본정보")
            st.json(
                {
                    "publication_number": metadata.get("publication_number"),
                    "title": metadata.get("title"),
                    "applicant": metadata.get("applicant"),
                    "filename": metadata.get("filename"),
                },
                expanded=False,
            )
            for warning in diagnostics.get("warnings", []):
                st.warning(warning)

        structured = result.get("structured_patent")
        if structured:
            st.markdown("### Ontology 분석 상태")
            a, b, c, d = st.columns(4)
            a.metric("Independent Claims", len(structured.get("independent_claims", [])))
            b.metric("Problems", len(structured.get("problem_assertions", [])))
            c.metric("Effects", len(structured.get("effect_assertions", [])))
            d.metric("Validation Warnings", len(structured.get("validation_warnings", [])))
            if structured.get("validation_warnings"):
                with st.expander("Mapping / Validation 경고 보기"):
                    for warning in structured["validation_warnings"]:
                        st.write(f"- {warning}")

    with tabs[1]:
        report = result.get("module1_report")
        if not report:
            st.info("Ontology 기반 Module 1 보고서는 OpenAI API Key를 설정하면 생성됩니다.")
            m1 = result["module1"]
            st.markdown("### Parser에서 확인된 기본정보")
            st.json(m1["basic_info"], expanded=False)
        else:
            summary = report["three_line_summary"]
            st.markdown("### 3줄 핵심 요약")
            st.info(f"**이 특허는 무엇인가?**\n\n{summary['what_is_patent']}")
            st.info(f"**어떻게 해결하는가?**\n\n{summary['how_it_solves']}")
            st.info(f"**무엇이 핵심인가?**\n\n{summary['key_point']}")

            raw_meta = result.get("raw_patent", {}).get("metadata", {})
            st.markdown("### 1. 특허 기본정보")
            st.dataframe([
                {"항목": "공개/등록번호", "내용": raw_meta.get("publication_number") or result["patent_number"]},
                {"항목": "특허명", "내용": raw_meta.get("title") or "자동 추출되지 않음"},
                {"항목": "출원인", "내용": raw_meta.get("applicant") or "자동 추출되지 않음"},
            ], use_container_width=True, hide_index=True)

            st.markdown("### 2. 핵심 과제")
            st.write(report["core_problem"])

            st.markdown("### 3. 독립청구항")
            for claim in report["independent_claims"]:
                with st.container(border=True):
                    st.markdown(f"#### 청구항 {claim['claim_number']}")
                    st.write(claim["plain_explanation"])
                    st.markdown("**필수 구성요소**")
                    st.dataframe(
                        [
                            {
                                "구성요소": e["name"],
                                "원문 표현": e["original_expression"],
                                "쉽게 설명하면": e["explanation"],
                            }
                            for e in claim["claim_elements"]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.markdown("**구성요소 간 관계**")
                    st.write(claim["relation_explanation"])
                    st.markdown("**핵심 청구조건**")
                    if claim["core_conditions"]:
                        for condition in claim["core_conditions"]:
                            st.write(f"- {condition}")
                    else:
                        st.write("추가적인 구조화 조건이 명확히 식별되지 않았습니다.")
                    st.caption(claim["scope_note"])

            st.markdown("### 4. 종속청구항의 추가조건")
            st.write(report["dependent_claims"])
            st.markdown("### 5. 작동원리")
            for idx, step in enumerate(report["operation_principle_steps"], start=1):
                st.write(f"**{idx}.** {step}")
            st.markdown("### 6. 기술 효과")
            st.write(report["technical_effects"])
            st.markdown("### 7. PSD 기술분류")
            st.write(report["technology_classification"])
            st.markdown("### 8. 핵심 기술 요약")
            st.write(report["core_technology_summary"])
            st.caption(report["evidence_note"])

            report_bytes = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                "Module 1 Report JSON 다운로드",
                data=report_bytes,
                file_name=f"{result['patent_number']}_module1_report.json",
                mime="application/json",
                use_container_width=True,
            )

    with tabs[2]:
        structured = result.get("structured_patent")
        if not structured:
            st.info("LLM Ontology 분석이 완료되면 이 탭에 Canonical Mapping 결과가 표시됩니다.")
        else:
            st.caption("이 탭은 개발/검증용입니다. 일반 보고서에는 내부 Ontology ID를 기본 노출하지 않습니다.")
            for claim in structured.get("independent_claims", []):
                st.markdown(f"### Claim {claim.get('claim_number')}")
                st.markdown("**Claim Elements**")
                st.dataframe([
                    {
                        "Instance": e.get("element_instance_id"),
                        "Canonical ID": e.get("master_element_id"),
                        "Canonical Name": e.get("canonical_name"),
                        "Original": e.get("original_expression"),
                        "Status": e.get("normalization_status"),
                    }
                    for e in claim.get("claim_elements", [])
                ], use_container_width=True, hide_index=True)
                st.markdown("**Relations**")
                st.dataframe([
                    {
                        "Subject": r.get("subject_instance_id"),
                        "Relation": r.get("canonical_relation"),
                        "Object": r.get("object_instance_id") or ", ".join(r.get("object_set", [])),
                        "Status": r.get("normalization_status"),
                    }
                    for r in claim.get("relation_assertions", [])
                ], use_container_width=True, hide_index=True)

            st.markdown("### Problem / Effect")
            st.json({
                "problems": structured.get("problem_assertions", []),
                "effects": structured.get("effect_assertions", []),
                "technology": structured.get("technology_assignments", []),
                "architecture": structured.get("architecture_assignments", []),
            }, expanded=False)
            structured_bytes = json.dumps(structured, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                "Structured Patent JSON 다운로드",
                data=structured_bytes,
                file_name=f"{result['patent_number']}_structured_patent.json",
                mime="application/json",
                use_container_width=True,
            )

    with tabs[3]:
        raw_patent = result.get("raw_patent")
        if not raw_patent:
            st.info("PDF를 업로드하면 Raw Patent JSON이 생성됩니다.")
        else:
            diagnostics = raw_patent.get("parser_diagnostics", {})
            claims = raw_patent.get("claims", [])
            st.markdown("### 탐지된 섹션")
            sections = diagnostics.get("sections_found", [])
            st.write(", ".join(sections) if sections else "탐지된 표준 heading 없음")
            st.markdown("### Claims")
            if claims:
                st.dataframe([
                    {
                        "Claim": claim.get("claim_number"),
                        "Type": claim.get("claim_type"),
                        "Depends on": ", ".join(map(str, claim.get("depends_on", []))) or "-",
                        "Preview": claim.get("text", "")[:240],
                    }
                    for claim in claims
                ], use_container_width=True, hide_index=True)
            display_json = dict(raw_patent)
            raw_text = display_json.get("raw_text", "")
            display_json["raw_text"] = f"<UI에서 생략: {len(raw_text):,} characters>"
            st.json(display_json, expanded=False)
            json_bytes = json.dumps(raw_patent, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                "Raw Patent JSON 다운로드",
                data=json_bytes,
                file_name=f"{result['patent_number']}_raw_patent.json",
                mime="application/json",
                use_container_width=True,
            )

    with tabs[4]:
        evidence = result.get("evidence", [])
        if not evidence:
            st.info("Ontology 분석이 완료되면 Claim/Specification 원문 Evidence가 표시됩니다.")
        else:
            st.caption("보고서 설명의 근거가 된 원문 표현을 확인하는 검증용 화면입니다.")
            for item in evidence:
                title = f"{item['label']} · {item.get('canonical') or '-'} · {item['source']}"
                with st.expander(title):
                    if item.get("evidence_level"):
                        st.write(f"Evidence Level: **{item['evidence_level']}**")
                    if item.get("claim_id"):
                        st.write(f"Claim: **{item['claim_id']}**")
                    st.write(item["text"])

    with tabs[5]:
        st.caption("Module 2는 다음 단계에서 실제 공개특허 Retrieval + Ontology 기반 관련도 재정렬을 연결합니다.")
        st.dataframe(result["module2"]["related_patents"], use_container_width=True, hide_index=True)
        st.markdown("### 비교 요약")
        st.write(result["module2"]["comparison_summary"])

    with tabs[6]:
        st.caption("Module 3는 Module 2 관련 특허 Corpus를 기반으로 기술 흐름/트렌드를 계산하도록 연결할 예정입니다.")
        st.markdown("### 기술 발전 흐름")
        st.write(result["module3"]["evolution"])
        st.markdown("### 최근 기술 트렌드")
        st.write(result["module3"]["trends"])
        st.markdown("### 기술적 한계")
        st.write(result["module3"]["limitations"])
        st.markdown("### 향후 발전 방향")
        st.write(result["module3"]["future_direction"])
