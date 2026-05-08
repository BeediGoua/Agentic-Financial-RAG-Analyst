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
