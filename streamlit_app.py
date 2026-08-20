import streamlit as st
from engine.app_service import analyze_patent

st.set_page_config(
    page_title="PSD Patent Intelligence",
    page_icon="📘",
    layout="wide",
)

st.title("PSD Patent Intelligence")
st.caption("Power Sliding Door 특허를 Ontology 기반으로 분석하는 웹 서비스")

with st.sidebar:
    st.header("Patent Input")
    patent_number = st.text_input(
        "특허번호",
        placeholder="예: JP7604988B2",
    )
    uploaded_file = st.file_uploader("또는 특허 PDF 업로드", type=["pdf"])
    analyze_clicked = st.button("특허 분석 시작", type="primary", use_container_width=True)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if analyze_clicked:
    if not patent_number and uploaded_file is None:
        st.warning("특허번호를 입력하거나 PDF를 업로드해 주세요.")
    else:
        with st.status("PSD 특허 분석 준비 중...", expanded=True) as status:
            st.write("1. 입력 데이터 확인")
            st.write("2. Patent Parser 준비")
            st.write("3. PSD Ontology Mapping 준비")
            st.write("4. Module 1·2·3 결과 생성 준비")
            result = analyze_patent(
                patent_number=patent_number.strip() or None,
                uploaded_file_name=uploaded_file.name if uploaded_file else None,
            )
            st.session_state.analysis_result = result
            status.update(label="MVP 분석 화면 생성 완료", state="complete")

result = st.session_state.analysis_result

if result is None:
    st.info(
        "왼쪽에서 특허번호를 입력하거나 PDF를 업로드한 뒤 ‘특허 분석 시작’을 눌러 주세요. "
        "현재 버전은 GitHub/배포 구조 확인용 MVP이며, 다음 단계에서 실제 LLM·특허 검색 엔진을 연결합니다."
    )
else:
    st.subheader(result["title"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Patent", result["patent_number"])
    c2.metric("Primary Technology", result["primary_technology"])
    c3.metric("Status", result["status"])

    tabs = st.tabs([
        "Overview",
        "Module 1 · Patent Analysis",
        "Module 2 · Related Patents",
        "Module 3 · Technology Intelligence",
        "Evidence",
    ])

    with tabs[0]:
        st.markdown(result["overview"])

    with tabs[1]:
        m1 = result["module1"]
        st.markdown("### 1. 특허 기본정보")
        st.json(m1["basic_info"], expanded=False)
        st.markdown("### 2. 핵심 과제")
        st.write(m1["core_problem"])
        st.markdown("### 3. 독립청구항 분석")
        st.write("**필수 구성요소**")
        st.dataframe(m1["claim_elements"], use_container_width=True, hide_index=True)
        st.write("**구성요소 관계**")
        st.dataframe(m1["relations"], use_container_width=True, hide_index=True)
        st.markdown("### 4. 종속청구항의 추가조건")
        st.write(m1["dependent_claims"])
        st.markdown("### 5. 작동원리")
        st.write(m1["operation_principle"])
        st.markdown("### 6. 기술 효과")
        st.write(m1["effects"])
        st.markdown("### 7. PSD 기술분류")
        st.write(m1["technology_classification"])
        st.markdown("### 8. 핵심 기술 요약")
        st.write(m1["summary"])

    with tabs[2]:
        st.caption("다음 단계에서 실제 특허 검색 + Ontology 기반 재정렬을 연결합니다.")
        st.dataframe(result["module2"]["related_patents"], use_container_width=True, hide_index=True)
        st.markdown("### 비교 요약")
        st.write(result["module2"]["comparison_summary"])

    with tabs[3]:
        st.caption("다음 단계에서 관련 특허 Corpus를 기반으로 연도·기술분류·출원인 통계를 계산합니다.")
        st.markdown("### 기술 발전 흐름")
        st.write(result["module3"]["evolution"])
        st.markdown("### 최근 기술 트렌드")
        st.write(result["module3"]["trends"])
        st.markdown("### 기술적 한계")
        st.write(result["module3"]["limitations"])
        st.markdown("### 향후 발전 방향")
        st.write(result["module3"]["future_direction"])

    with tabs[4]:
        st.caption("향후 모든 Patent Fact는 Evidence/Provenance 객체와 연결됩니다.")
        for item in result["evidence"]:
            with st.expander(f'{item["label"]} · {item["source"]}'):
                st.write(item["text"])
