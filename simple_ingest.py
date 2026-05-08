#!/usr/bin/env python
"""
Simple ingestion runner - Tests the tools directly without LLM orchestration.
This is the simplest way to verify Phase 1 works.
No LLM required!
"""
import json
import sys
from pathlib import Path
from app.ingest.brvm_tools import discover_brvm_reports
from app.ingest.quality_tools import validate_pdf_file, compute_file_checksum
from app.ingest.storage_tools import (
    download_report_pdf,
    load_existing_checksums,
    save_report_metadata,
    save_ingestion_log,
)


def run_simple_ingestion(companies="", years="", max_pages=2, limit=5):
    """
    Run ingestion without LLM.
    This directly executes the workflow step by step.
    """
    print("\n" + "=" * 70)
    print("AGENTIC FINANCIAL RAG - SIMPLE INGESTION (No LLM Required)")
    print("=" * 70)

    # Step 1: Discover reports
    print("\n[1/6] 🔍 Discovering BRVM reports...")
    try:
        result = discover_brvm_reports(companies=companies, years=years, max_pages=max_pages)
        reports = json.loads(result)
        print(f"     ✅ Found {len(reports)} reports")
        if not reports:
            print("     (No reports found - try different filters)")
            return
    except Exception as e:
        print(f"     ❌ Error: {e}")
        return

    # Keep only limit reports
    reports = reports[:limit]
    print(f"     📌 Processing {len(reports)} reports (limit: {limit})")

    # Step 2: Load existing checksums (for dedup)
    print("\n[2/6] Loading existing checksums (for deduplication)...")
    try:
        existing = load_existing_checksums("data/raw")
        existing_checksums = set(json.loads(existing))
        print(f"     [OK] Found {len(existing_checksums)} existing checksums")
    except Exception as e:
        print(f"     [WARNING] Warning: {e}")
        existing_checksums = set()

    # Step 3-5: Process each report
    results = []
    for idx, report in enumerate(reports, 1):
        print(f"\n[3/6] Report {idx}/{len(reports)}: {report.get('title', 'Unknown')[:50]}...")

        # Download
        try:
            print(f"     📥 Downloading PDF...")
            download_result = download_report_pdf(json.dumps(report), "data/raw")
            download_data = json.loads(download_result)
            local_path = download_data.get("local_path")
            print(f"     ✅ Downloaded to: {local_path}")
        except Exception as e:
            print(f"     ❌ Download error: {e}")
            results.append({"status": "error", "report": report, "error": str(e)})
            continue

        # Validate
        if local_path:
            try:
                print(f"     🔍 Validating PDF...")
                validation = validate_pdf_file(local_path)
                val_data = json.loads(validation)
                if not val_data.get("valid"):
                    print(f"     ❌ Invalid PDF: {val_data.get('reason')}")
                    results.append({
                        "status": "invalid_pdf",
                        "report": report,
                        "local_path": local_path,
                        "reason": val_data.get("reason"),
                    })
                    continue
                print(f"     ✅ PDF is valid")
            except Exception as e:
                print(f"     ❌ Validation error: {e}")
                results.append({
                    "status": "error",
                    "report": report,
                    "local_path": local_path,
                    "error": str(e),
                })
                continue

        # Compute checksum
        if local_path:
            try:
                print(f"     🔐 Computing checksum...")
                checksum = compute_file_checksum(local_path)
                print(f"     ✅ Checksum: {checksum[:16]}...")

                # Check for duplicates
                if checksum in existing_checksums:
                    print(f"     ⚠️  Duplicate detected (already downloaded)")
                    results.append({
                        "status": "duplicate",
                        "report": report,
                        "local_path": local_path,
                        "checksum": checksum,
                    })
                    continue

                # Save metadata
                print(f"     💾 Saving metadata...")
                metadata_result = save_report_metadata(
                    json.dumps(report),
                    local_path,
                    checksum,
                    "success",
                )
                metadata_data = json.loads(metadata_result)
                print(f"     ✅ Metadata: {metadata_data.get('metadata_path')}")

                results.append({
                    "status": "success",
                    "report": report,
                    "local_path": local_path,
                    "checksum": checksum,
                    "metadata_path": metadata_data.get("metadata_path"),
                })
            except Exception as e:
                print(f"     ❌ Checksum/metadata error: {e}")
                results.append({
                    "status": "error",
                    "report": report,
                    "local_path": local_path,
                    "error": str(e),
                })

    # Step 6: Save log
    print(f"\n[6/6] 📝 Saving ingestion log...")
    try:
        log_result = save_ingestion_log(json.dumps(results), "data/logs")
        log_data = json.loads(log_result)
        print(f"     ✅ Log saved: {log_data.get('log_path')}")
    except Exception as e:
        print(f"     ❌ Log error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    success = sum(1 for r in results if r.get("status") == "success")
    duplicates = sum(1 for r in results if r.get("status") == "duplicate")
    invalid = sum(1 for r in results if r.get("status") == "invalid_pdf")
    errors = sum(1 for r in results if r.get("status") == "error")

    print(f"Total processed:       {len(results)}")
    print(f"✅ Successful:         {success}")
    print(f"⚠️  Duplicates:        {duplicates}")
    print(f"❌ Invalid PDFs:       {invalid}")
    print(f"🔴 Errors:            {errors}")

    if success > 0:
        print(f"\n✅ {success} report(s) successfully ingested!")
        print(f"📁 Location: data/raw/BRVM/")
        print(f"📊 Metadata: *.pdf.manifest.json files")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Simple ingestion without LLM - Direct tool execution"
    )
    parser.add_argument(
        "--companies", type=str, default="", help='Example: "CIE CI,SONATEL"'
    )
    parser.add_argument("--years", type=str, default="", help='Example: "2023,2024"')
    parser.add_argument(
        "--max-pages", type=int, default=2, help="BRVM pages to scan (default: 2)"
    )
    parser.add_argument("--limit", type=int, default=5, help="Max reports (default: 5)")

    args = parser.parse_args()

    run_simple_ingestion(
        companies=args.companies,
        years=args.years,
        max_pages=args.max_pages,
        limit=args.limit,
    )
