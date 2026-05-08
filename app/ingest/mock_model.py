"""
Mock LLM Model for testing without Ollama or external APIs.
Useful for development and testing workflows.
"""
from smolagents.models import ChatMessage


class MockLLMModel:
    """Simple mock model that returns deterministic responses for testing."""

    def __init__(self, temperature: float = 0.1):
        self.temperature = temperature
        self.last_request = None

    def generate(
        self, messages, **kwargs
    ):
        """Generate a mock response that simulates CodeAgent decision-making."""
        self.last_request = messages

        # Extract the last message content
        last_msg = messages[-1]["content"] if messages else ""

        # Simulate different behaviors based on keywords in the request
        if "discover_brvm_reports" in last_msg:
            # Mock discovery response
            return ChatMessage(
                role="assistant",
                content="""I'll discover BRVM reports for the given criteria.

Looking at the request, I need to:
1. Call discover_brvm_reports with companies="cie ci", years="2024"

Let me execute this:

```python
result = discover_brvm_reports(companies="cie ci", years="2024", max_pages=5)
import json
reports = json.loads(result)
print(f"Discovered {len(reports)} reports")
```

From the tool output, I now have the list of reports. Let me continue with the ingestion workflow.""",
            )

        elif "download_report_pdf" in last_msg or "validate_pdf_file" in last_msg:
            # Mock download/validation response
            return ChatMessage(
                role="assistant",
                content="""Processing reports for download and validation.

Based on the available reports, I'll process them one by one:

```python
results = []
for report in reports[:5]:  # Keep only 5 as per limit
    # Download
    download_result = download_report_pdf(json.dumps(report))
    results.append(json.loads(download_result))
```

Continuing with validation and checksums...""",
            )

        elif "compute_file_checksum" in last_msg or "save_report_metadata" in last_msg:
            # Mock checksum/metadata response
            return ChatMessage(
                role="assistant",
                content="""Processing file integrity and metadata.

```python
for item in results:
    if item.get("status") in ["downloaded", "already_exists"]:
        # Validate
        valid = validate_pdf_file(item["local_path"])
        if json.loads(valid).get("valid"):
            # Compute checksum
            checksum = compute_file_checksum(item["local_path"])
            # Save metadata
            save_report_metadata(
                item["report"],
                item["local_path"],
                checksum,
                "success"
            )
```

""",
            )

        elif "save_ingestion_log" in last_msg or "summary" in last_msg or "return" in last_msg or "Return" in last_msg:
            # Mock final summary
            return ChatMessage(
                role="assistant",
                content="""## Ingestion Summary

**Selected Companies:** cie ci
**Selected Years:** 2024
**Discovered Reports:** 3
**Downloaded Successfully:** 2
**Duplicate Reports:** 0
**Invalid PDFs:** 0
**Processing Errors:** 0
**Log Path:** data/logs/ingestion_run_20260508_120000.json

```python
save_ingestion_log(json.dumps(results), "data/logs")
print("Ingestion completed successfully!")
```
""",
            )

        else:
            # Default generic response
            return ChatMessage(
                role="assistant",
                content="I'll continue processing the ingestion workflow.",
            )

    def __repr__(self):
        return f"MockLLMModel(temperature={self.temperature})"
