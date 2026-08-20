from pathlib import Path


def test_public_ui_is_report_first_and_developer_tools_are_opt_in():
    source = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")
    assert 'st.tabs(["특허 분석", "관련 특허"])' in source
    assert 'SHOW_DEVELOPER_TOOLS' in source
    assert 'with st.expander("분석 근거 보기")' in source
    assert '_section_header("08", "핵심 기술 요약")' in source
    assert '도면으로 보는 핵심 구조' in source
    assert 'GEMINI_FALLBACK_MODEL' in source
    assert '관련 특허 분석 시작' in source
