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

    assert parsed["schema_version"] == "raw-patent-v0.2"
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
    assert parsed["parser_diagnostics"]["claim_detection_strategy"] == "explicit_claims_heading"


def test_claims_count_heading_and_invention_claimed_preamble():
    text = """
ABSTRACT
A door drive system.
DESCRIPTION
Long description content.
THE INVENTION CLAIMED IS:
1. An opening-closing body driving device comprising a case, a drum, and a cable configured to move a sliding door.
2. The opening-closing body driving device according to claim 1, wherein the cable is guided by a pulley.
3. The opening-closing body driving device according to claim 2, wherein the pulley is rotatably supported by a holder.
"""
    parsed = parse_patent_text(text)
    assert len(parsed["claims"]) == 3
    assert parsed["claims"][1]["depends_on"] == [1]
    assert parsed["claims"][2]["depends_on"] == [2]
    assert parsed["parser_diagnostics"]["claim_detection_strategy"] in {"explicit_claims_heading", "claim_preamble"}


def test_claims_count_parenthetical_heading():
    text = """
ABSTRACT
A door apparatus.
CLAIMS (3)
1. A sliding door apparatus comprising a motor and a drive cable configured to move a sliding door.
2. The sliding door apparatus of claim 1, wherein the drive cable is wound on a drum.
3. The sliding door apparatus of claim 1, wherein a guide pulley guides the drive cable.
"""
    parsed = parse_patent_text(text)
    assert [c["claim_number"] for c in parsed["claims"]] == [1, 2, 3]
    assert parsed["parser_diagnostics"]["claim_heading_or_preamble"].upper().startswith("CLAIMS")


def test_tail_number_sequence_fallback_when_heading_is_lost():
    description = "\n".join(["Detailed description paragraph about a vehicle sliding door and drive unit."] * 50)
    text = f"""
ABSTRACT
A vehicle sliding door drive.
{description}
1. A power sliding door system comprising a motor, a drum, and a cable configured to move a sliding door along a guide rail.
2. The power sliding door system according to claim 1, wherein the cable is wound on the drum.
3. The power sliding door system according to claim 2, wherein a pulley guides the cable.
"""
    parsed = parse_patent_text(text)
    assert len(parsed["claims"]) == 3
    assert parsed["parser_diagnostics"]["claim_detection_strategy"] == "tail_number_sequence"


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
    assert parsed["parser_diagnostics"]["claim_detection_strategy"] == "not_found"
