#!/usr/bin/env python
"""
Test script for ingestion tools without LLM dependency.
Run this to verify that all tools work correctly.
"""
import json
from pathlib import Path

# Import tools
from app.ingest.brvm_tools import discover_brvm_reports
from app.ingest.quality_tools import validate_pdf_file, compute_file_checksum
from app.ingest.storage_tools import (
    download_report_pdf,
    load_existing_checksums,
    save_report_metadata,
    save_ingestion_log,
)


def test_brvm_discovery():
    """Test BRVM report discovery."""
    print("\n" + "=" * 60)
    print("TEST 1: BRVM Report Discovery")
    print("=" * 60)
    try:
        print("Discovering BRVM reports for CIE CI (2024)...")
        result = discover_brvm_reports(companies="cie ci", years="2024", max_pages=2)
        reports = json.loads(result)
        print(f"[OK] Success! Discovered {len(reports)} reports")
        if reports:
            print(f"   Sample report: {reports[0]['title'][:60]}...")
        return reports
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return []


def test_checksum_functions():
    """Test checksum and validation functions."""
    print("\n" + "=" * 60)
    print("TEST 2: Checksum & Validation Functions")
    print("=" * 60)

    # Create a test PDF file
    test_file = Path("test_sample.pdf")
    test_file.write_bytes(b"%PDF-1.4\nTest content here")

    try:
        # Test validation
        print("Testing PDF validation...")
        validation = validate_pdf_file(str(test_file))
        val_result = json.loads(validation)
        if val_result.get("valid"):
            print(f"PDF validation passed")
        else:
            print(f"PDF validation failed: {val_result.get('reason')}")

        # Test checksum
        print("Computing file checksum...")
        checksum = compute_file_checksum(str(test_file))
        print(f"Checksum computed: {checksum[:16]}...")

        # Test loading existing checksums
        print("Loading existing checksums...")
        existing = load_existing_checksums("data/raw")
        checksums = json.loads(existing)
        print(f"Found {len(checksums)} existing checksums")

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        test_file.unlink(missing_ok=True)


def test_storage_functions():
    """Test storage and metadata functions."""
    print("\n" + "=" * 60)
    print("TEST 3: Storage & Metadata Functions")
    print("=" * 60)

    # Create a test report
    test_report = {
        "source": "BRVM",
        "title": "Test Annual Report",
        "page_url": "https://brvm.org/test",
        "pdf_url": "https://brvm.org/test.pdf",
        "company": "TEST COMPANY",
        "year": "2024",
        "document_type": "annual_report",
    }

    try:
        # Test ingestion log (without actual downloads)
        print("Testing ingestion log function...")
        log_data = [
            {
                "status": "test",
                "report": test_report,
                "message": "Test log entry",
            }
        ]
        log_result = save_ingestion_log(json.dumps(log_data), "data/logs")
        log_path = json.loads(log_result)
        print(f"Ingestion log created: {log_path.get('log_path')}")

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# INGESTION TOOLS TEST SUITE")
    print("#" * 60)

    reports = test_brvm_discovery()
    storage_ok = test_storage_functions()
    checksum_ok = test_checksum_functions()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"BRVM Discovery: {' PASS' if reports else ' PARTIAL (no reports found)'}")
    print(f"Storage Functions: {'PASS' if storage_ok else ' FAIL'}")
    print(f"Checksum Functions: {'PASS' if checksum_ok else 'FAIL'}")

    if storage_ok and checksum_ok:
        print("\nAll core tools are working!")
        print("\nNext step: Configure an LLM server")
        print("  - Option 1: ollama serve (localhost:11434)")
        print("  - Option 2: Use HuggingFace API (needs HUGGINGFACE_API_KEY)")
        print("  - Option 3: Use --mock flag for testing")
    else:
        print("\n Some tests failed. Check the output above.")


if __name__ == "__main__":
    run_all_tests()
