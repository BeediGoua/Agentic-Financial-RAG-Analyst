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
    if report.get("status") == "REAL_BENCHMARK_NOT_READY":
        lines.extend([
            "## Real benchmark status",
            "",
            "- Status: `REAL_BENCHMARK_NOT_READY`",
            "- No real BRVM metric is reported.",
            "",
            "Missing prerequisites:",
            "",
        ])
        lines.extend(f"- {item}" for item in report.get("missing", []))
        lines.append("")
    counts = report.get("counts")
    if counts:
        lines.extend([
            "## Evaluation counts",
            "",
            f"- Answerable: {counts.get('answerable', 0)}",
            f"- Unanswerable: {counts.get('unanswerable', 0)}",
            f"- Evaluated: {counts.get('evaluated', 0)}",
            f"- Ignored: {counts.get('ignored', 0)}",
            f"- Technical errors: {counts.get('technical_errors', 0)}",
            "",
        ])
    rows = report.get("per_query", [])
    configurations: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("metrics"):
            configurations.setdefault(str(row.get("configuration_id")), []).append(row)
    if configurations:
        metric_names = sorted({
            name
            for group in configurations.values()
            for row in group
            for name in row.get("metrics", {}).keys()
            if isinstance(row.get("metrics", {}).get(name), (int, float))
        })
        lines.extend(["## Configuration comparison", "", "| Configuration | " + " | ".join(metric_names) + " |", "|" + "---|" * (len(metric_names) + 1)])
        for configuration_id, group in sorted(configurations.items()):
            values = []
            for name in metric_names:
                samples = [
                    float(row["metrics"][name])
                    for row in group
                    if row.get("metrics", {}).get(name) is not None
                    and isinstance(row["metrics"][name], (int, float))
                ]
                values.append(f"{sum(samples) / len(samples):.4f}" if samples else "-")
            lines.append("| " + configuration_id + " | " + " | ".join(values) + " |")
        lines.extend(["", "## Results by question", "", "| Question | Split | Configuration | Status | Metrics |", "|---|---|---|---|---|"])
        for row in rows:
            metrics = row.get("metrics") or {}
            metrics_text = ", ".join(
                f"{key}={value:.4f}"
                for key, value in sorted(metrics.items())
                if isinstance(value, (int, float))
            )
            lines.append(
                f"| {row.get('question_id')} | {row.get('split', '-')} | "
                f"{row.get('configuration_id')} | {row.get('status')} | {metrics_text} |"
            )
    text = "\n".join(lines)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
