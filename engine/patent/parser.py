from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from pypdf import PdfReader

from engine.schemas import RawPatent


class PatentParseError(ValueError):
    """Raised when an uploaded PDF cannot be parsed as a readable PDF."""


@dataclass(frozen=True)
class SectionHit:
    section: str
    start: int
    end: int
    heading: str


SECTION_PATTERNS: dict[str, list[str]] = {
    "abstract": [
        r"ABSTRACT",
        r"要約",
        r"초록",
        r"요약",
    ],
    "background": [
        r"BACKGROUND(?:\s+OF\s+THE\s+INVENTION)?",
        r"BACKGROUND\s+ART",
        r"TECHNICAL\s+BACKGROUND",
        r"背景技術",
        r"従来技術",
        r"배경기술",
        r"배경\s*기술",
    ],
    "summary": [
        r"SUMMARY(?:\s+OF\s+THE\s+INVENTION)?",
        r"発明の概要",
        r"発明の内容",
        r"발명의\s*내용",
        r"발명의\s*개요",
        r"해결하려는\s*과제",
    ],
    "figure_description": [
        r"BRIEF\s+DESCRIPTION\s+OF\s+THE\s+DRAWINGS?",
        r"DESCRIPTION\s+OF\s+THE\s+DRAWINGS?",
        r"図面の簡単な説明",
        r"도면의\s*간단한\s*설명",
    ],
    "description": [
        r"DETAILED\s+DESCRIPTION(?:\s+OF\s+THE\s+INVENTION)?",
        r"DESCRIPTION\s+OF\s+(?:THE\s+)?EMBODIMENTS?",
        r"BEST\s+MODE\s+FOR\s+CARRYING\s+OUT\s+THE\s+INVENTION",
        r"発明を実施するための形態",
        r"実施形態",
        r"발명을\s*실시하기\s*위한\s*(?:구체적인\s*)?내용",
        r"발명의\s*실시를\s*위한\s*형태",
    ],
    "claims": [
        r"CLAIMS",
        r"WHAT\s+IS\s+CLAIMED\s+IS",
        r"特許請求の範囲",
        r"청구범위",
    ],
}

TITLE_LABELS = [
    "TITLE OF INVENTION",
    "TITLE OF THE INVENTION",
    "INVENTION TITLE",
    "発明の名称",
    "발명의 명칭",
]

APPLICANT_LABELS = [
    "Applicant",
    "Applicants",
    "Applicant(s)",
    "Assignee",
    "Assignees",
    "出願人",
    "출원인",
]


# Publication numbers are deliberately broad. We preserve the raw match and also
# expose a compact canonical form for downstream lookup/normalization.
PUBLICATION_RE = re.compile(
    r"\b(?P<country>US|JP|KR|EP|WO)\s*"
    r"(?P<number>[0-9][0-9,./\-\s]{5,24}[0-9])\s*"
    r"(?P<kind>[A-Z]\d?)?\b",
    re.IGNORECASE,
)

CLAIM_MARKER_RE = re.compile(
    r"(?im)^\s*(?:"
    r"(?:claim|청구항|請求項)\s*(?P<word_num>\d{1,3})\s*(?:[.:：\]】)]\s*|(?=$))"
    r"|제\s*(?P<kr_num>\d{1,3})\s*항\s*(?:[.:：)]\s*|(?=$))"
    r"|(?P<plain_num>\d{1,3})\s*[.)]\s+"
    r")"
)

DEPENDENCY_CUES = [
    re.compile(r"\b(?:according\s+to|of|as\s+(?:recited|set\s+forth)\s+in)\s+(?:any\s+one\s+of\s+)?claims?\b", re.I),
    re.compile(r"\bclaims?\s+\d+\s*(?:to|-|through)\s*\d+\b", re.I),
    re.compile(r"(?:청구항\s*\d+|제\s*\d+\s*항).{0,40}?(?:에\s*있어서|에\s*따른|에\s*기재된|중\s*어느\s*한\s*항)", re.I | re.S),
    re.compile(r"請求項\s*\d+.{0,30}?(?:に記載|に係る|のいずれか)", re.I | re.S),
]



def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")



def _clean_text(text: str) -> str:
    text = _nfkc(text)
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()



