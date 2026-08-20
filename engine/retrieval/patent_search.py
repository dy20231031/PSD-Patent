from __future__ import annotations

import json
import re
from html import unescape
from typing import Any

import requests
from bs4 import BeautifulSoup

GOOGLE_PATENTS_XHR = "https://patents.google.com/xhr/query"
GOOGLE_PATENTS_BASE = "https://patents.google.com/patent"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://patents.google.com/",
}


class RelatedPatentSearchError(RuntimeError):
    """Raised when the public related-patent search source is unavailable."""


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = unescape(str(value))
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _terms_from_name(name: str) -> list[str]:
    text = re.sub(r"[_/]+", " ", name or " ")
    text = re.sub(r"[^A-Za-z0-9가-힣\- ]+", " ", text)
    stop = {
        "improve", "reduce", "stabilize", "prevent", "increase", "facilitate",
        "the", "and", "or", "of", "to", "a", "an", "management", "performance",
    }
    out: list[str] = []
    for token in text.split():
        low = token.lower()
        if len(low) < 3 or low in stop:
            continue
        if low not in {x.lower() for x in out}:
            out.append(token)
    return out


def build_related_search_queries(structured_patent: dict, raw_patent: dict | None = None) -> list[str]:
    """Build a small set of recall-oriented Google Patents keyword queries.

    The search stage is intentionally broad. Ontology-based precision is applied
    later during reranking, so this function favors recall over exact matching.
    """
    raw_patent = raw_patent or {}
    queries: list[str] = []

    technology_names = [
        x.get("technology_name")
        for x in structured_patent.get("technology_assignments", [])
        if x.get("technology_name")
    ]
    problems = [
        x.get("canonical_problem") or x.get("korean_name")
        for x in structured_patent.get("problem_assertions", [])
        if x.get("canonical_problem") or x.get("korean_name")
    ]
    functions: list[str] = []
    elements: list[str] = []
    relations: list[str] = []
    for claim in structured_patent.get("independent_claims", []):
        functions.extend(
            f.get("canonical_function") for f in claim.get("function_assignments", []) if f.get("canonical_function")
        )
        elements.extend(
            e.get("canonical_name") for e in claim.get("claim_elements", []) if e.get("canonical_name")
        )
        relations.extend(
            r.get("canonical_relation") for r in claim.get("relation_assertions", []) if r.get("canonical_relation")
        )

    # Query 1: subsystem/technology + strongest element terms.
    q1_terms: list[str] = ["\"power sliding door\""]
    for name in technology_names[:2]:
        q1_terms.extend(_terms_from_name(name)[:3])
    for name in elements[:4]:
        q1_terms.extend(_terms_from_name(name)[:2])
    if len(q1_terms) > 1:
        queries.append(" ".join(dict.fromkeys(q1_terms)))

    # Query 2: problem/function mechanism. This finds different structures solving
    # the same engineering issue, which is especially useful for Module 2.
    q2_terms: list[str] = ["\"sliding door\""]
    for name in problems[:2] + functions[:4]:
        q2_terms.extend(_terms_from_name(name)[:3])
    if len(q2_terms) > 1:
        queries.append(" ".join(dict.fromkeys(q2_terms)))

    # Query 3: structural relations + key elements. Relation tokens are converted
    # from snake_case to plain search terms and used only as a recall hint.
    q3_terms: list[str] = ["\"sliding door\""]
    for name in relations[:3] + elements[:5]:
        q3_terms.extend(_terms_from_name(name)[:2])
    if len(q3_terms) > 1:
        queries.append(" ".join(dict.fromkeys(q3_terms)))

    title = (raw_patent.get("metadata") or {}).get("title") or ""
    if title:
        title_terms = _terms_from_name(title)[:6]
        if title_terms:
            queries.append("\"sliding door\" " + " ".join(title_terms))

    # Deduplicate while keeping at most three diversified searches. Overly many
    # queries increase public-source load without improving MVP quality much.
    deduped: list[str] = []
    for q in queries:
        key = q.lower().strip()
        if q and key not in {x.lower() for x in deduped}:
            deduped.append(q)
    return deduped[:3] or ["\"power sliding door\""]


def _unwrap_payload(data: dict[str, Any]) -> dict[str, Any]:
    content = data.get("content")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    if isinstance(content, dict):
        return content
    return data


def _flatten_search_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results_root = payload.get("results") if isinstance(payload.get("results"), dict) else payload
    clusters = results_root.get("cluster", []) if isinstance(results_root, dict) else []
    if isinstance(clusters, dict):
        clusters = [clusters]
    out: list[dict[str, Any]] = []
    for cluster in clusters or []:
        rows = cluster.get("result", []) if isinstance(cluster, dict) else []
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows:
            if isinstance(row, dict):
                out.append(row)
    return out


