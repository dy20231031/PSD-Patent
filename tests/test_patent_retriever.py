from engine.patent.retriever import normalize_patent_number, parse_google_patents_html, retrieve_patent_by_number


GOOGLE_PATENT_HTML = """
<!doctype html>
<html>
<head>
<title>US10774572B2 - Opening-closing body driving device - Google Patents</title>
<meta name="DC.title" content="US10774572B2 - Opening-closing body driving device">
<meta name="citation_patent_publication_number" content="US10774572B2">
<meta name="citation_patent_application_number" content="US16/082,993">
<meta scheme="assignee" content="Mitsuba Corp">
<meta scheme="inventor" content="Yoshitaka Urano">
</head>
<body>
<dl>
<dt>Priority date</dt><dd>2016-03-10</dd>
<dt>Filing date</dt><dd>2017-01-26</dd>
<dt>Publication date</dt><dd>2020-09-15</dd>
<dt>Legal status</dt><dd>Active</dd>
</dl>
<div>Family ID=12345678</div>
<section itemprop="abstract"><h2>Abstract</h2><div>A cable pulley structure improves durability.</div></section>
<section itemprop="description"><h2>Description</h2>
BACKGROUND ART
A conventional power sliding door cable may be damaged.
SUMMARY
A circular arc connecting unit suppresses cable damage.
BRIEF DESCRIPTION OF THE DRAWINGS
FIG. 1 is a perspective view of the sliding door drive assembly.
FIG. 2 is an exploded view of the pulley and spring member.
DETAILED DESCRIPTION
A case accommodates a drum, a pulley, and a spring member.
</section>
<section itemprop="images">
<img id="fig1" src="https://patentimages.storage.googleapis.com/a/US10774572B2-D00000.png" alt="FIG. 1">
<img id="fig2" src="https://patentimages.storage.googleapis.com/b/US10774572B2-D00001.png" alt="FIG. 2">
</section>
<section itemprop="claims" itemscope>
<h2>Claims (3)</h2>
<div itemprop="content" class="claims">
<div class="claim"><div num="1" class="claim"><div class="claim-text">1. An opening-closing body driving device comprising a case, a drum, a cable, and a pulley configured to guide the cable.</div></div></div>
<div class="claim-dependent"><div num="2" class="claim"><div class="claim-text">2. The opening-closing body driving device according to claim 1, wherein a spring member presses a pulley holder.</div></div></div>
<div class="claim-dependent"><div num="3" class="claim"><div class="claim-text">3. The opening-closing body driving device according to claim 2, wherein the pulley is axially movable.</div></div></div>
</div>
</section>
</body>
</html>
"""


def test_normalize_patent_number():
    assert normalize_patent_number("US 10,774,572 B2") == "US10774572B2"
    assert normalize_patent_number("jp-7604988-b2") == "JP7604988B2"


def test_parse_google_patents_html_structured_claims():
    parsed = parse_google_patents_html(
        GOOGLE_PATENT_HTML,
        patent_number="US10774572B2",
        source_url="https://patents.google.com/patent/US10774572B2/en",
    )
    assert parsed["source"]["input_type"] == "patent_number"
    assert parsed["source"]["provider"] == "Google Patents"
    assert parsed["metadata"]["publication_number"] == "US10774572B2"
    assert parsed["metadata"]["title"] == "Opening-closing body driving device"
    assert parsed["metadata"]["applicant"] == "Mitsuba Corp"
    assert parsed["metadata"]["inventors"] == ["Yoshitaka Urano"]
    assert parsed["metadata"]["family_id"] == "12345678"
    assert len(parsed["figures"]) == 2
    assert parsed["figures"][0]["figure_number"] == 1
    assert "perspective view" in parsed["figures"][0]["caption"]
    assert len(parsed["claims"]) == 3
    assert parsed["claims"][1]["depends_on"] == [1]
    assert parsed["claims"][2]["depends_on"] == [2]
    assert parsed["parser_diagnostics"]["claim_detection_strategy"] == "google_patents_structured_html"
    assert "conventional power sliding door" in parsed["background"]


class FakeResponse:
    status_code = 200
    text = GOOGLE_PATENT_HTML
    url = "https://patents.google.com/patent/US10774572B2/en"


class FakeSession:
    def __init__(self):
        self.called_url = None

    def get(self, url, timeout, headers):
        self.called_url = url
        return FakeResponse()


def test_retrieve_patent_by_number_builds_google_patents_url():
    session = FakeSession()
    parsed = retrieve_patent_by_number("US10774572B2", session=session)
    assert session.called_url.endswith("/US10774572B2/en")
    assert parsed["parser_diagnostics"]["claim_count"] == 3
