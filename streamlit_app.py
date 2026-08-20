import json
from html import escape

import streamlit as st

from engine.app_service import analyze_patent, analyze_related_patents
from engine.patent.parser import PatentParseError
from engine.patent.retriever import PatentRetrievalError

st.set_page_config(
    page_title="PSD Patent Intelligence",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Deployment UI: keep the public page report-first and hide implementation details.
st.markdown(
    """
    <style>
      .block-container {max-width: 1120px; padding-top: 2.2rem; padding-bottom: 4rem;}
      .psd-hero {padding: 1.6rem 1.8rem; border: 1px solid rgba(128,128,128,.22); border-radius: 18px; margin-bottom: 1.2rem;}
      .psd-kicker {font-size: .82rem; letter-spacing: .08em; text-transform: uppercase; opacity: .68; margin-bottom: .3rem;}
      .psd-hero h1 {margin: 0 0 .35rem 0; font-size: 2.15rem;}
      .psd-hero p {margin: 0; opacity: .78;}
      .summary-card {padding: 1rem 1.1rem; border: 1px solid rgba(128,128,128,.22); border-radius: 14px; height: 100%;}
      .summary-card b {display:block; margin-bottom:.35rem;}
      .meta-card {padding: .75rem 1rem; border-radius: 12px; background: rgba(128,128,128,.07); min-height: 76px;}
      .meta-label {font-size: .78rem; opacity: .65; margin-bottom:.2rem;}
      .meta-value {font-weight: 650; line-height: 1.3;}
      .section-gap {height:.35rem;}
      div[data-testid="stDataFrame"] {border-radius: 12px; overflow: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def _safe(value, fallback="확인되지 않음"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _render_meta_card(label: str, value: str) -> None:
    st.markdown(
        f'<div class="meta-card"><div class="meta-label">{escape(label)}</div><div class="meta-value">{escape(_safe(value))}</div></div>',
        unsafe_allow_html=True,
    )


def _render_evidence(evidence: list[dict]) -> None:
    if not evidence:
        st.caption("표시할 원문 근거가 없습니다.")
        return

    label_ko = {
        "Claim Element": "구성요소",
        "Relation": "구성요소 관계",
        "Function": "기능",
        "Claim Constraint": "청구조건",
        "State": "상태",
        "Operation Mode": "작동 모드",
        "Problem": "핵심 과제",
        "Effect": "기술 효과",
    }
    for item in evidence:
        title = label_ko.get(item.get("label"), item.get("label") or "근거")
        canonical = item.get("canonical")
        source = item.get("source") or "Patent"
        heading = f"{title} · {canonical}" if canonical else title
        with st.expander(heading):
            st.caption(f"근거 위치: {source}")
            st.write(item.get("text") or "-")


def _render_report(result: dict) -> None:
    report = result.get("module1_report")
    raw_patent = result.get("raw_patent") or {}
    metadata = raw_patent.get("metadata") or {}

    if not report:
        if result.get("status") == "Claim parsing failed":
            st.error("청구항을 안정적으로 식별하지 못해 전체 특허 분석을 중단했습니다. 다른 특허번호를 입력하거나 텍스트형 PDF를 업로드해 주세요.")
        elif not api_key:
            st.error("분석 서비스의 Gemini API 설정이 완료되지 않았습니다.")
        else:
            st.error("분석 보고서를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return

    st.markdown("---")
    st.markdown(f"## {_safe(metadata.get('title'), result.get('title'))}")

    m1, m2, m3 = st.columns([1, 1.4, 1.2])
    with m1:
        _render_meta_card("공개/등록번호", metadata.get("publication_number") or result.get("patent_number"))
    with m2:
        _render_meta_card("출원인", metadata.get("applicant"))
    with m3:
        _render_meta_card("주요 PSD 기술", result.get("primary_technology"))

    source_url = (raw_patent.get("source") or {}).get("source_url")
    if source_url:
        st.link_button("공개 특허 원문 보기", source_url)

    if "deterministic fallback" in (result.get("overview") or ""):
        st.warning("설명 생성 모델이 일시적으로 응답하지 않아, 구조화된 특허 분석 결과를 바탕으로 기본 설명을 표시하고 있습니다.")

    summary = report.get("three_line_summary") or {}
    st.markdown("## 핵심 요약")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f'<div class="summary-card"><b>이 특허는 무엇인가?</b>{escape(_safe(summary.get("what_is_patent")))}</div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div class="summary-card"><b>어떻게 해결하는가?</b>{escape(_safe(summary.get("how_it_solves")))}</div>',
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            f'<div class="summary-card"><b>무엇이 핵심인가?</b>{escape(_safe(summary.get("key_point")))}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("## 1. 특허 기본정보")
    basic_rows = [
        {"항목": "공개/등록번호", "내용": _safe(metadata.get("publication_number") or result.get("patent_number"))},
        {"항목": "특허명", "내용": _safe(metadata.get("title"))},
        {"항목": "출원인", "내용": _safe(metadata.get("applicant"))},
    ]
    # Add dates only when the parser/retriever actually has them.
    optional_meta = [
        ("출원번호", metadata.get("application_number")),
        ("우선일", metadata.get("priority_date")),
        ("출원일", metadata.get("filing_date")),
        ("공개/등록일", metadata.get("publication_date")),
    ]
    for label, value in optional_meta:
        if value:
            basic_rows.append({"항목": label, "내용": value})
    st.dataframe(basic_rows, use_container_width=True, hide_index=True)

    st.markdown("## 2. 핵심 과제")
    st.write(_safe(report.get("core_problem")))

    st.markdown("## 3. 독립청구항 핵심구성")
    independent_claims = report.get("independent_claims") or []
    if not independent_claims:
        st.write("독립청구항 설명이 생성되지 않았습니다.")
    for claim in independent_claims:
        claim_no = claim.get("claim_number")
        with st.container(border=True):
            st.markdown(f"### 청구항 {claim_no}")
            st.write(_safe(claim.get("plain_explanation")))

            elements = claim.get("claim_elements") or []
            if elements:
                st.markdown("**주요 구성요소**")
                st.dataframe(
                    [
                        {
                            "구성요소": _safe(e.get("name")),
                            "특허 원문 표현": _safe(e.get("original_expression"), "-"),
                            "쉽게 설명하면": _safe(e.get("explanation")),
                        }
                        for e in elements
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("**구성요소 간 관계**")
            st.write(_safe(claim.get("relation_explanation")))

            conditions = claim.get("core_conditions") or []
            st.markdown("**핵심 청구조건**")
            if conditions:
                for condition in conditions:
                    st.write(f"- {condition}")
            else:
                st.write("추가로 구조화된 핵심 조건이 명확히 식별되지 않았습니다.")

            if claim.get("scope_note"):
                st.caption(claim.get("scope_note"))

    st.markdown("## 4. 종속청구항의 추가조건")
    st.write(_safe(report.get("dependent_claims")))

    st.markdown("## 5. 작동원리")
    steps = report.get("operation_principle_steps") or []
    if steps:
        for idx, step in enumerate(steps, start=1):
            st.markdown(f"**{idx}.** {step}")
    else:
        st.write("작동 순서를 명확히 구성하지 못했습니다.")

    st.markdown("## 6. 기술 효과")
    st.write(_safe(report.get("technical_effects")))

    st.markdown("## 7. PSD 기술분류")
    st.write(_safe(report.get("technology_classification")))

    st.markdown("## 8. 핵심 기술 요약")
    st.info(_safe(report.get("core_technology_summary")))

    st.markdown("---")
    with st.expander("분석 근거 보기"):
        st.caption("보고서 내용은 공개 특허의 청구항과 명세서에서 확인되는 근거를 우선하여 작성합니다.")
        _render_evidence(result.get("evidence") or [])

    report_bytes = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        "분석 결과 저장",
        data=report_bytes,
        file_name=f"{result.get('patent_number', 'patent')}_analysis_report.json",
        mime="application/json",
    )


def _render_module2(module2: dict | None) -> None:
    if not module2:
        st.caption("관련 특허 분석을 아직 실행하지 않았습니다.")
        return

    status = module2.get("status")
    if status != "completed":
        message = module2.get("overview") or "관련 특허 분석을 완료하지 못했습니다."
        if status in {"search_failed", "candidate_analysis_failed"}:
            st.error(message)
        else:
            st.warning(message)
        return

    st.markdown("## 관련 공개 특허")
    st.write(_safe(module2.get("overview")))
    st.caption("관련도 점수는 공개 특허의 PSD Ontology 특징을 비교한 기술적 유사도이며, 법적 유사성·침해 판단을 의미하지 않습니다.")

    patents = module2.get("related_patents") or []
    if patents:
        st.dataframe(
            [
                {
                    "순위": idx,
                    "관련도": f"{float(item.get('score', 0)):.1f}%",
                    "공개번호": item.get("publication_number") or "-",
                    "특허명": item.get("title") or "-",
                    "출원인": item.get("applicant") or "-",
                    "공개일": item.get("publication_date") or "-",
                }
                for idx, item in enumerate(patents, start=1)
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("## 관련 특허 선정 이유 및 비교")
    for idx, item in enumerate(patents, start=1):
        number = item.get("publication_number") or f"Related Patent {idx}"
        title = item.get("title") or "특허명 확인되지 않음"
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"### {idx}. {number} · {title}")
                if item.get("applicant"):
                    st.caption(f"출원인: {item.get('applicant')}")
            with c2:
                st.metric("관련도", f"{float(item.get('score', 0)):.1f}%")

            if item.get("source_url"):
                st.link_button("공개 특허 원문 보기", item.get("source_url"))

            st.markdown("**왜 관련된 특허인가?**")
            st.write(_safe(item.get("selection_reason")))

            if item.get("solution_summary"):
                st.markdown("**관련 특허의 해결 방식**")
                st.write(item.get("solution_summary"))

            st.markdown("**공통 기술 과제**")
            st.write(_safe(item.get("shared_problem")))

            common = item.get("common_points") or []
            st.markdown("**공통점**")
            if common:
                for x in common:
                    st.write(f"- {x}")
            else:
                st.write("명확한 공통 구조가 별도로 정리되지 않았습니다.")

            differences = item.get("differences") or []
            st.markdown("**차이점**")
            if differences:
                for x in differences:
                    st.write(f"- {x}")
            else:
                st.write("구체적인 차이점이 별도로 정리되지 않았습니다.")

            st.markdown("**기술적 발전·변형 요소**")
            st.write(_safe(item.get("technical_development")))

            if show_developer_tools:
                with st.expander("유사도 세부 점수"):
                    st.json(item.get("score_breakdown") or {}, expanded=False)

    st.markdown("## 종합 비교")
    st.info(_safe(module2.get("comparison_summary")))

    with st.expander("관련 특허 선정 방법"):
        st.write(_safe(module2.get("selection_method")))
        if show_developer_tools:
            st.write("검색 Query")
            st.code("\n".join(module2.get("search_queries") or []))
            warnings = module2.get("warnings") or []
            if warnings:
                st.write("Warnings")
                st.json(warnings, expanded=False)


api_key = _secret("GEMINI_API_KEY")
gemini_model = _secret("GEMINI_MODEL", "gemini-3.7-flash")
report_model = _secret("GEMINI_REPORT_MODEL", gemini_model)
show_developer_tools = bool(_secret("SHOW_DEVELOPER_TOOLS", False))

st.markdown(
    """
    <div class="psd-hero">
      <div class="psd-kicker">Power Sliding Door Patent Analysis</div>
      <h1>PSD Patent Intelligence</h1>
      <p>공개 특허를 입력하면 핵심 과제와 청구구조를 설명하고, 관련 공개 특허까지 PSD Ontology 기준으로 비교합니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("patent_input_form", border=True):
    st.markdown("### 분석할 특허")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        patent_number = st.text_input(
            "특허번호",
            placeholder="예: US10774572B2",
            help="공개/등록번호를 입력하면 공개 특허 원문을 조회합니다.",
        )
    with c2:
        uploaded_file = st.file_uploader(
            "또는 특허 PDF 업로드",
            type=["pdf"],
            help="PDF를 함께 올리면 PDF 분석을 우선합니다. 텍스트형 PDF를 권장합니다.",
        )
    analyze_clicked = st.form_submit_button("특허 분석 시작", type="primary", use_container_width=True)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "module2_result" not in st.session_state:
    st.session_state.module2_result = None
if "module2_for_patent" not in st.session_state:
    st.session_state.module2_for_patent = None

if analyze_clicked:
    if not patent_number and uploaded_file is None:
        st.warning("특허번호를 입력하거나 PDF를 업로드해 주세요.")
    else:
        try:
            with st.status("특허를 분석하고 있습니다...", expanded=True) as status:
                uploaded_bytes = uploaded_file.getvalue() if uploaded_file is not None else None
                st.write("특허 원문을 읽고 있습니다.")
                st.write("청구항과 명세서 구조를 파악하고 있습니다.")
                if api_key:
                    st.write("PSD 기술구조와 핵심 관계를 분석하고 있습니다.")
                    st.write("이해하기 쉬운 보고서를 작성하고 있습니다.")
                else:
                    st.write("분석 서비스 설정을 확인하고 있습니다.")

                result = analyze_patent(
                    patent_number=patent_number.strip() or None,
                    uploaded_file_name=uploaded_file.name if uploaded_file else None,
                    uploaded_file_bytes=uploaded_bytes,
                    gemini_api_key=api_key,
                    gemini_model=gemini_model,
                    report_model=report_model,
                )
                st.session_state.analysis_result = result
                st.session_state.module2_result = None
                st.session_state.module2_for_patent = None
                if result.get("analysis_error") or result.get("status") == "Claim parsing failed":
                    status.update(label="분석을 완료하지 못했습니다.", state="error", expanded=False)
                else:
                    status.update(label="특허 분석이 완료되었습니다.", state="complete", expanded=False)
        except (PatentParseError, PatentRetrievalError) as exc:
            st.error(f"특허 원문을 불러오거나 읽는 중 문제가 발생했습니다. {exc}")
        except Exception as exc:
            if show_developer_tools:
                st.exception(exc)
            else:
                st.error("분석 중 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

result = st.session_state.analysis_result

if result is None:
    st.caption("특허번호 입력을 권장하며, 원문 조회가 어려운 경우 PDF를 직접 업로드할 수 있습니다.")
else:
    if result.get("analysis_error"):
        st.error("AI 분석 단계에서 일시적인 오류가 발생했습니다. 잠시 후 다시 분석해 주세요.")
        if show_developer_tools:
            st.code(result.get("analysis_error"))

    tab1, tab2 = st.tabs(["특허 분석", "관련 특허"])
    with tab1:
        _render_report(result)

    with tab2:
        if not result.get("structured_patent") or not result.get("module1_report"):
            st.info("먼저 Module 1 특허 분석이 정상적으로 완료되어야 관련 특허를 분석할 수 있습니다.")
        elif not api_key:
            st.warning("관련 특허 분석에는 Gemini API 설정이 필요합니다.")
        else:
            current_patent = result.get("patent_number")
            if st.session_state.module2_for_patent != current_patent:
                st.session_state.module2_result = None

            if st.session_state.module2_result is None:
                st.markdown("## 관련 특허 분석")
                st.write("현재 특허의 핵심 문제, 기능, 구성요소와 관계를 이용해 공개 특허 후보를 찾고 PSD Ontology 기준으로 관련도를 비교합니다.")
                st.caption("후보 특허의 청구항을 추가로 읽기 때문에 Module 1보다 시간이 조금 더 걸릴 수 있습니다.")
                if st.button("관련 특허 분석 시작", type="primary", use_container_width=True):
                    with st.status("관련 공개 특허를 분석하고 있습니다...", expanded=True) as m2_status:
                        st.write("Ontology 기반 검색어를 구성하고 있습니다.")
                        st.write("공개 특허 후보를 검색하고 있습니다.")
                        st.write("후보 특허의 청구항을 경량 Ontology 분석하고 있습니다.")
                        st.write("현재 특허와 비교하여 Top 5를 선정하고 있습니다.")
                        module2_result = analyze_related_patents(
                            result,
                            gemini_api_key=api_key,
                            gemini_model=gemini_model,
                            report_model=report_model,
                            top_n=5,
                        )
                        st.session_state.module2_result = module2_result
                        st.session_state.module2_for_patent = current_patent
                        if module2_result.get("status") == "completed":
                            m2_status.update(label="관련 특허 분석이 완료되었습니다.", state="complete", expanded=False)
                        else:
                            m2_status.update(label="관련 특허 분석을 완료하지 못했습니다.", state="error", expanded=False)
                    st.rerun()
            else:
                _render_module2(st.session_state.module2_result)
                if st.button("관련 특허 다시 분석", use_container_width=True):
                    st.session_state.module2_result = None
                    st.rerun()

# Optional owner-only diagnostics. Public deployment keeps this hidden by default.
if show_developer_tools and result:
    st.markdown("---")
    with st.expander("Developer tools"):
        st.warning("배포용 화면에서는 SHOW_DEVELOPER_TOOLS=false로 유지하세요.")
        st.markdown("#### Service status")
        st.json(
            {
                "status": result.get("status"),
                "overview": result.get("overview"),
                "primary_technology": result.get("primary_technology"),
            },
            expanded=False,
        )
        st.markdown("#### Structured Patent JSON")
        st.json(result.get("structured_patent") or {}, expanded=False)
        st.markdown("#### Raw Patent JSON")
        raw = dict(result.get("raw_patent") or {})
        raw_text = raw.get("raw_text", "")
        if raw_text:
            raw["raw_text"] = f"<hidden: {len(raw_text):,} characters>"
        st.json(raw, expanded=False)
