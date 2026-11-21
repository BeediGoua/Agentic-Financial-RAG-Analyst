from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def write_csv_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_markdown(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# G3 retrieval benchmark report",
        "",
        f"- Synthetic: `{report.get('synthetic', False)}`",
        f"- Run ID: `{report.get('run_id', 'unknown')}`",
        f"- Seed: `{report.get('seed', 'unset')}`",
        "",
    ]
    if report.get("synthetic"):
        lines.append(
            "> This report contains synthetic fixture results only and is not "
            "representative of BRVM retrieval performance."
        )
        lines.append("")
    text = "\n".join(lines)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
