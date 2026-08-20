import json
from html import escape

import streamlit as st

from engine.app_service import analyze_patent, analyze_related_patents
from engine.patent.parser import PatentParseError
from engine.patent.retriever import PatentRetrievalError
from engine.reports.figures import select_representative_figures

st.set_page_config(
    page_title="PSD Patent Intelligence",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Deployment UI: report-first, visual, and readable on desktop/mobile.
st.markdown(
    """
    <style>
      :root {--psd-blue:#2563eb; --psd-blue2:#0ea5e9; --psd-line:rgba(100,116,139,.20);}
      #MainMenu, footer {visibility:hidden;}
      .block-container {max-width:1180px; padding-top:1.7rem; padding-bottom:5rem;}
      .psd-hero {
        position:relative; overflow:hidden; padding:2.05rem 2.2rem;
        border:1px solid rgba(37,99,235,.16); border-radius:24px; margin-bottom:1.25rem;
        background:linear-gradient(135deg, rgba(37,99,235,.10), rgba(14,165,233,.04) 52%, rgba(255,255,255,.02));
        box-shadow:0 14px 42px rgba(15,23,42,.07);
      }
      .psd-hero:after {content:""; position:absolute; width:230px; height:230px; border-radius:50%; right:-70px; top:-100px; background:rgba(37,99,235,.08);}
      .psd-kicker {font-size:.76rem; font-weight:750; letter-spacing:.11em; text-transform:uppercase; color:var(--psd-blue); margin-bottom:.55rem;}
      .psd-hero h1 {margin:0 0 .45rem 0; font-size:2.35rem; letter-spacing:-.035em;}
      .psd-hero p {margin:0; opacity:.72; font-size:1rem; max-width:760px; line-height:1.65;}
      .summary-card {padding:1.22rem 1.25rem; border:1px solid var(--psd-line); border-radius:18px; min-height:164px; height:100%; background:rgba(148,163,184,.045);}
      .summary-icon {font-size:1.28rem; margin-bottom:.55rem;}
      .summary-card b {display:block; margin-bottom:.42rem; font-size:.93rem;}
      .summary-card span {font-size:.94rem; line-height:1.62; opacity:.88;}
      .meta-card {padding:.9rem 1rem; border:1px solid var(--psd-line); border-radius:15px; background:rgba(148,163,184,.045); min-height:84px;}
      .meta-label {font-size:.73rem; opacity:.60; margin-bottom:.25rem; letter-spacing:.02em;}
      .meta-value {font-weight:680; line-height:1.38; font-size:.94rem;}
      .quality-strip {display:flex; gap:.45rem; flex-wrap:wrap; margin:.95rem 0 1.25rem;}
      .quality-chip {display:inline-flex; align-items:center; gap:.3rem; padding:.38rem .67rem; border-radius:999px; font-size:.78rem; border:1px solid rgba(34,197,94,.20); background:rgba(34,197,94,.07);}
      .section-title {display:flex; align-items:center; gap:.72rem; margin:2.25rem 0 .9rem;}
      .section-no {width:2rem; height:2rem; display:inline-flex; align-items:center; justify-content:center; border-radius:10px; background:rgba(37,99,235,.10); color:var(--psd-blue); font-size:.82rem; font-weight:800;}
      .section-title h2 {margin:0; font-size:1.34rem; letter-spacing:-.02em;}
      .figure-caption {font-size:.79rem; line-height:1.48; opacity:.72; margin-top:.32rem;}
      .claim-label {display:inline-block; padding:.28rem .58rem; border-radius:8px; background:rgba(37,99,235,.10); color:var(--psd-blue); font-size:.76rem; font-weight:750; margin-bottom:.35rem;}
      .related-badge {display:inline-block; padding:.28rem .58rem; border-radius:999px; background:rgba(37,99,235,.10); color:var(--psd-blue); font-size:.78rem; font-weight:750;}
      .muted-note {font-size:.8rem; opacity:.65; line-height:1.5;}
      div[data-testid="stDataFrame"] {border-radius:14px; overflow:hidden; border:1px solid var(--psd-line);}
      div[data-testid="stForm"] {border-radius:20px !important; border-color:var(--psd-line) !important; padding:1.15rem 1.2rem .8rem !important;}
      div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:18px !important;}
      .stButton>button, .stLinkButton>a {border-radius:11px !important;}
      @media (max-width: 700px) {
        .block-container {padding-left:1rem; padding-right:1rem; padding-top:1rem;}
        .psd-hero {padding:1.45rem 1.25rem; border-radius:19px;}
        .psd-hero h1 {font-size:1.85rem;}
        .summary-card {min-height:auto;}
      }
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


def _section_header(number: str, title: str) -> None:
    st.markdown(
        f'<div class="section-title"><span class="section-no">{escape(str(number))}</span><h2>{escape(title)}</h2></div>',
        unsafe_allow_html=True,
    )


def _render_quality_strip(result: dict) -> None:
    q = result.get("quality") or {}
    chips = []
    if q.get("source_ready"):
        chips.append("✓ 공개 원문 확인")
    if q.get("independent_claim_count"):
        chips.append(f"✓ 독립청구항 {q.get('independent_claim_count')}개")
    if q.get("grounded_fact_count"):
        chips.append(f"✓ 원문 근거 {q.get('grounded_fact_count')}건")
    if q.get("figure_count"):
        chips.append(f"✓ 특허 도면 {q.get('figure_count')}개")
    if result.get("cache_hit"):
        chips.append("⚡ 검증된 분석 캐시 사용")
    if chips:
        html = ''.join(f'<span class="quality-chip">{escape(x)}</span>' for x in chips)
        st.markdown(f'<div class="quality-strip">{html}</div>', unsafe_allow_html=True)


def _render_patent_figures(result: dict, *, limit: int = 3) -> None:
    figures = select_representative_figures(result, limit=limit)
    if not figures:
        return
    st.markdown("#### 도면으로 보는 핵심 구조")
    st.caption("해당 특허의 실제 공개 도면입니다. 도면 선택은 명세서의 FIG 설명과 분석된 핵심 구성요소를 기준으로 하며, 청구범위 판단은 청구항 원문을 우선합니다.")
    cols = st.columns(min(3, len(figures)))
    for idx, figure in enumerate(figures):
        with cols[idx % len(cols)]:
            try:
                st.image(figure.get("image_url"), use_container_width=True)
            except Exception:
                st.caption("도면을 불러오지 못했습니다.")
            st.markdown(f"**{_safe(figure.get('label'), 'Patent Figure')}**")
            if figure.get("caption"):
                st.markdown(
                    f'<div class="figure-caption">{escape(_safe(figure.get("caption")))}</div>',
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
        if result.get("status") in {"Claim parsing failed", "Independent claim validation failed"}:
            st.error("독립청구항을 안정적으로 확인하지 못해 전체 특허 분석을 중단했습니다. 다른 특허번호를 입력하거나 텍스트형 PDF를 업로드해 주세요.")
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

    _render_quality_strip(result)

    if "deterministic fallback" in (result.get("overview") or ""):
        st.warning("설명 생성 모델이 일시적으로 응답하지 않아, 구조화된 특허 분석 결과를 바탕으로 기본 설명을 표시하고 있습니다.")

    summary = report.get("three_line_summary") or {}
    st.markdown("## 핵심 요약")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f'<div class="summary-card"><div class="summary-icon">◉</div><b>이 특허는 무엇인가?</b><span>{escape(_safe(summary.get("what_is_patent")))}</span></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div class="summary-card"><div class="summary-icon">↳</div><b>어떻게 해결하는가?</b><span>{escape(_safe(summary.get("how_it_solves")))}</span></div>',
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            f'<div class="summary-card"><div class="summary-icon">◆</div><b>무엇이 핵심인가?</b><span>{escape(_safe(summary.get("key_point")))}</span></div>',
            unsafe_allow_html=True,
        )

    _section_header("01", "특허 기본정보")
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

    _section_header("02", "핵심 과제")
    st.write(_safe(report.get("core_problem")))

    _section_header("03", "독립청구항 핵심구성")
    _render_patent_figures(result)
    independent_claims = report.get("independent_claims") or []
    if not independent_claims:
        st.write("독립청구항 설명이 생성되지 않았습니다.")
    for claim in independent_claims:
        claim_no = claim.get("claim_number")
        with st.container(border=True):
            st.markdown(f'<span class="claim-label">Independent Claim {claim_no}</span>', unsafe_allow_html=True)
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

    _section_header("04", "종속청구항의 추가조건")
    st.write(_safe(report.get("dependent_claims")))

    _section_header("05", "작동원리")
    steps = report.get("operation_principle_steps") or []
    if steps:
        for idx, step in enumerate(steps, start=1):
            with st.container(border=True):
                st.markdown(f"**STEP {idx:02d}**  ·  {step}")
    else:
        st.write("작동 순서를 명확히 구성하지 못했습니다.")

    _section_header("06", "기술 효과")
    st.write(_safe(report.get("technical_effects")))

    _section_header("07", "PSD 기술분류")
    st.write(_safe(report.get("technology_classification")))

    _section_header("08", "핵심 기술 요약")
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
                    "기술 관련도": item.get("relatedness_level") or "-",
                    "구조 유사도": f"{float(item.get('score', 0)):.0f}/100",
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
            c1, c2 = st.columns([3.6, 1.4])
            with c1:
                st.markdown(f"### {idx}. {number} · {title}")
                if item.get("applicant"):
                    st.caption(f"출원인: {item.get('applicant')}")
            with c2:
                st.markdown(f'<span class="related-badge">기술 관련도 {escape(_safe(item.get("relatedness_level"), "-") )}</span>', unsafe_allow_html=True)
                st.caption(f"구조 유사도 {float(item.get('score', 0)):.0f}/100")

            if item.get("source_url"):
                st.link_button("공개 특허 원문 보기", item.get("source_url"))

            figure = item.get("representative_figure") or {}
            if figure.get("image_url"):
                img_col, text_col = st.columns([1, 2.15])
                with img_col:
                    st.image(figure.get("image_url"), use_container_width=True)
                    st.caption(figure.get("label") or "Patent Figure")
                with text_col:
                    st.markdown("**왜 관련된 특허인가?**")
                    st.write(_safe(item.get("selection_reason")))
                    if item.get("psd_relevance_reason"):
                        st.caption("PSD 관련성: " + item.get("psd_relevance_reason"))
            else:
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
fallback_model = _secret("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
try:
    max_retries = int(_secret("GEMINI_MAX_RETRIES", 2))
except Exception:
    max_retries = 2
show_developer_tools = bool(_secret("SHOW_DEVELOPER_TOOLS", False))

st.markdown(
    """
    <div class="psd-hero">
      <div class="psd-kicker">Power Sliding Door Patent Analysis</div>
      <h1>PSD Patent Intelligence</h1>
      <p>특허번호 하나로 원문·청구항·실제 도면을 함께 읽고, 핵심 기술과 관련 공개 특허를 이해하기 쉬운 엔지니어링 보고서로 정리합니다.</p>
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
                    fallback_model=fallback_model,
                    max_retries=max_retries,
                )
                st.session_state.analysis_result = result
                st.session_state.module2_result = None
                st.session_state.module2_for_patent = None
                if result.get("analysis_error") or result.get("status") in {"Claim parsing failed", "Independent claim validation failed"}:
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
                            fallback_model=fallback_model,
                            max_retries=max_retries,
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
