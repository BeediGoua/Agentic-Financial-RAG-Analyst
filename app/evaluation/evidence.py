from __future__ import annotations

import re
import unicodedata


def normalize_evidence_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def evidence_matches_chunk(
    evidence: dict,
    chunk: dict,
) -> bool:
    document_sha256 = str(
        chunk.get("document_sha256")
        or chunk.get("source_sha256")
        or ""
    )
    if not evidence.get("document_sha256") or not document_sha256:
        return False
    if evidence["document_sha256"].lower() != document_sha256.lower():
        return False
    page_start = chunk.get("page_start")
    page_end = chunk.get("page_end")
    if page_start is None or page_end is None:
        return False
    if int(page_end) < int(evidence["page_start"]) or int(page_start) > int(evidence["page_end"]):
        return False
    quote = normalize_evidence_text(str(evidence.get("quote") or ""))
    text = normalize_evidence_text(str(chunk.get("text") or ""))
    if not quote or not text:
        return False
    return quote in text