def _compact_publication_number(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", raw).upper()



def _extract_publication_number(text: str, hint: str | None) -> tuple[str | None, str | None]:
    if hint:
        hint_clean = hint.strip()
        if hint_clean:
            return _compact_publication_number(hint_clean), hint_clean

    for match in PUBLICATION_RE.finditer(text[:25000]):
        raw = match.group(0).strip()
        compact = _compact_publication_number(raw)
        # Reject obvious short/non-patent false positives.
        if len(re.sub(r"\D", "", compact)) >= 6:
            return compact, raw
    return None, None



def _line_after_label(text: str, labels: list[str]) -> str | None:
    lines = [line.strip() for line in text[:25000].splitlines()]
    for idx, line in enumerate(lines):
        for label in labels:
            label_re = re.compile(rf"^{re.escape(label)}\s*[:：-]?\s*(.*)$", re.I)
            match = label_re.match(line)
            if not match:
                continue
            same_line = match.group(1).strip()
            if same_line:
                return same_line
            for candidate in lines[idx + 1 : idx + 5]:
                if candidate:
                    return candidate
    return None



def _extract_applicant(text: str, pdf_metadata: dict[str, str]) -> str | None:
    value = _line_after_label(text, APPLICANT_LABELS)
    if value:
        return value
    author = pdf_metadata.get("author")
    return author or None



def _extract_title(text: str, pdf_metadata: dict[str, str]) -> str | None:
    value = _line_after_label(text, TITLE_LABELS)
    if value:
        return value

    meta_title = (pdf_metadata.get("title") or "").strip()
    if meta_title and meta_title.lower() not in {"untitled", "microsoft word"}:
        return meta_title

    # Conservative fallback: use a short all-caps/front-page line only when it
    # looks like a technical title rather than a bibliographic label.
    excluded = re.compile(
        r"^(?:UNITED STATES PATENT|PATENT|ABSTRACT|CLAIMS?|BACKGROUND|SUMMARY|"
        r"PUBLICATION|APPLICATION|INVENTOR|APPLICANT|ASSIGNEE)",
        re.I,
    )
    for line in text[:8000].splitlines():
        candidate = line.strip(" -:\t")
        if not (8 <= len(candidate) <= 180):
            continue
        if excluded.search(candidate):
            continue
        if len(candidate.split()) >= 2 and re.search(r"[A-Za-z가-힣ぁ-んァ-ン一-龥]", candidate):
            # Avoid choosing lines dominated by bibliographic numbers.
            if sum(ch.isdigit() for ch in candidate) / max(len(candidate), 1) < 0.25:
                return candidate
    return None



def _compile_heading_pattern(heading_regex: str) -> re.Pattern[str]:
    # Patent PDFs often prefix headings with paragraph numbers such as [0001].
    return re.compile(
        rf"(?im)^\s*(?:\[[0-9]{{1,5}}\]\s*)?(?P<heading>{heading_regex})\s*[:：]?\s*$"
    )



def _find_section_hits(text: str) -> list[SectionHit]:
    candidates: list[SectionHit] = []
    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            for match in _compile_heading_pattern(pattern).finditer(text):
                candidates.append(
                    SectionHit(
                        section=section,
                        start=match.start(),
                        end=match.end(),
                        heading=match.group("heading").strip(),
                    )
                )

    # Keep the first occurrence of each section, then sort by document order.
    first_by_section: dict[str, SectionHit] = {}
    for hit in sorted(candidates, key=lambda h: h.start):
        first_by_section.setdefault(hit.section, hit)
    return sorted(first_by_section.values(), key=lambda h: h.start)



def _slice_sections(text: str, hits: list[SectionHit]) -> tuple[dict[str, str], dict[str, str]]:
    sections = {key: "" for key in SECTION_PATTERNS}
    headings: dict[str, str] = {}

    for idx, hit in enumerate(hits):
        next_start = hits[idx + 1].start if idx + 1 < len(hits) else len(text)
        sections[hit.section] = text[hit.end : next_start].strip()
        headings[hit.section] = hit.heading

    return sections, headings



def _claim_number_from_marker(match: re.Match[str]) -> int:
    for key in ("word_num", "kr_num", "plain_num"):
        value = match.groupdict().get(key)
        if value:
            return int(value)
    raise ValueError("Claim marker without claim number")



def _expand_numeric_ranges(fragment: str) -> list[int]:
    numbers: set[int] = set()
    normalized = _nfkc(fragment)
    for left, right in re.findall(r"(\d{1,3})\s*(?:to|through|-|~|내지)\s*(?:제\s*)?(\d{1,3})", normalized, flags=re.I):
        a, b = int(left), int(right)
        if 0 < a <= b <= 999 and b - a <= 50:
            numbers.update(range(a, b + 1))
    for num in re.findall(r"\d{1,3}", normalized):
        value = int(num)
        if value > 0:
            numbers.add(value)
    return sorted(numbers)



def _extract_claim_dependencies(text: str, claim_number: int) -> list[int]:
    if not any(pattern.search(text) for pattern in DEPENDENCY_CUES):
        return []

    refs: set[int] = set()

    # English: claim 1 / claims 1, 2 and 3 / claims 1 to 3
    for match in re.finditer(r"\bclaims?\s+([^.;:\n]{0,80})", text, re.I):
        fragment = match.group(1)
        # Stop if we run too far into normal prose.
        fragment = re.split(r"\b(?:wherein|comprising|characterized|which|that)\b", fragment, maxsplit=1, flags=re.I)[0]
        refs.update(_expand_numeric_ranges(fragment))

    # Korean/Japanese references.
    refs.update(int(x) for x in re.findall(r"청구항\s*(\d{1,3})", text))
    refs.update(int(x) for x in re.findall(r"제\s*(\d{1,3})\s*항", text))
    refs.update(int(x) for x in re.findall(r"請求項\s*(\d{1,3})", text))

    refs.discard(claim_number)
    return sorted(refs)



def _parse_claims(claims_text: str) -> list[dict[str, Any]]:
    claims_text = _clean_text(claims_text)
    if not claims_text:
        return []

    markers = list(CLAIM_MARKER_RE.finditer(claims_text))
    if not markers:
        return []

    claims: list[dict[str, Any]] = []
    seen: set[int] = set()
    for idx, marker in enumerate(markers):
        number = _claim_number_from_marker(marker)
        if number in seen:
            # A duplicate marker is usually a page header/cross-reference artifact.
            continue
        seen.add(number)
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(claims_text)
        body = claims_text[marker.end() : end].strip()
        if not body:
            continue
        depends_on = _extract_claim_dependencies(body, number)
        claim_type = "dependent" if depends_on else "independent"
        claims.append(
            {
                "claim_id": f"C{number}",
                "claim_number": number,
                "claim_type": claim_type,
                "depends_on": depends_on,
                "text": body,
            }
        )

    return sorted(claims, key=lambda item: item["claim_number"])



def _fallback_claims_text(text: str) -> str:
    # Common US wording may be present even when the heading does not occupy its own line.
    match = re.search(r"(?is)\bWHAT\s+IS\s+CLAIMED\s+IS\s*:?\s*(.*)$", text)
    if match:
        return match.group(1).strip()
    return ""



def _build_metadata(
    text: str,
    filename: str | None,
    patent_number_hint: str | None,
    pdf_metadata: dict[str, str],
) -> dict[str, Any]:
    publication_number, publication_number_raw = _extract_publication_number(text, patent_number_hint)
    return {
        "publication_number": publication_number,
        "publication_number_raw": publication_number_raw,
        "title": _extract_title(text, pdf_metadata),
        "applicant": _extract_applicant(text, pdf_metadata),
        "filename": filename,
        "pdf_metadata": pdf_metadata,
    }



def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, dict[str, Any]]:
    """Extract embedded text from a PDF without OCR.

    Returns `(text, source_info)`. Scanned/image-only PDFs are not OCRed in this
    parser version; instead a diagnostic warning is returned.
    """
    if not pdf_bytes:
        raise PatentParseError("업로드된 PDF가 비어 있습니다.")

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:  # pypdf exposes several parser-specific exception types
        raise PatentParseError(f"PDF 파일을 열 수 없습니다: {exc}") from exc

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt("")
        except Exception as exc:
            raise PatentParseError("암호화된 PDF이며 빈 비밀번호로 열 수 없습니다.") from exc
        if not decrypt_result:
            raise PatentParseError("암호화된 PDF이며 비밀번호가 필요합니다.")

    page_texts: list[str] = []
    page_char_counts: list[int] = []
    extraction_errors: list[str] = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            page_text = ""
            extraction_errors.append(f"page {page_number}: {type(exc).__name__}")
        page_text = _clean_text(page_text)
        page_texts.append(page_text)
        page_char_counts.append(len(page_text))

    text = _clean_text("\n\n".join(page_texts))
    page_count = len(reader.pages)
    char_count = len(text)
    avg_chars = char_count / max(page_count, 1)

    warnings: list[str] = []
    if char_count < 500:
        warnings.append(
            "PDF에서 추출된 텍스트가 매우 적습니다. 스캔/이미지형 PDF일 수 있으며 현재 버전은 OCR을 수행하지 않습니다."
        )
    elif avg_chars < 250:
        warnings.append(
            "페이지당 추출 텍스트가 적습니다. 일부 페이지가 이미지형이거나 폰트 인코딩 때문에 누락되었을 수 있습니다."
        )
    if extraction_errors:
        warnings.append(f"{len(extraction_errors)}개 페이지에서 텍스트 추출 오류가 발생했습니다.")

    raw_meta = reader.metadata or {}
    pdf_metadata: dict[str, str] = {}
    metadata_map = {
        "/Title": "title",
        "/Author": "author",
        "/Subject": "subject",
        "/Creator": "creator",
        "/Producer": "producer",
        "/CreationDate": "creation_date",
        "/ModDate": "modified_date",
    }
    for source_key, output_key in metadata_map.items():
        value = raw_meta.get(source_key)
        if value is not None:
            pdf_metadata[output_key] = str(value)

    source_info = {
        "page_count": page_count,
        "text_char_count": char_count,
        "average_chars_per_page": round(avg_chars, 1),
        "page_char_counts": page_char_counts,
        "extraction_method": "pypdf_embedded_text",
        "ocr_used": False,
        "warnings": warnings,
        "page_extraction_errors": extraction_errors,
        "pdf_metadata": pdf_metadata,
    }
    return text, source_info



