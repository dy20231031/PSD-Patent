from io import BytesIO

from pypdf import PdfWriter

from engine.patent.parser import parse_patent_pdf, parse_patent_text


SAMPLE_PATENT_TEXT = """
US 10,774,572 B2
TITLE OF INVENTION
Power Sliding Door Cable Tension Device
Applicant: Example Mobility Corp.

ABSTRACT
A power sliding door device maintains cable tension during opening and closing.

BACKGROUND OF THE INVENTION
Conventional sliding door cable systems may develop slack after repeated operation.

SUMMARY OF THE INVENTION
A spring biases a tension pulley so that cable tension can be maintained.

BRIEF DESCRIPTION OF THE DRAWINGS
FIG. 1 shows a sliding door drive unit.

DETAILED DESCRIPTION
The drive unit includes a drum, a cable, a tension pulley and a spring.

CLAIMS
1. A power sliding door system comprising a drive cable, a tension pulley, and a spring configured to bias the tension pulley toward the drive cable.
2. The power sliding door system according to claim 1, wherein the tension pulley is movably supported by a holder.
3. The power sliding door system of claim 1, wherein the spring is a coil spring.
4. A method for operating a power sliding door, comprising driving a cable to move a sliding door.
"""


def test_parse_patent_text_sections_and_claims():
    parsed = parse_patent_text(SAMPLE_PATENT_TEXT, filename="sample.pdf")

    assert parsed["schema_version"] == "raw-patent-v0.1"
    assert parsed["metadata"]["publication_number"] == "US10774572B2"
    assert parsed["metadata"]["title"] == "Power Sliding Door Cable Tension Device"
    assert parsed["metadata"]["applicant"] == "Example Mobility Corp."
    assert "maintains cable tension" in parsed["abstract"]
    assert "develop slack" in parsed["background"]
    assert "spring biases" in parsed["summary"]
    assert "FIG. 1" in parsed["figure_description"]
    assert "drive unit includes" in parsed["description"]

    claims = parsed["claims"]
    assert len(claims) == 4
    assert claims[0]["claim_type"] == "independent"
    assert claims[1]["claim_type"] == "dependent"
    assert claims[1]["depends_on"] == [1]
    assert claims[2]["claim_type"] == "dependent"
    assert claims[2]["depends_on"] == [1]
    assert claims[3]["claim_type"] == "independent"


def test_korean_claim_dependency_detection():
    text = """
발명의 명칭: 파워 슬라이딩 도어 장치
출원인: 예시자동차 주식회사
초록
슬라이딩 도어 장치에 관한 것이다.
청구범위
청구항 1
모터와 케이블을 포함하는 슬라이딩 도어 장치.
청구항 2
청구항 1에 있어서, 상기 케이블을 안내하는 풀리를 더 포함하는 슬라이딩 도어 장치.
청구항 3
제1항에 있어서, 상기 풀리는 회전 가능하게 지지되는 슬라이딩 도어 장치.
"""
    parsed = parse_patent_text(text)
    assert len(parsed["claims"]) == 3
    assert parsed["claims"][0]["claim_type"] == "independent"
    assert parsed["claims"][1]["depends_on"] == [1]
    assert parsed["claims"][2]["depends_on"] == [1]


def test_image_only_or_blank_pdf_returns_warning_instead_of_crashing():
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(buffer)

    parsed = parse_patent_pdf(buffer.getvalue(), filename="blank.pdf")
    assert parsed["source"]["page_count"] == 1
    assert parsed["source"]["ocr_used"] is False
    assert parsed["source"]["warnings"]
    assert parsed["claims"] == []
