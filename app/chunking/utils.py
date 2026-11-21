from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from app.core.atomic import atomic_text_writer
from app.chunking.schemas import TextChunk


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
    with atomic_text_writer(path) as f:
        for row in rows:
            if hasattr(row, "model_dump_json"):
                f.write(row.model_dump_json() + "\n")
            else:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def validate_cached_chunks(
    output_path: str | Path,
    *,
    expected_strategy: str,
) -> tuple[bool, int]:
    path = Path(output_path)
    try:
        rows = load_jsonl(path)
        if not rows:
            return True, 0

        identifiers: set[str] = set()
        for raw in rows:
            chunk = TextChunk.model_validate(raw)
            if chunk.chunking_strategy != expected_strategy:
                return False, 0
            if not chunk.chunk_id.strip() or chunk.chunk_id in identifiers:
                return False, 0
            identifiers.add(chunk.chunk_id)
            if not chunk.source_pdf:
                return False, 0
            if chunk.page_start < 1 or chunk.page_end < chunk.page_start:
                return False, 0
            if not chunk.text.strip():
                return False, 0
            if chunk.char_count != len(chunk.text):
                return False, 0
            if chunk.word_count != len(chunk.text.split()):
                return False, 0
        return True, len(rows)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False, 0


def write_chunk_artifact(
    output_path: str | Path,
    rows: list,
    fingerprint: dict,
) -> None:
    from app.core.artifact_cache import write_artifact_manifest

    output_path = Path(output_path)
    manifest_path = Path(str(output_path) + ".build.json")
    backup_dir = output_path.parent / ".g2-chunk-backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    output_backup = backup_dir / output_path.name
    manifest_backup = backup_dir / manifest_path.name

    if output_path.exists():
        shutil.copy2(output_path, output_backup)
    if manifest_path.exists():
        shutil.copy2(manifest_path, manifest_backup)

    try:
        write_jsonl(output_path, rows)
        write_artifact_manifest(output_path, fingerprint)
    except Exception:
        if output_backup.exists():
            os.replace(output_backup, output_path)
        else:
            output_path.unlink(missing_ok=True)
        if manifest_backup.exists():
            os.replace(manifest_backup, manifest_path)
        else:
            manifest_path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)


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
    from app.core.universe import canonical_company
    import yaml

    universe_path = Path("config/universe.yaml")
    universe = {"companies": []}
    if universe_path.is_file():
        try:
            loaded = yaml.safe_load(universe_path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                universe = loaded
        except (OSError, yaml.YAMLError):
            pass

    company = canonical_company(str(record.get("company") or ""), universe)
    year = str(record.get("year") or "")

    if companies:
        accepted = {
            canonical_company(str(c), universe) or f"unknown:{normalize_text(str(c)).lower()}"
            for c in companies
        }
        if company not in accepted:
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

    if not raw_chunks:
        return []

    chunks: list[str] = []
    covered_until = 0
    for raw_chunk in raw_chunks:
        chunk = raw_chunk.strip()
        if not chunk:
            continue

        if chunks:
            prefix = chunks[-1][-chunk_overlap:] if chunk_overlap > 0 else ""
            combined = f"{prefix} {chunk}".strip() if prefix else chunk
            if len(combined) <= chunk_size:
                chunk = combined

        if len(chunk) > chunk_size:
            chunk = chunk[:chunk_size]

        chunks.append(chunk)

    # Guarantee exact coverage even when overlap cannot fit in the size limit.
    if "".join(chunks).strip():
        return chunks
    return [text[:chunk_size]]
