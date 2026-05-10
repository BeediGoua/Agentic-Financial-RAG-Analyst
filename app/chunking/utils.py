from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []

    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            if hasattr(row, "model_dump_json"):
                f.write(row.model_dump_json() + "\n")
            else:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_text(text: str | None) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def make_chunk_id(
    strategy: str,
    source_pdf: str,
    page_start: int,
    page_end: int,
    index: int,
    text: str,
) -> str:
    raw = f"{strategy}|{source_pdf}|{page_start}|{page_end}|{index}|{text[:120]}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{strategy}_{digest}"


def matches_filter(
    record: dict,
    companies: list[str] | None = None,
    years: list[str] | None = None,
) -> bool:
    company = str(record.get("company") or "").lower()
    year = str(record.get("year") or "")

    if companies:
        if not any(c.lower() in company for c in companies):
            return False

    if years:
        if year not in years:
            return False

    return True


def group_pages_by_document(pages: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}

    for page in pages:
        source_pdf = page.get("source_pdf")
        if not source_pdf:
            continue

        grouped.setdefault(source_pdf, []).append(page)

    for source_pdf in grouped:
        grouped[source_pdf] = sorted(
            grouped[source_pdf],
            key=lambda x: int(x.get("page_number") or 0),
        )

    return grouped


def recursive_split_text(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
    separators: list[str] | None = None,
) -> list[str]:
    """
    Recursive splitter simple, inspiré du principe LangChain :
    essayer d'abord les gros séparateurs, puis les plus fins.
    """

    text = normalize_text(text)

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    separators = separators or ["\n\n", "\n", ". ", "; ", ", ", " "]

    chunks: list[str] = []

    def split_recursive(part: str, seps: list[str]) -> list[str]:
        if len(part) <= chunk_size:
            return [part.strip()] if part.strip() else []

        if not seps:
            return [
                part[i : i + chunk_size].strip()
                for i in range(0, len(part), chunk_size - chunk_overlap)
                if part[i : i + chunk_size].strip()
            ]

        sep = seps[0]
        pieces = part.split(sep)

        if len(pieces) == 1:
            return split_recursive(part, seps[1:])

        merged = []
        current = ""

        for piece in pieces:
            candidate = f"{current}{sep}{piece}" if current else piece

            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current.strip():
                    merged.append(current.strip())
                current = piece

        if current.strip():
            merged.append(current.strip())

        output = []
        for item in merged:
            if len(item) > chunk_size:
                output.extend(split_recursive(item, seps[1:]))
            else:
                output.append(item)

        return output

    raw_chunks = split_recursive(text, separators)

    for chunk in raw_chunks:
        if chunk:
            chunks.append(chunk.strip())

    return chunks