def _pick(obj: dict[str, Any], *keys: str):
    for key in keys:
        if key in obj and obj.get(key) not in (None, "", []):
            return obj.get(key)
    return None


def _normalize_publication_number(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", _clean(value)).upper()


def parse_google_patents_search_json(data: dict[str, Any], *, query: str = "") -> list[dict[str, Any]]:
    payload = _unwrap_payload(data)
    rows = _flatten_search_results(payload)
    parsed: list[dict[str, Any]] = []
    for rank_idx, row in enumerate(rows):
        patent = row.get("patent") if isinstance(row.get("patent"), dict) else row
        publication_number = _normalize_publication_number(
            _pick(patent, "publication_number", "publicationNumber", "publication")
        )
        if not publication_number:
            patent_id = _clean(_pick(patent, "id", "patent_id", "result_id"))
            m = re.search(r"/patent/([A-Z]{2}[A-Z0-9]+)/", patent_id, re.I)
            if m:
                publication_number = m.group(1).upper()
        if not publication_number:
            continue

        title = _clean(_pick(patent, "title", "invention_title", "name"))
        snippet = _clean(_pick(patent, "snippet", "abstract", "description"))
        assignee_value = _pick(patent, "assignee", "assignee_name", "owner")
        if isinstance(assignee_value, list):
            assignee = ", ".join(_clean(x) for x in assignee_value if _clean(x))
        else:
            assignee = _clean(assignee_value)
        source_url = f"{GOOGLE_PATENTS_BASE}/{publication_number}/en"

        parsed.append(
            {
                "publication_number": publication_number,
                "title": title,
                "snippet": snippet,
                "assignee": assignee,
                "priority_date": _clean(_pick(patent, "priority_date", "priorityDate")),
                "filing_date": _clean(_pick(patent, "filing_date", "filingDate")),
                "publication_date": _clean(_pick(patent, "publication_date", "publicationDate")),
                "source_url": source_url,
                "query": query,
                "search_rank": int(_pick(row, "rank", "position") or rank_idx),
            }
        )
    return parsed


def search_google_patents(query: str, *, num: int = 12, timeout: int = 18, session=None) -> list[dict[str, Any]]:
    """Search the public Google Patents search endpoint.

    Google Patents does not expose a supported official search API for this use.
    The web UI currently uses a public XHR endpoint; this function treats it as a
    best-effort source and raises a clear error if its response format changes.
    """
    http = session or requests
    inner_query = f"q={query}&num={max(1, min(int(num), 100))}&sort=relevance"
    try:
        response = http.get(
            GOOGLE_PATENTS_XHR,
            params={"url": inner_query, "exp": ""},
            headers=DEFAULT_HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise RelatedPatentSearchError(f"Google Patents 관련특허 검색에 실패했습니다: {exc}") from exc
    if not isinstance(data, dict):
        raise RelatedPatentSearchError("Google Patents 검색 응답 형식이 예상과 다릅니다.")
    return parse_google_patents_search_json(data, query=query)


def search_related_patents(
    structured_patent: dict,
    raw_patent: dict | None = None,
    *,
    per_query: int = 10,
    max_candidates: int = 20,
    session=None,
) -> tuple[list[dict[str, Any]], list[str]]:
    queries = build_related_search_queries(structured_patent, raw_patent)
    target_number = re.sub(
        r"[^A-Za-z0-9]",
        "",
        ((raw_patent or {}).get("metadata") or {}).get("publication_number") or "",
    ).upper()

    merged: dict[str, dict[str, Any]] = {}
    for query_idx, query in enumerate(queries):
        for item in search_google_patents(query, num=per_query, session=session):
            number = item["publication_number"]
            if number == target_number:
                continue
            if number not in merged:
                enriched = dict(item)
                enriched["matched_queries"] = [query]
                enriched["best_search_rank"] = item.get("search_rank", 999)
                enriched["query_index"] = query_idx
                merged[number] = enriched
            else:
                if query not in merged[number]["matched_queries"]:
                    merged[number]["matched_queries"].append(query)
                merged[number]["best_search_rank"] = min(
                    merged[number].get("best_search_rank", 999), item.get("search_rank", 999)
                )

    # Google ranking is only a recall prior. Keep diversified results, then let
    # ontology similarity rerank them after candidate analysis.
    candidates = sorted(
        merged.values(),
        key=lambda x: (x.get("query_index", 999), x.get("best_search_rank", 999)),
    )[:max_candidates]
    return candidates, queries