def parse_patent_text(
    raw_text: str,
    *,
    filename: str | None = None,
    patent_number_hint: str | None = None,
    source_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse extracted patent text into a Raw Patent JSON-compatible dictionary."""
    text = _clean_text(raw_text)
    source_info = dict(source_info or {})
    pdf_metadata = dict(source_info.get("pdf_metadata") or {})

    hits = _find_section_hits(text)
    sections, headings = _slice_sections(text, hits)

    claims_text = sections.get("claims", "") or _fallback_claims_text(text)
    claims = _parse_claims(claims_text)

    warnings = list(source_info.get("warnings") or [])
    if not claims:
        warnings.append(
            "청구항을 자동 분리하지 못했습니다. PDF 텍스트 형식에 따라 Claims heading/번호 패턴 보완이 필요할 수 있습니다."
        )

    if not sections.get("abstract"):
        warnings.append("Abstract 섹션을 자동 탐지하지 못했습니다.")

    independent_count = sum(1 for claim in claims if claim["claim_type"] == "independent")
    dependent_count = sum(1 for claim in claims if claim["claim_type"] == "dependent")

    metadata = _build_metadata(text, filename, patent_number_hint, pdf_metadata)

    parser_diagnostics = {
        "section_headings_found": headings,
        "sections_found": sorted(headings.keys()),
        "claim_count": len(claims),
        "independent_claim_count": independent_count,
        "dependent_claim_count": dependent_count,
        "warnings": warnings,
    }

    payload = {
        "schema_version": "raw-patent-v0.1",
        "source": {
            "input_type": "pdf" if filename else "text",
            "filename": filename,
            "page_count": source_info.get("page_count"),
            "text_char_count": source_info.get("text_char_count", len(text)),
            "average_chars_per_page": source_info.get("average_chars_per_page"),
            "extraction_method": source_info.get("extraction_method", "provided_text"),
            "ocr_used": bool(source_info.get("ocr_used", False)),
            "warnings": warnings,
        },
        "metadata": metadata,
        "abstract": sections.get("abstract", ""),
        "background": sections.get("background", ""),
        "summary": sections.get("summary", ""),
        "figure_description": sections.get("figure_description", ""),
        "description": sections.get("description", ""),
        "claims": claims,
        "parser_diagnostics": parser_diagnostics,
        "raw_text": text,
    }
    return RawPatent.model_validate(payload).model_dump()



def parse_patent_pdf(
    pdf_bytes: bytes,
    *,
    filename: str | None = None,
    patent_number_hint: str | None = None,
) -> dict[str, Any]:
    """PDF bytes -> text extraction -> patent section/claim parsing -> Raw Patent JSON."""
    text, source_info = extract_pdf_text(pdf_bytes)
    return parse_patent_text(
        text,
        filename=filename,
        patent_number_hint=patent_number_hint,
        source_info=source_info,
    )



def parse_patent_document(raw_text: str) -> dict[str, Any]:
    """Backward-compatible wrapper used by early project code/tests."""
    return parse_patent_text(raw_text)
