from __future__ import annotations

import unicodedata
import re


def normalize_evidence_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def evidence_matches_chunk(
    evidence: dict,
    chunk: dict,
) -> bool:
    document_sha256 = str(chunk.get("document_sha256") or "")
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
    if quote not in text:
        evidence_numbers = re.findall(r"(?<![\w.])[-+]?(?:\d[\d\s]*(?:[.,]\d+)?)", quote)
        text_numbers = re.findall(r"(?<![\w.])[-+]?(?:\d[\d\s]*(?:[.,]\d+)?)", text)
        normalized_evidence_numbers = [
            normalize_evidence_text(number).replace(" ", "")
            for number in evidence_numbers
        ]
        normalized_text_numbers = {
            normalize_evidence_text(number).replace(" ", "")
            for number in text_numbers
        }
        if normalized_evidence_numbers and not all(
            number in normalized_text_numbers for number in normalized_evidence_numbers
        ):
            return False
        return quote.lower() in text.lower()

    evidence_numbers = re.findall(r"(?<![\w.])[-+]?(?:\d[\d\s]*(?:[.,]\d+)?)", quote)
    text_numbers = re.findall(r"(?<![\w.])[-+]?(?:\d[\d\s]*(?:[.,]\d+)?)", text)
    if evidence_numbers:
        evidence_number_set = {
            normalize_evidence_text(number).replace(" ", "")
            for number in evidence_numbers
        }
        text_number_set = {
            normalize_evidence_text(number).replace(" ", "")
            for number in text_numbers
        }
        if evidence_number_set != evidence_number_set.intersection(text_number_set):
            return False

    known_units = ("fcfa", "xof", "millions", "million", "millions de", "usd", "eur", "euro", "euros", "%")
    evidence_units = {unit for unit in known_units if re.search(rf"\b{re.escape(unit)}\b", quote.lower())}
    text_units = {unit for unit in known_units if re.search(rf"\b{re.escape(unit)}\b", text.lower())}
    if evidence_units and not evidence_units.issubset(text_units):
        return False

    for field_name in ("unit", "column", "table_column"):
        expected = normalize_evidence_text(str(evidence.get(field_name) or ""))
        if expected:
            found = normalize_evidence_text(str(chunk.get(field_name) or ""))
            if found and expected.lower() != found.lower():
                return False
            if not found and expected.lower() not in text.lower():
                return False
    return True
