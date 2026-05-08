# Agentic-Financial-RAG-Analyst
Oui. On modifie comme ça :

* les vraies actions restent des fonctions Python fiables ;
* ces fonctions deviennent des tools Smolagents ;
* un CodeAgent superviseur choisit quoi appeler ;
* on garde le choix entreprise + année dès le prompt.

Nouvelle architecture

app/
  ingest/
    schemas.py
    brvm_tools.py
    quality_tools.py
    storage_tools.py
    model_provider.py
    run_smol_ingestion.py
data/
  raw/
  metadata/
  logs/

Smolagents est adapté ici parce que CodeAgent peut appeler des tools Python sous forme de code, faire des boucles, filtrer les résultats et orchestrer les étapes. Mais attention : le scraping, le téléchargement et la validation PDF doivent rester déterministes. Smolagents sert surtout de superviseur.  ￼

1) Installation

pip install smolagents requests beautifulsoup4 pydantic tqdm

2) app/ingest/schemas.py

from pydantic import BaseModel
class ReportDocument(BaseModel):
    source: str
    title: str
    page_url: str
    pdf_url: str
    company: str | None = None
    year: str | None = None
    document_type: str | None = None

3) app/ingest/brvm_tools.py

from __future__ import annotations
import json
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from smolagents import tool
from app.ingest.schemas import ReportDocument
BRVM_LISTING_PAGES = [
    "https://www.brvm.org/fr/type-document/rapports-annuels",
    "https://www.brvm.org/fr/type-document/etats-financiers",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 Financial-RAG-Analyst/0.1 educational project"
}
def extract_year(text: str) -> str | None:
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else None
def infer_document_type(text: str) -> str:
    text = text.lower()
    if "rapport" in text and "annuel" in text:
        return "annual_report"
    if "etats financiers" in text or "états financiers" in text:
        return "financial_statements"
    if "trimestre" in text or "trimestriel" in text:
        return "quarterly_report"
    if "semestre" in text or "semestriel" in text:
        return "half_year_report"
    return "other"
def infer_company(title: str) -> str | None:
    if ":" in title:
        return title.split(":")[0].strip()
    if "-" in title:
        return title.split("-")[0].strip()
    return None
def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    title = soup.find("title")
    if title:
        return title.get_text(" ", strip=True)
    return "untitled"
