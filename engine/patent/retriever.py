from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

import requests
from bs4 import BeautifulSoup

from engine.patent.parser import _clean_text, _extract_claim_dependencies, parse_patent_text
from engine.schemas import RawPatent


class PatentRetrievalError(ValueError):
    """Raised when a public patent page cannot be retrieved or parsed."""


PATENT_NUMBER_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{5,24}$")
GOOGLE_PATENTS_BASE = "https://patents.google.com/patent"


def normalize_patent_number(value: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]", "", (value or "")).upper()
    if not compact:
        raise PatentRetrievalError("특허번호가 비어 있습니다.")
    if not PATENT_NUMBER_RE.fullmatch(compact):
        raise PatentRetrievalError(
            "특허번호 형식을 확인해 주세요. 예: US10774572B2, US20190093412A1, JP7604988B2, EP1234567A1"
        )
    return compact


def _meta_content(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return _clean_text(str(tag["content"]))
    return None


def _scheme_meta_values(soup: BeautifulSoup, scheme: str) -> list[str]:
    out: list[str] = []
    for tag in soup.find_all("meta", attrs={"scheme": scheme}):
        value = tag.get("content")
        if value:
            clean = _clean_text(str(value))
            if clean and clean not in out:
                out.append(clean)
    return out


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            value = _clean_text(node.get_text(" ", strip=True))
            if value:
                return value
    return None


def _remove_source_language_spans(node) -> None:
    # On translated /en pages Google Patents may embed original-language text in
    # span.google-src-text. Removing those spans prevents duplicate bilingual text.
    for source in node.select("span.google-src-text"):
        source.decompose()


def _section_text(soup: BeautifulSoup, itemprop: str) -> str:
    section = soup.select_one(f'section[itemprop="{itemprop}"]')
    if not section:
        return ""
    clone = BeautifulSoup(str(section), "html.parser")
    _remove_source_language_spans(clone)
    heading = clone.find(["h1", "h2", "h3"])
    if heading:
        heading.decompose()
    return _clean_text(clone.get_text("\n", strip=True))


def _extract_google_claims(soup: BeautifulSoup) -> list[dict[str, Any]]:
    section = soup.select_one('section[itemprop="claims"]')
    if not section:
        return []

    clone = BeautifulSoup(str(section), "html.parser")
    _remove_source_language_spans(clone)

    claims: list[dict[str, Any]] = []
    seen: set[int] = set()

    # Current Google Patents commonly uses .claim[num] elements. This also works
    # for nested US div.claim and EP/translated list structures.
    nodes = clone.select('.claim[num], .claim-dependent[num], [num].claim, [num].claim-dependent')
    for node in nodes:
        raw_num = node.get("num")
        if raw_num is None or not str(raw_num).isdigit():
            continue
        number = int(raw_num)
        if number in seen or not (1 <= number <= 300):
            continue
        text_node = node.select_one(".claim-text") or node
        text = _clean_text(text_node.get_text(" ", strip=True))
        text = re.sub(rf"^\s*{number}\s*[.)：:]?\s*", "", text)
        if len(text) < 20:
            continue
        seen.add(number)
        depends_on = _extract_claim_dependencies(text, number)
        claims.append(
            {
                "claim_id": f"C{number}",
                "claim_number": number,
                "claim_type": "dependent" if depends_on else "independent",
                "depends_on": depends_on,
                "text": text,
            }
        )

    if claims:
        return sorted(claims, key=lambda x: x["claim_number"])

    # Fallback: section plain text is still far better than failing silently.
    plain = _clean_text(clone.get_text("\n", strip=True))
    synthetic = f"CLAIMS\n{plain}"
    parsed = parse_patent_text(synthetic)
    return parsed.get("claims", [])


def _extract_title(soup: BeautifulSoup, number: str) -> str | None:
    title = _meta_content(soup, "DC.title", "citation_title")
    if not title:
        title = _first_text(soup, ["span[itemprop=title]", "h1"])
    if not title:
        return None
    # DC.title is often 'US123... - Invention title'.
    title = re.sub(rf"^\s*{re.escape(number)}\s*[-–—:]\s*", "", title, flags=re.I)
    title = re.sub(r"\s*-\s*Google Patents\s*$", "", title, flags=re.I)
    return title.strip() or None


def _extract_assignee(soup: BeautifulSoup) -> str | None:
    values = _scheme_meta_values(soup, "assignee")
    if values:
        return values[0]
    return _first_text(
        soup,
        [
            "dd[itemprop=assigneeOriginal]",
            "span[itemprop=assigneeOriginal]",
            "dd[itemprop=assignee]",
            "span[itemprop=assignee]",
        ],
    )


def _extract_inventors(soup: BeautifulSoup) -> list[str]:
    values = _scheme_meta_values(soup, "inventor")
    if values:
        return values
    out: list[str] = []
    for node in soup.select("dd[itemprop=inventor], span[itemprop=inventor]"):
        value = _clean_text(node.get_text(" ", strip=True))
        if value and value not in out:
            out.append(value)
    return out


def _visible_info_value(soup: BeautifulSoup, label: str) -> str | None:
    # Google Patents info uses DT/DD pairs in several page generations.
    for dt in soup.find_all("dt"):
        if _clean_text(dt.get_text(" ", strip=True)).lower() == label.lower():
            dd = dt.find_next_sibling("dd")
            if dd:
                return _clean_text(dd.get_text(" ", strip=True)) or None
    return None


def parse_google_patents_html(html: str, *, patent_number: str, source_url: str | None = None) -> dict[str, Any]:
    number = normalize_patent_number(patent_number)
    if not html or len(html) < 500:
        raise PatentRetrievalError("공개 특허 페이지 응답이 비어 있거나 너무 짧습니다.")

    soup = BeautifulSoup(html, "html.parser")
    page_title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    if "Google Patents" not in page_title and not soup.select_one('section[itemprop="claims"]'):
        raise PatentRetrievalError("Google Patents 특허 상세 페이지 형식을 확인하지 못했습니다.")

    abstract = _section_text(soup, "abstract")
    description = _section_text(soup, "description")
    claims = _extract_google_claims(soup)

    title = _extract_title(soup, number)
    applicant = _extract_assignee(soup)
    inventors = _extract_inventors(soup)

    publication_number = _meta_content(soup, "citation_patent_publication_number") or number
    publication_number = re.sub(r"[^A-Za-z0-9]", "", publication_number).upper() or number
    application_number = (
        _meta_content(soup, "citation_patent_application_number")
        or next(iter(_scheme_meta_values(soup, "applicationNumber")), None)
        or _visible_info_value(soup, "Application number")
    )
    priority_date = (
        next(iter(_scheme_meta_values(soup, "priorityDate")), None)
        or _meta_content(soup, "DC.date")
        or _visible_info_value(soup, "Priority date")
    )
    filing_date = (
        next(iter(_scheme_meta_values(soup, "filingDate")), None)
        or _meta_content(soup, "citation_date")
        or _visible_info_value(soup, "Filing date")
    )
    publication_date = (
        next(iter(_scheme_meta_values(soup, "publicationDate")), None)
        or _visible_info_value(soup, "Publication date")
    )
    legal_status = _visible_info_value(soup, "Legal status")

    # Feed the description through the same section splitter used for PDFs, then
    # replace claims with the structured HTML claims (more reliable than text regex).
    synthetic = ""
    if abstract:
        synthetic += f"ABSTRACT\n{abstract}\n\n"
    synthetic += description
    if claims:
        synthetic += "\n\nCLAIMS\n" + "\n\n".join(f"{c['claim_number']}. {c['text']}" for c in claims)

    raw = parse_patent_text(
        synthetic,
        patent_number_hint=publication_number,
        source_info={
            "input_type": "patent_number",
            "page_count": None,
            "text_char_count": len(_clean_text(synthetic)),
            "average_chars_per_page": None,
            "extraction_method": "google_patents_html",
            "ocr_used": False,
            "warnings": [],
            "source_url": source_url,
            "provider": "Google Patents",
        },
        metadata_override={
            "publication_number": publication_number,
            "publication_number_raw": publication_number,
            "title": title,
            "applicant": applicant,
            "filename": None,
            "application_number": application_number,
            "priority_date": priority_date,
            "filing_date": filing_date,
            "publication_date": publication_date,
            "inventors": inventors,
            "legal_status": legal_status,
        },
    )

    if claims:
        raw["claims"] = claims
        raw["parser_diagnostics"].update(
            {
                "claim_count": len(claims),
                "independent_claim_count": sum(c["claim_type"] == "independent" for c in claims),
                "dependent_claim_count": sum(c["claim_type"] == "dependent" for c in claims),
                "claim_detection_strategy": "google_patents_structured_html",
                "claim_heading_or_preamble": "section[itemprop=claims]",
                "claim_candidate_marker_count": len(claims),
                "claim_text_preview": "\n\n".join(f"{c['claim_number']}. {c['text']}" for c in claims)[:1200],
            }
        )
        # Remove a claims warning that may have been created while sectionizing a
        # translated/atypical description before the HTML claims were injected.
        raw["source"]["warnings"] = [w for w in raw["source"].get("warnings", []) if "청구항을 자동 분리" not in w]
        raw["parser_diagnostics"]["warnings"] = [
            w for w in raw["parser_diagnostics"].get("warnings", []) if "청구항을 자동 분리" not in w
        ]

    return RawPatent.model_validate(raw).model_dump()


def retrieve_patent_by_number(
    patent_number: str,
    *,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Retrieve a public patent from Google Patents and return Raw Patent JSON.

    The user supplies a publication/grant number. We request the English page
    (`/en`) so non-English families can use Google Patents' available translation.
    PDF upload remains available as a fallback when the public page is unavailable.
    """
    number = normalize_patent_number(patent_number)
    url = f"{GOOGLE_PATENTS_BASE}/{number}/en"
    client = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PSD-Patent-Intelligence/0.4; +https://streamlit.app)",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = client.get(url, timeout=timeout, headers=headers)
    except requests.RequestException as exc:
        raise PatentRetrievalError(f"공개 특허 원문 조회에 실패했습니다: {exc}") from exc

    if response.status_code == 404:
        raise PatentRetrievalError(f"{number} 특허를 Google Patents에서 찾지 못했습니다.")
    if response.status_code == 429:
        raise PatentRetrievalError("Google Patents 요청 한도에 도달했습니다. 잠시 후 다시 시도하거나 PDF를 업로드해 주세요.")
    if response.status_code >= 500:
        raise PatentRetrievalError(f"Google Patents 서버가 일시적으로 응답하지 않습니다 (HTTP {response.status_code}).")
    if response.status_code != 200:
        raise PatentRetrievalError(f"공개 특허 조회가 실패했습니다 (HTTP {response.status_code}). PDF 업로드를 이용해 주세요.")

    return parse_google_patents_html(response.text, patent_number=number, source_url=response.url or url)
