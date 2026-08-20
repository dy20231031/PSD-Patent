from __future__ import annotations


def parse_patent_document(raw_text: str) -> dict:
    """특허 문서를 metadata/abstract/background/claims/description 등으로 분리한다.

    TODO: 실제 patent-number retrieval 및 PDF parser를 연결한다.
    """
    return {
        "metadata": {},
        "abstract": "",
        "background": "",
        "summary": "",
        "claims": [],
        "description": "",
    }
