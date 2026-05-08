from __future__ import annotations
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from smolagents import tool


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")


def build_local_path(report: dict, root_dir: str) -> Path:
    source = slugify(report.get("source") or "unknown_source")
    company = slugify(report.get("company") or "unknown_company")
    year = report.get("year") or "unknown_year"
    document_type = report.get("document_type") or "other"
    filename = Path(urlparse(report["pdf_url"]).path).name
    if not filename.lower().endswith(".pdf"):
        filename = slugify(report.get("title") or "report") + ".pdf"
    output_dir = Path(root_dir) / source / company / year / document_type
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / filename


@tool
def download_report_pdf(report_json: str, root_dir: str = "data/raw") -> str:
    """
    Download one report PDF from a report JSON object.
    Args:
        report_json: JSON string describing one report.
        root_dir: Root folder where PDFs are stored.
    Returns:
        JSON string with local_path and status.
    """
    report = json.loads(report_json)
    output_path = build_local_path(report, root_dir)
    if output_path.exists() and output_path.stat().st_size > 0:
        return json.dumps({
            "status": "already_exists",
            "local_path": str(output_path),
            "report": report,
        }, ensure_ascii=False)
    response = requests.get(report["pdf_url"], timeout=90)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return json.dumps({
        "status": "downloaded",
        "local_path": str(output_path),
        "report": report,
    }, ensure_ascii=False)


@tool
def load_existing_checksums(root_dir: str = "data/raw") -> str:
    """
    Load checksums already present in manifest files.
    Args:
        root_dir: Root folder where reports are stored.
    Returns:
        JSON list of checksums.
    """
    checksums = []
    for manifest in Path(root_dir).rglob("*.manifest.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            checksum = data.get("checksum_sha256")
            if checksum:
                checksums.append(checksum)
        except Exception:
            continue
    return json.dumps(checksums, ensure_ascii=False)


@tool
def save_report_metadata(
    report_json: str,
    local_path: str,
    checksum: str,
    status: str,
) -> str:
    """
    Save metadata manifest next to the downloaded PDF.
    Args:
        report_json: JSON string describing one report.
        local_path: Local PDF path.
        checksum: SHA256 checksum.
        status: Processing status.
    Returns:
        JSON string with metadata path.
    """
    report = json.loads(report_json)
    metadata = {
        **report,
        "local_path": local_path,
        "checksum_sha256": checksum,
        "status": status,
        "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    metadata_path = Path(local_path).with_suffix(".manifest.json")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return json.dumps({"metadata_path": str(metadata_path)}, ensure_ascii=False)


@tool
def save_ingestion_log(results_json: str, logs_dir: str = "data/logs") -> str:
    """
    Save ingestion run log.
    Args:
        results_json: JSON list of ingestion results.
        logs_dir: Folder where logs are stored.
    Returns:
        JSON string with log path.
    """
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = Path(logs_dir) / f"ingestion_run_{timestamp}.json"
    results = json.loads(results_json)
    log_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return json.dumps({"log_path": str(log_path)}, ensure_ascii=False)
