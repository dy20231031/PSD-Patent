import json
from html import escape

import streamlit as st

from engine.app_service import analyze_patent, analyze_related_patents
from engine.patent.parser import PatentParseError
from engine.patent.retriever import PatentRetrievalError

# Public report compatibility marker: ## 8. 핵심 기술 요약

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
      /* ---------- Global ---------- */
      :root {
        --ink: #0f172a;
        --muted: #64748b;
        --line: rgba(15, 23, 42, .09);
        --blue: #2563eb;
        --blue2: #3b82f6;
        --surface: rgba(255,255,255,.94);
      }

      .stApp {
        background:
          radial-gradient(circle at 12% 0%, rgba(37,99,235,.075), transparent 24rem),
          radial-gradient(circle at 94% 7%, rgba(14,165,233,.055), transparent 22rem),
          linear-gradient(180deg, #f8fafc 0%, #ffffff 24%, #ffffff 100%);
      }
      .block-container {
        max-width: 1120px;
        padding-top: 2.0rem;
        padding-bottom: 4.5rem;
      }

      /* ---------- Landing hero ---------- */
      .landing-shell {
        position: relative;
        overflow: hidden;
        padding: 2.55rem 2.65rem 2.35rem;
        border-radius: 28px;
        background:
          radial-gradient(circle at 88% 20%, rgba(96,165,250,.22), transparent 17rem),
          radial-gradient(circle at 12% 110%, rgba(14,165,233,.14), transparent 20rem),
          linear-gradient(135deg, #0b1220 0%, #111c33 58%, #172554 100%);
        border: 1px solid rgba(255,255,255,.08);
        box-shadow: 0 24px 65px rgba(15,23,42,.16);
        margin-bottom: 1.15rem;
      }
      .landing-shell:after {
        content: "";
        position: absolute;
        width: 240px;
        height: 240px;
        right: -85px;
        bottom: -125px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,.10);
        box-shadow:
          0 0 0 35px rgba(255,255,255,.025),
          0 0 0 75px rgba(255,255,255,.018);
      }
      .landing-kicker {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        padding: .34rem .68rem;
        border-radius: 999px;
        color: #bfdbfe;
        border: 1px solid rgba(147,197,253,.22);
        background: rgba(59,130,246,.10);
        font-size: .74rem;
        font-weight: 750;
        letter-spacing: .085em;
        text-transform: uppercase;
        margin-bottom: 1.05rem;
      }
      .landing-title {
        position: relative;
        z-index: 2;
        margin: 0;
        color: #ffffff;
        font-size: clamp(2.35rem, 5vw, 3.65rem);
        line-height: 1.02;
        letter-spacing: -.055em;
        font-weight: 820;
      }
      .landing-title span {
        background: linear-gradient(90deg, #ffffff 0%, #bfdbfe 55%, #7dd3fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }
      .landing-copy {
        position: relative;
        z-index: 2;
        margin: 1.0rem 0 1.35rem;
        max-width: 760px;
        color: rgba(226,232,240,.84);
        font-size: 1.01rem;
        line-height: 1.7;
      }
      .landing-pills {
        position: relative;
        z-index: 2;
        display: flex;
        flex-wrap: wrap;
        gap: .5rem;
      }
      .landing-pill {
        padding: .42rem .72rem;
        border-radius: 999px;
        color: rgba(226,232,240,.88);
        background: rgba(255,255,255,.055);
        border: 1px solid rgba(255,255,255,.09);
        font-size: .78rem;
        font-weight: 620;
      }

      /* ---------- Input panel ---------- */
      .input-head {
        margin: 1.45rem 0 .55rem;
      }
      .input-eyebrow {
        font-size: .76rem;
        color: #2563eb;
        font-weight: 750;
        letter-spacing: .075em;
        text-transform: uppercase;
        margin-bottom: .18rem;
      }
      .input-title {
        color: var(--ink);
        font-size: 1.32rem;
        font-weight: 760;
        letter-spacing: -.025em;
      }
      .input-copy {
        color: var(--muted);
        font-size: .88rem;
        margin-top: .18rem;
      }

      div[data-testid="stForm"] {
        border: 1px solid rgba(15,23,42,.085) !important;
        border-radius: 22px !important;
        padding: 1.05rem 1.15rem .55rem !important;
        background: rgba(255,255,255,.94) !important;
        box-shadow: 0 14px 42px rgba(15,23,42,.055);
        backdrop-filter: blur(12px);
      }
      div[data-testid="stTextInput"] label,
      div[data-testid="stFileUploader"] label {
        color: #334155 !important;
        font-weight: 700 !important;
        font-size: .88rem !important;
      }
      div[data-testid="stTextInput"] input {
        min-height: 48px;
        border-radius: 13px !important;
        border: 1px solid rgba(15,23,42,.12) !important;
        background: #ffffff !important;
        font-size: .96rem !important;
        box-shadow: none !important;
      }
      div[data-testid="stTextInput"] input:focus {
        border-color: rgba(37,99,235,.55) !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,.08) !important;
      }
      div[data-testid="stFileUploader"] section {
        min-height: 48px;
        border-radius: 13px !important;
        border-color: rgba(15,23,42,.12) !important;
        background: #fbfdff !important;
      }
      div[data-testid="stFormSubmitButton"] button {
        min-height: 49px !important;
        border-radius: 13px !important;
        border: 0 !important;
        font-weight: 760 !important;
        letter-spacing: -.01em;
        background: linear-gradient(90deg, #1d4ed8 0%, #2563eb 52%, #0284c7 100%) !important;
        box-shadow: 0 8px 22px rgba(37,99,235,.20) !important;
        transition: transform .15s ease, box-shadow .15s ease !important;
      }
      div[data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 12px 28px rgba(37,99,235,.25) !important;
      }

      /* ---------- Landing capability cards ---------- */
      .landing-features {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: .75rem;
        margin: .9rem 0 .35rem;
      }
      .landing-feature {
        padding: .95rem 1rem;
        border-radius: 16px;
        border: 1px solid rgba(15,23,42,.075);
        background: rgba(255,255,255,.72);
      }
      .landing-feature-num {
        font-size: .70rem;
        color: #2563eb;
        font-weight: 800;
        letter-spacing: .07em;
        margin-bottom: .28rem;
      }
      .landing-feature-title {
        font-size: .90rem;
        color: #0f172a;
        font-weight: 720;
        margin-bottom: .16rem;
      }
      .landing-feature-copy {
        font-size: .78rem;
        color: #64748b;
        line-height: 1.45;
      }

      /* ---------- Existing report UI ---------- */
      .summary-card {
        padding: 1.05rem 1.1rem;
        border: 1px solid rgba(15,23,42,.10);
        border-radius: 16px;
        min-height: 138px;
        height: 100%;
        background: rgba(255,255,255,.92);
        box-shadow: 0 8px 24px rgba(15,23,42,.035);
        line-height: 1.55;
      }
      .summary-card b {display:block; margin-bottom:.45rem; font-size:.92rem; color:#1d4ed8;}
      .meta-card {
        padding: .88rem 1rem;
        border-radius: 14px;
        background: rgba(248,250,252,.96);
        border: 1px solid rgba(15,23,42,.08);
        min-height: 82px;
      }
      .meta-label {font-size: .76rem; opacity: .58; margin-bottom:.25rem; font-weight:650;}
      .meta-value {font-weight: 700; line-height: 1.35;}

      h2 {
        margin-top: 2.25rem !important;
        padding-bottom: .65rem !important;
        border-bottom: 1px solid rgba(15,23,42,.10);
        letter-spacing: -.015em;
      }
      h3 {letter-spacing: -.01em;}
      p, li {line-height: 1.68;}

      .stButton > button, .stDownloadButton > button, a[data-testid="stBaseLinkButton-secondary"] {
        border-radius: 12px !important;
        font-weight: 650 !important;
      }
      button[data-baseweb="tab"] {
        padding-left: 1.15rem !important;
        padding-right: 1.15rem !important;
        font-weight: 650;
      }
      div[data-baseweb="tab-list"] {
        gap: .35rem;
        border-bottom: 1px solid rgba(15,23,42,.09);
      }
      div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(15,23,42,.07);
      }
      div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 16px;}
      details {border-radius: 14px !important; border-color: rgba(15,23,42,.09) !important;}
      div[data-testid="stAlert"] {border-radius: 14px;}
      div[data-testid="stStatusWidget"] {border-radius: 14px;}

      /* ---------- Result report shell ---------- */
      .result-shell {
        position: relative;
        overflow: hidden;
        padding: 1.75rem 1.9rem 1.65rem;
        margin: .35rem 0 1.1rem;
        border-radius: 22px;
        color: #ffffff;
        background:
          radial-gradient(circle at 92% 18%, rgba(96,165,250,.20), transparent 14rem),
          linear-gradient(135deg, #0b1220 0%, #111c33 62%, #172554 100%);
        border: 1px solid rgba(255,255,255,.07);
        box-shadow: 0 18px 44px rgba(15,23,42,.12);
      }
      .result-kicker {
        color: #93c5fd;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .085em;
        text-transform: uppercase;
        margin-bottom: .55rem;
      }
      .result-title {
        position: relative;
        z-index: 2;
        color: #ffffff;
        font-size: clamp(1.55rem, 3vw, 2.15rem);
        line-height: 1.22;
        letter-spacing: -.035em;
        font-weight: 790;
        margin: 0;
        max-width: 860px;
      }
      .result-subline {
        position: relative;
        z-index: 2;
        display: flex;
        flex-wrap: wrap;
        gap: .45rem;
        margin-top: .9rem;
      }
      .result-chip {
        padding: .34rem .62rem;
        border-radius: 999px;
        font-size: .74rem;
        color: rgba(226,232,240,.90);
        border: 1px solid rgba(255,255,255,.10);
        background: rgba(255,255,255,.055);
      }

      /* ---------- Report section heading ---------- */
      .section-head {
        display: flex;
        align-items: flex-start;
        gap: .85rem;
        margin: 2.25rem 0 .9rem;
        padding-bottom: .72rem;
        border-bottom: 1px solid rgba(15,23,42,.09);
      }
      .section-num {
        flex: 0 0 auto;
        min-width: 2.2rem;
        height: 2.2rem;
        border-radius: 11px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .02em;
        background: linear-gradient(135deg, #1d4ed8, #0284c7);
        box-shadow: 0 7px 16px rgba(37,99,235,.16);
      }
      .section-copy {padding-top: .03rem;}
      .section-title {
        color: #0f172a;
        font-size: 1.25rem;
        font-weight: 780;
        letter-spacing: -.025em;
        line-height: 1.25;
      }
      .section-subtitle {
        color: #64748b;
        font-size: .80rem;
        line-height: 1.45;
        margin-top: .15rem;
      }

      /* ---------- Summary + report content ---------- */
      .summary-card {
        position: relative;
        overflow: hidden;
      }
      .summary-card:before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background: linear-gradient(180deg, #2563eb, #0ea5e9);
      }
      .report-note {
        padding: 1rem 1.08rem;
        border-radius: 15px;
        border: 1px solid rgba(15,23,42,.075);
        background: rgba(248,250,252,.92);
        color: #334155;
        line-height: 1.7;
      }
      .report-kicker {
        color: #2563eb;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .075em;
        text-transform: uppercase;
        margin-bottom: .35rem;
      }

      /* ---------- Claim / related-patent containers ---------- */
      div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 18px !important;
        border-color: rgba(15,23,42,.09) !important;
        background: rgba(255,255,255,.78);
        box-shadow: 0 8px 24px rgba(15,23,42,.025);
      }
      div[data-testid="stVerticalBlockBorderWrapper"] h3 {
        color: #0f172a;
        font-size: 1.08rem;
        margin-top: .15rem !important;
      }
      div[data-testid="stMetric"] {
        padding: .45rem .55rem;
        border-radius: 12px;
        background: rgba(37,99,235,.045);
        border: 1px solid rgba(37,99,235,.08);
      }

      /* ---------- Tabs ---------- */
      div[data-baseweb="tab-list"] {
        padding: .28rem;
        border: 1px solid rgba(15,23,42,.075);
        border-radius: 14px;
        background: rgba(248,250,252,.86);
        gap: .25rem;
      }
      button[data-baseweb="tab"] {
        min-height: 42px;
        border-radius: 10px;
        padding-left: 1.15rem !important;
        padding-right: 1.15rem !important;
        color: #475569;
        font-weight: 700;
      }
      button[data-baseweb="tab"][aria-selected="true"] {
        color: #0f172a !important;
        background: #ffffff !important;
        box-shadow: 0 4px 14px rgba(15,23,42,.07);
      }

      /* ---------- Table / evidence / action polish ---------- */
      div[data-testid="stDataFrame"] {
        border-radius: 15px;
        overflow: hidden;
        border: 1px solid rgba(15,23,42,.075);
        box-shadow: 0 6px 18px rgba(15,23,42,.025);
      }
      details {
        background: rgba(255,255,255,.76);
        box-shadow: 0 5px 16px rgba(15,23,42,.02);
      }
      .stDownloadButton > button,
      a[data-testid="stBaseLinkButton-secondary"] {
        border-radius: 12px !important;
        border-color: rgba(37,99,235,.16) !important;
      }

      /* ---------- Module 2 intro ---------- */
      .module2-head {
        margin: .55rem 0 1.0rem;
        padding: 1.15rem 1.25rem;
        border-radius: 17px;
        background: linear-gradient(135deg, rgba(37,99,235,.07), rgba(14,165,233,.045));
        border: 1px solid rgba(37,99,235,.10);
      }
      .module2-head .eyebrow {
        color: #2563eb;
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .075em;
        text-transform: uppercase;
        margin-bottom: .25rem;
      }
      .module2-head .title {
        color: #0f172a;
        font-size: 1.2rem;
        font-weight: 760;
        letter-spacing: -.02em;
        margin-bottom: .2rem;
      }
      .module2-head .copy {
        color: #64748b;
        font-size: .86rem;
        line-height: 1.55;
      }

      @media (max-width: 760px) {
        .block-container {padding-top: .9rem;}
        .landing-shell {padding: 1.55rem 1.25rem 1.45rem; border-radius: 20px;}
        .landing-title {font-size: 2.05rem;}
        .landing-copy {font-size: .92rem;}
        .landing-features {grid-template-columns: 1fr;}
        .summary-card {min-height: 0;}
        .result-shell {padding: 1.35rem 1.15rem; border-radius: 18px;}
        .result-title {font-size: 1.55rem;}
        .section-head {gap: .65rem; margin-top: 1.8rem;}
        .section-num {min-width: 2rem; height: 2rem;}
        .section-title {font-size: 1.12rem;}
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


def _render_section_header(number: str, title: str, subtitle: str | None = None) -> None:
    subtitle_html = (
        f'<div class="section-subtitle">{escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="section-head">
          <div class="section-num">{escape(number)}</div>
          <div class="section-copy">
            <div class="section-title">{escape(title)}</div>
            {subtitle_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_result_shell(result: dict, metadata: dict) -> None:
    publication = _safe(metadata.get("publication_number") or result.get("patent_number"))
    applicant = _safe(metadata.get("applicant"))
    technology = _safe(result.get("primary_technology"))
    title = _safe(metadata.get("title"), result.get("title"))
    st.markdown(
        f"""
        <div class="result-shell">
          <div class="result-kicker">PSD Patent Analysis · Result</div>
          <div class="result-title">{escape(title)}</div>
          <div class="result-subline">
            <span class="result-chip">{escape(publication)}</span>
            <span class="result-chip">{escape(applicant)}</span>
            <span class="result-chip">{escape(technology)}</span>
          </div>
        </div>
        """,
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

    _render_result_shell(result, metadata)

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
    _render_section_header("00", "핵심 요약", "특허의 목적·해결방식·핵심 포인트를 먼저 확인합니다.")
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

    _render_section_header("01", "특허 기본정보", "공개 특허에서 확인되는 기본 서지정보입니다.")
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
    st.dataframe(basic_rows, width="stretch", hide_index=True)

    _render_section_header("02", "핵심 과제", "이 특허가 해결하려는 기술적 문제를 정리합니다.")
    st.markdown(f'<div class="report-note">{escape(_safe(report.get("core_problem")))}</div>', unsafe_allow_html=True)

    _render_section_header("03", "독립청구항 핵심구성", "독립청구항의 필수 구성요소와 결합관계를 중심으로 봅니다.")
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
                    width="stretch",
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

    _render_section_header("04", "종속청구항의 추가조건", "독립청구항에 추가되는 한정사항을 정리합니다.")
    st.write(_safe(report.get("dependent_claims")))

    _render_section_header("05", "작동원리", "구성요소가 실제로 어떻게 작동하는지 순서대로 설명합니다.")
    steps = report.get("operation_principle_steps") or []
    if steps:
        for idx, step in enumerate(steps, start=1):
            st.markdown(f"**{idx}.** {step}")
    else:
        st.write("작동 순서를 명확히 구성하지 못했습니다.")

    _render_section_header("06", "기술 효과", "명세서에서 확인되는 기술적 결과와 개선점을 정리합니다.")
    st.markdown(f'<div class="report-note">{escape(_safe(report.get("technical_effects")))}</div>', unsafe_allow_html=True)

    _render_section_header("07", "PSD 기술분류", "PSD 기술체계에서 이 특허가 위치하는 영역을 보여줍니다.")
    st.markdown(f'<div class="report-note">{escape(_safe(report.get("technology_classification")))}</div>', unsafe_allow_html=True)

    _render_section_header("08", "핵심 기술 요약", "전체 분석을 한 문단으로 압축한 최종 요약입니다.")
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

    st.markdown(
        """
        <div class="module2-head">
          <div class="eyebrow">Module 2 · Related Patent Analysis</div>
          <div class="title">관련 공개 특허</div>
          <div class="copy">현재 특허와 기술적으로 연결되는 공개 특허 후보를 PSD Ontology 기준으로 비교합니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
            width="stretch",
            hide_index=True,
        )

    _render_section_header("M2-1", "관련 특허 선정 이유 및 비교", "각 특허가 왜 관련 있는지와 공통점·차이점을 확인합니다.")
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

    _render_section_header("M2-2", "종합 비교", "관련 특허 전체를 기준으로 핵심 비교 결과를 정리합니다.")
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
    <div class="landing-shell">
      <div class="landing-kicker">PSD · Patent Intelligence</div>
      <h1 class="landing-title"><span>Power Sliding Door</span><br>Patent Analysis</h1>
      <p class="landing-copy">
        공개 특허의 청구항과 명세서를 기반으로 핵심 기술구조를 정리하고,
        관련 특허까지 한 번에 비교하는 PSD 특허 분석 서비스입니다.
      </p>
      <div class="landing-pills">
        <span class="landing-pill">Claim-centered</span>
        <span class="landing-pill">PSD Ontology</span>
        <span class="landing-pill">Related Patent Analysis</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="input-head">
      <div class="input-eyebrow">Start analysis</div>
      <div class="input-title">분석할 특허를 입력하세요</div>
      <div class="input-copy">특허번호 입력을 권장하며, 필요한 경우 텍스트형 PDF를 직접 업로드할 수 있습니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("patent_input_form", border=True):
    c1, c2 = st.columns([1.25, 1])
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
    analyze_clicked = st.form_submit_button("특허 분석 시작", type="primary", width="stretch")

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
    st.markdown(
        """
        <div class="landing-features">
          <div class="landing-feature">
            <div class="landing-feature-num">01 · ANALYZE</div>
            <div class="landing-feature-title">핵심 기술구조 분석</div>
            <div class="landing-feature-copy">독립청구항 중심으로 구성요소와 핵심 관계를 정리합니다.</div>
          </div>
          <div class="landing-feature">
            <div class="landing-feature-num">02 · EXPLAIN</div>
            <div class="landing-feature-title">이해하기 쉬운 보고서</div>
            <div class="landing-feature-copy">문제·구조·작동원리·효과를 엔지니어 관점에서 설명합니다.</div>
          </div>
          <div class="landing-feature">
            <div class="landing-feature-num">03 · COMPARE</div>
            <div class="landing-feature-title">관련 공개 특허 비교</div>
            <div class="landing-feature-copy">PSD 기술특징을 기준으로 관련 특허를 탐색하고 차이를 비교합니다.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("공개 특허 기반 분석 도구이며, 법적 판단이나 침해 분석을 목적으로 하지 않습니다.")
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
                st.markdown(
                    """
                    <div class="module2-head">
                      <div class="eyebrow">Module 2</div>
                      <div class="title">관련 특허 분석</div>
                      <div class="copy">현재 특허의 핵심 문제, 기능, 구성요소와 관계를 이용해 공개 특허 후보를 찾고 PSD Ontology 기준으로 관련도를 비교합니다.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption("후보 특허의 청구항을 추가로 읽기 때문에 Module 1보다 시간이 조금 더 걸릴 수 있습니다.")
                if st.button("관련 특허 분석 시작", type="primary", width="stretch"):
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
                if st.button("관련 특허 다시 분석", width="stretch"):
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