def find_document_pages(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    keywords = [
        "rapport",
        "etats financiers",
        "états financiers",
        "exercice",
        "trimestre",
        "semestre",
    ]
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        candidate = f"{href} {text}".lower()
        if any(k in candidate for k in keywords):
            full_url = urljoin(base_url, href)
            if "brvm.org" in full_url and "/fr/" in full_url:
                links.add(full_url)
    return sorted(links)
def find_pdf_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    pdfs = set()
    for a in soup.find_all("a", href=True):
        full_url = urljoin(page_url, a["href"])
        if ".pdf" in full_url.lower():
            pdfs.add(full_url)
    return sorted(pdfs)
def normalize_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [x.strip().lower() for x in value.split(",") if x.strip()]
def report_matches(
    report: ReportDocument,
    companies: list[str] | None,
    years: list[str] | None,
) -> bool:
    if companies:
        company = (report.company or "").lower()
        title = (report.title or "").lower()
        if not any(c in company or c in title for c in companies):
            return False
    if years:
        if report.year not in years:
            return False
    return True
@tool
def discover_brvm_reports(
    companies: str = "",
    years: str = "",
    max_pages: int = 5,
) -> str:
    """
    Discover BRVM public financial reports and return matching reports as JSON.
    Args:
        companies: Comma-separated company names. Example: "CIE CI,SONATEL". Empty means all companies.
        years: Comma-separated years. Example: "2023,2024". Empty means all years.
        max_pages: Number of BRVM listing pages to scan.
    Returns:
        JSON string containing discovered report metadata.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    selected_companies = normalize_list(companies)
    selected_years = normalize_list(years)
    reports: list[ReportDocument] = []
    for listing_base_url in BRVM_LISTING_PAGES:
        for page in range(max_pages):
            listing_url = listing_base_url if page == 0 else f"{listing_base_url}?page={page}"
            try:
                response = session.get(listing_url, timeout=60)
                response.raise_for_status()
                document_pages = find_document_pages(response.text, listing_url)
            except Exception:
                continue
            for document_page in document_pages:
                try:
                    response = session.get(document_page, timeout=60)
                    response.raise_for_status()
                    title = extract_title(response.text)
                    pdf_links = find_pdf_links(response.text, document_page)
                    for pdf_url in pdf_links:
                        full_text = f"{title} {pdf_url}"
                        report = ReportDocument(
                            source="BRVM",
                            title=title,
                            page_url=document_page,
                            pdf_url=pdf_url,
                            company=infer_company(title),
                            year=extract_year(full_text),
                            document_type=infer_document_type(full_text),
                        )
                        if report_matches(report, selected_companies, selected_years):
                            reports.append(report)
                    time.sleep(1)
                except Exception:
                    continue
            time.sleep(1)
    unique = {}
    for report in reports:
        unique[report.pdf_url] = report
    return json.dumps(
        [r.model_dump() for r in unique.values()],
        indent=2,
        ensure_ascii=False,
    )

4) app/ingest/quality_tools.py

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from smolagents import tool
@tool
def validate_pdf_file(path: str) -> str:
    """
    Validate that a local file exists and is probably a PDF.
    Args:
        path: Local path of the downloaded file.
    Returns:
        JSON string with validation status.
    """
    file_path = Path(path)
    if not file_path.exists():
        return json.dumps({"valid": False, "reason": "file_not_found"})
    if file_path.stat().st_size < 1_000:
        return json.dumps({"valid": False, "reason": "file_too_small"})
    with file_path.open("rb") as f:
        header = f.read(5)
    if header != b"%PDF-":
        return json.dumps({"valid": False, "reason": "invalid_pdf_header"})
    return json.dumps({"valid": True, "reason": "ok"})
@tool
def compute_file_checksum(path: str) -> str:
    """
    Compute SHA256 checksum of a local file.
    Args:
        path: Local file path.
    Returns:
        SHA256 checksum string.
    """
    file_path = Path(path)
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

5) app/ingest/storage_tools.py

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
def download_report_pdf(report_json: str, root_dir: str = "data/raw/reports") -> str:
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
def load_existing_checksums(root_dir: str = "data/raw/reports") -> str:
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

6) app/ingest/model_provider.py

import os
from smolagents import HfApiModel, LiteLLMModel
def build_model(provider: str = "ollama", model_id: str | None = None):
    if provider == "ollama":
        return LiteLLMModel(
            model_id=model_id or "ollama/qwen2.5-coder:7b",
            api_base=os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
            temperature=0.1,
        )
    if provider == "huggingface":
        return HfApiModel(
            model_id=model_id or "Qwen/Qwen2.5-Coder-32B-Instruct",
            temperature=0.1,
            max_tokens=4096,
        )
    raise ValueError(f"Unknown provider: {provider}")

7) app/ingest/run_smol_ingestion.py

from __future__ import annotations
import argparse
from smolagents import CodeAgent
from app.ingest.brvm_tools import discover_brvm_reports
from app.ingest.quality_tools import validate_pdf_file, compute_file_checksum
from app.ingest.storage_tools import (
    download_report_pdf,
    load_existing_checksums,
    save_report_metadata,
    save_ingestion_log,
)
from app.ingest.model_provider import build_model
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--companies",
        type=str,
        default="",
        help='Entreprises séparées par virgule. Exemple: "CIE CI,SONATEL"',
    )
    parser.add_argument(
        "--years",
        type=str,
        default="",
        help='Années séparées par virgule. Exemple: "2023,2024"',
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Nombre de pages BRVM à parcourir.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Nombre maximum de rapports à traiter.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="ollama",
        choices=["ollama", "huggingface"],
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default=None,
    )
    args = parser.parse_args()
    model = build_model(provider=args.provider, model_id=args.model_id)
    ingestion_agent = CodeAgent(
        tools=[
            discover_brvm_reports,
            download_report_pdf,
            validate_pdf_file,
            compute_file_checksum,
            load_existing_checksums,
            save_report_metadata,
            save_ingestion_log,
        ],
        model=model,
        max_steps=25,
        additional_authorized_imports=["json"],
    )
    task = f"""
You are the ingestion supervisor for a Financial RAG Analyst project.
Goal:
Download BRVM financial reports according to user filters.
Filters:
- companies: "{args.companies}"
- years: "{args.years}"
- max_pages: {args.max_pages}
- limit: {args.limit}
Strict workflow:
1. Call discover_brvm_reports(companies, years, max_pages).
2. Parse the returned JSON list.
3. Keep at most {args.limit} reports.
4. Call load_existing_checksums().
5. For each report:
   - call download_report_pdf(report_json)
   - call validate_pdf_file(local_path)
   - if invalid, add result with status "invalid_pdf"
   - call compute_file_checksum(local_path)
   - if checksum already exists, add result with status "duplicate"
   - otherwise call save_report_metadata(report_json, local_path, checksum, "success")
   - add result with status "success"
6. Call save_ingestion_log(results_json).
7. Return a clear summary with:
   - selected companies
   - selected years
   - discovered reports
   - downloaded reports
   - duplicates
   - invalid PDFs
   - errors
   - log path
Important:
Do not invent URLs.
Do not create fake reports.
Only use tool outputs.
"""
    result = ingestion_agent.run(task)
    print(result)
if __name__ == "__main__":
    main()

8) Commandes

Avec Ollama + Qwen Coder :

ollama pull qwen2.5-coder:7b
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --model-id "ollama/qwen2.5-coder:7b" \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5

Plusieurs entreprises + plusieurs années :

python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --model-id "ollama/qwen2.5-coder:7b" \
  --companies "CIE CI,SONATEL,ORANGE CI" \
  --years "2023,2024" \
  --limit 20

Toutes les entreprises pour 2024 :

python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --years "2024" \
  --limit 30

Version roadmap corrigée

PHASE 1 — Collecte et stockage des données
Objectif :
Construire une ingestion fiable des rapports financiers publics.
Approche :
Pipeline déterministe orchestré avec Smolagents.
Architecture :
- Tools Python :
  - discover_brvm_reports()
  - download_report_pdf()
  - validate_pdf_file()
  - compute_file_checksum()
  - load_existing_checksums()
  - save_report_metadata()
  - save_ingestion_log()
- Agent superviseur :
  - CodeAgent Smolagents
  - choisit les tools à appeler
  - applique les filtres entreprise / année
  - contrôle le workflow
  - produit un résumé d’exécution
Choix utilisateur :
- une entreprise ou plusieurs ;
- une année ou plusieurs ;
- toutes les entreprises ;
- toutes les années disponibles ;
- limite de rapports pour tester.
Principe important :
Le LLM ne fait pas le scraping lui-même.
Il orchestre des tools fiables.
Les actions critiques restent en Python déterministe.

À retenir : oui, là on utilise bien Smolagents, mais proprement. Le CodeAgent est le manager, et les fonctions Python sont ses outils. C’est exactement le bon niveau d’agentique pour cette phase.