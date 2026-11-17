from __future__ import annotations

import json
import logging
from pathlib import Path

import fitz
import pytest
import requests

from app.ingest.schemas import ReportDocument
from app.ingest.url_security import (
    BRVM_HTML_HOSTS,
    MAX_REDIRECTS,
    configured_pdf_hosts,
    get_trusted_response,
    validate_https_url,
)


def _pdf_bytes() -> bytes:
    with fitz.open() as document:
        page = document.new_page()
        for line in range(45):
            page.insert_text((40, 35 + line * 12), f"Financial statement line {line}")
        return document.tobytes()


def _report(url: str = "https://www.brvm.org/files/report.pdf") -> ReportDocument:
    return ReportDocument(
        title="Orange CI - Rapport annuel 2025",
        page_url="https://www.brvm.org/fr/rapport-annuel",
        pdf_url=url,
        company="ORANGE CI",
        year="2025",
        document_type="annual_report",
        source_url="https://www.brvm.org/fr/rapport-annuel",
        language="fr",
    )


def _report_with_path_fields(
    *,
    year: str | None = "2025",
    document_type: str | None = "annual_report",
) -> ReportDocument:
    return _report().model_copy(
        update={"year": year, "document_type": document_type}
    )


class FakeResponse:
    def __init__(
        self,
        content: bytes = b"",
        *,
        text: str = "",
        status_code: int = 200,
        headers: dict | None = None,
    ):
        self.content = content
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False

    def close(self):
        self.closed = True

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=65_536):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset : offset + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class RecordingSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError(f"Unexpected network call: {url}")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.parametrize(
    "url",
    [
        "https://brvm.org/fr/rapport-annuel",
        "https://www.brvm.org/fr/etats-financiers",
    ],
)
def test_approved_brvm_urls_are_accepted(url):
    assert validate_https_url(url, allowed_hosts=BRVM_HTML_HOSTS) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://evil-brvm.org/fr/rapport",
        "https://brvm.org.evil.example/fr/rapport",
        "https://brvm.org@evil.example/fr/rapport",
        "http://127.0.0.1/admin",
        "http://localhost:8000/private",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "https://127.0.0.1/private",
        "https://localhost/private",
        "https://www.brvm.org:8443/fr/rapport",
        "ftp://www.brvm.org/rapport.pdf",
        "https://evil.example/rapport.pdf",
    ],
)
def test_untrusted_urls_are_rejected(url):
    with pytest.raises(ValueError):
        validate_https_url(url, allowed_hosts=BRVM_HTML_HOSTS)


def test_url_with_control_characters_or_credentials_is_rejected():
    for url in (
        "https://www.brvm.org/\nprivate",
        "https://user:password@www.brvm.org/fr/",
    ):
        with pytest.raises(ValueError):
            validate_https_url(url, allowed_hosts=BRVM_HTML_HOSTS)


def test_configured_pdf_hosts_are_explicit_and_validated(monkeypatch):
    monkeypatch.setenv("BRVM_ALLOWED_PDF_HOSTS", "cdn.example.com, docs.example.org ")
    assert configured_pdf_hosts() == frozenset(
        {"brvm.org", "www.brvm.org", "cdn.example.com", "docs.example.org"}
    )

    monkeypatch.setenv("BRVM_ALLOWED_PDF_HOSTS", "http://evil.example")
    with pytest.raises(ValueError, match="Invalid explicitly approved"):
        configured_pdf_hosts()


def test_document_discovery_rejects_fake_brvm_domain(caplog):
    from app.ingest.brvm_source import BRVMSourceAgent

    html = """
    <a href="https://evil-brvm.org/fr/rapport-annuel">Rapport annuel frauduleux</a>
    <a href="https://www.brvm.org/fr/rapport-annuel">Rapport annuel officiel</a>
    """
    with caplog.at_level(logging.WARNING):
        links = BRVMSourceAgent.find_document_pages(
            html,
            "https://www.brvm.org/fr/",
        )

    assert links == ["https://www.brvm.org/fr/rapport-annuel"]
    assert any(getattr(record, "event", None) == "brvm_url_rejected" for record in caplog.records)


def test_pdf_discovery_rejects_untrusted_host_and_logs(caplog, monkeypatch):
    from app.ingest.brvm_source import BRVMSourceAgent

    html = """
    <a href="https://evil.example/private.pdf">Faux PDF</a>
    <a href="/sites/default/files/rapport.pdf">Rapport officiel</a>
    """
    with caplog.at_level(logging.WARNING):
        links = BRVMSourceAgent.find_pdf_links(
            html,
            "https://www.brvm.org/fr/rapports",
        )
    assert links == ["https://www.brvm.org/sites/default/files/rapport.pdf"]
    assert any(
        getattr(record, "event", None) == "brvm_pdf_url_rejected"
        for record in caplog.records
    )

    monkeypatch.setenv("BRVM_ALLOWED_PDF_HOSTS", "cdn.example.com")
    assert BRVMSourceAgent.find_pdf_links(
        '<a href="https://cdn.example.com/report.pdf">Rapport</a>',
        "https://www.brvm.org/fr/rapports",
    ) == ["https://cdn.example.com/report.pdf"]
    assert BRVMSourceAgent.find_pdf_links(
        '<a href="/download?file=report.pdf">Rapport</a>',
        "https://www.brvm.org/fr/rapports",
    ) == ["https://www.brvm.org/download?file=report.pdf"]


def test_invalid_pdf_host_configuration_fails_discovery(monkeypatch):
    from app.ingest.brvm_source import BRVMSourceAgent

    monkeypatch.setenv("BRVM_ALLOWED_PDF_HOSTS", "https://cdn.example.com")
    with pytest.raises(ValueError, match="Invalid explicitly approved"):
        BRVMSourceAgent.find_pdf_links(
            '<a href="/report.pdf">Rapport</a>',
            "https://www.brvm.org/fr/rapports",
        )


def test_redirect_to_local_address_is_rejected_and_response_closed():
    redirect = FakeResponse(status_code=302, headers={"Location": "http://127.0.0.1:8000/private"})
    session = RecordingSession([redirect])
    with pytest.raises(ValueError):
        get_trusted_response(
            session,
            "https://www.brvm.org/fr/rapport",
            allowed_hosts=BRVM_HTML_HOSTS,
        )
    assert len(session.calls) == 1
    assert session.calls[0][1]["allow_redirects"] is False
    assert redirect.closed


def test_official_redirect_is_validated_and_final_response_is_caller_owned():
    redirect = FakeResponse(
        status_code=302,
        headers={"Location": "/fr/rapport-final"},
    )
    final = FakeResponse(text="official")
    session = RecordingSession([redirect, final])
    response = get_trusted_response(
        session,
        "https://www.brvm.org/fr/rapport",
        allowed_hosts=BRVM_HTML_HOSTS,
    )
    assert [call[0] for call in session.calls] == [
        "https://www.brvm.org/fr/rapport",
        "https://www.brvm.org/fr/rapport-final",
    ]
    assert all(call[1]["allow_redirects"] is False for call in session.calls)
    assert redirect.closed
    assert not final.closed
    response.close()
    assert final.closed


@pytest.mark.parametrize(
    "location",
    [
        "https://evil-brvm.org/fr/rapport.pdf",
        "https://www.brvm.org:8443/fr/rapport.pdf",
    ],
)
def test_redirect_to_similar_host_or_unapproved_port_is_rejected(location):
    redirect = FakeResponse(status_code=302, headers={"Location": location})
    session = RecordingSession([redirect])
    with pytest.raises(ValueError):
        get_trusted_response(
            session,
            "https://www.brvm.org/fr/rapport",
            allowed_hosts=BRVM_HTML_HOSTS,
        )
    assert len(session.calls) == 1
    assert redirect.closed


def test_redirect_without_location_is_rejected_and_closed():
    redirect = FakeResponse(status_code=301)
    with pytest.raises(ValueError, match="without Location"):
        get_trusted_response(
            RecordingSession([redirect]),
            "https://www.brvm.org/fr/rapport",
            allowed_hosts=BRVM_HTML_HOSTS,
        )
    assert redirect.closed


def test_redirect_limit_is_enforced_and_every_response_is_closed():
    redirects = [
        FakeResponse(status_code=302, headers={"Location": f"/fr/{index}"})
        for index in range(MAX_REDIRECTS + 2)
    ]
    session = RecordingSession(redirects)
    with pytest.raises(ValueError, match="Too many redirects"):
        get_trusted_response(
            session,
            "https://www.brvm.org/fr/start",
            allowed_hosts=BRVM_HTML_HOSTS,
            max_redirects=MAX_REDIRECTS,
        )
    assert len(session.calls) == MAX_REDIRECTS + 1
    assert all(response.closed for response in redirects[: MAX_REDIRECTS + 1])


def test_http_error_response_is_closed():
    response = FakeResponse(status_code=404)
    with pytest.raises(requests.HTTPError):
        get_trusted_response(
            RecordingSession([response]),
            "https://www.brvm.org/fr/missing",
            allowed_hosts=BRVM_HTML_HOSTS,
        )
    assert response.closed


def test_trusted_request_does_not_allow_tls_verification_to_be_disabled():
    session = RecordingSession([FakeResponse(text="unexpected")])
    with pytest.raises(ValueError, match="TLS certificate verification"):
        get_trusted_response(
            session,
            "https://www.brvm.org/fr/rapport",
            allowed_hosts=BRVM_HTML_HOSTS,
            verify=False,
        )
    assert session.calls == []


def test_trusted_request_respects_session_tls_setting_when_verify_is_none():
    session = RecordingSession([FakeResponse(text="unexpected")])
    session.verify = False
    with pytest.raises(ValueError, match="TLS certificate verification"):
        get_trusted_response(
            session,
            "https://www.brvm.org/fr/rapport",
            allowed_hosts=BRVM_HTML_HOSTS,
            verify=None,
        )
    assert session.calls == []


def test_invalid_pdf_url_is_rejected_before_network_or_cache(tmp_path, monkeypatch):
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    session = RecordingSession([])
    storage.session = session
    report = _report("https://evil.example/report.pdf")
    with pytest.raises(ValueError, match="Unapproved"):
        storage.download(report)
    assert session.calls == []


def test_valid_pdf_is_persisted_atomically_and_cached(tmp_path, monkeypatch):
    from app.ingest.storage import StorageAgent
    from app.ingest.quality import QualityAgent

    payload = _pdf_bytes()
    monkeypatch.chdir(tmp_path)
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    response = FakeResponse(content=payload)
    session = RecordingSession([response])
    storage.session = session
    path = storage.download(_report())

    assert path.read_bytes() == payload
    assert response.closed
    assert not list(path.parent.glob("*.part"))
    assert storage.download(_report()) == path
    assert len(session.calls) == 1
    assert QualityAgent().validate_pdf(path)[0]


def test_explicitly_approved_pdf_host_can_be_downloaded(tmp_path, monkeypatch):
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BRVM_ALLOWED_PDF_HOSTS", "cdn.example.com")
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    response = FakeResponse(content=_pdf_bytes())
    session = RecordingSession([response])
    storage.session = session
    path = storage.download(_report("https://cdn.example.com/report.pdf"))
    assert path.is_file()
    assert session.calls[0][0] == "https://cdn.example.com/report.pdf"


def test_sika_source_uses_separate_richbourse_allowlist(monkeypatch):
    from app.ingest import sika_source

    response = FakeResponse(
        text='data: [[1704067200000,1,2,0.5,1.5]]; data: [[1704067200000,10]];'
    )
    session = RecordingSession([response])
    monkeypatch.setattr(sika_source, "requests", session)
    frame = sika_source.fetch_history_raw("ORAC")

    assert not frame.empty
    assert session.calls[0][0].startswith("https://www.richbourse.com/")
    assert session.calls[0][1]["allow_redirects"] is False
    assert response.closed


def test_sika_redirect_to_untrusted_host_is_rejected(monkeypatch):
    from app.ingest import sika_source

    response = FakeResponse(
        status_code=302,
        headers={"Location": "https://evil.example/market-data"},
    )
    session = RecordingSession([response])
    monkeypatch.setattr(sika_source, "requests", session)
    with pytest.raises(ValueError, match="Unapproved"):
        sika_source.fetch_history_raw("ORAC")
    assert len(session.calls) == 1
    assert response.closed


def _make_supervisor(tmp_path, monkeypatch, reports, *, responses=None, storage=None):
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent
    from app.ingest.supervisor import SupervisorAgent

    monkeypatch.chdir(tmp_path)

    class StaticSource:
        discovery_errors = []

        def discover_reports(self):
            return reports

    storage = storage or StorageAgent(root_dir=str(tmp_path / "raw"))
    if responses is not None:
        storage.session = RecordingSession(responses)
    supervisor = SupervisorAgent(StaticSource(), QualityAgent(), storage)
    return supervisor, storage


def test_three_successive_runs_keep_success_manifest_and_duplicate_run_status(
    tmp_path, monkeypatch
):
    report = _report()
    response = FakeResponse(content=_pdf_bytes())
    supervisor, storage = _make_supervisor(
        tmp_path,
        monkeypatch,
        [report],
        responses=[response],
    )

    first = supervisor.run()
    manifest_path = Path(first["results"][0]["manifest_path"])
    first_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_downloaded_at = first_manifest["downloaded_at"]
    assert (first["success"], first["duplicates"]) == (1, 0)
    assert first_manifest["status"] == "success"

    second = supervisor.run()
    third = supervisor.run()
    assert (second["success"], second["duplicates"]) == (0, 1)
    assert (third["success"], third["duplicates"]) == (0, 1)
    for run in (second, third):
        manifest = json.loads(Path(run["results"][0]["manifest_path"]).read_text())
        assert manifest["status"] == "success"
        assert manifest["downloaded_at"] == first_downloaded_at
        assert manifest["checksum_sha256"] == first_manifest["checksum_sha256"]
        assert manifest["pdf_url"] == report.pdf_url
    assert len(storage.session.calls) == 1


def test_same_pdf_at_two_urls_keeps_provenance_for_both(tmp_path, monkeypatch):
    reports = [
        _report("https://www.brvm.org/files/report-a.pdf"),
        _report("https://www.brvm.org/files/report-b.pdf"),
    ]
    payload = _pdf_bytes()
    supervisor, storage = _make_supervisor(
        tmp_path,
        monkeypatch,
        reports,
        responses=[FakeResponse(content=payload), FakeResponse(content=payload)],
    )
    summary = supervisor.run()

    assert (summary["success"], summary["duplicates"]) == (1, 1)
    manifests = [
        json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        for result in summary["results"]
    ]
    assert manifests[0]["checksum_sha256"] == manifests[1]["checksum_sha256"]
    assert [manifest["status"] for manifest in manifests] == ["success", "success"]
    assert [manifest["pdf_url"] for manifest in manifests] == [
        reports[0].pdf_url,
        reports[1].pdf_url,
    ]
    assert manifests[0]["local_path"] != manifests[1]["local_path"]
    assert len(storage.session.calls) == 2


@pytest.mark.parametrize("legacy_state", ["duplicate", "corrupt_json", "wrong_checksum"])
def test_existing_pdf_with_legacy_or_corrupt_manifest_is_recovered(
    tmp_path, monkeypatch, caplog, legacy_state
):
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    report = _report()
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    path = storage.build_path(report)
    path.write_bytes(_pdf_bytes())
    checksum = QualityAgent().file_hash(path)
    manifest = storage.save_metadata(report, path, checksum, "duplicate")
    if legacy_state == "corrupt_json":
        manifest.write_text("{ broken", encoding="utf-8")
    elif legacy_state == "wrong_checksum":
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["checksum_sha256"] = "0" * 64
        manifest.write_text(json.dumps(payload), encoding="utf-8")

    supervisor, storage = _make_supervisor(
        tmp_path,
        monkeypatch,
        [report],
        storage=storage,
    )
    with caplog.at_level(logging.WARNING):
        summary = supervisor.run()

    assert (summary["success"], summary["duplicates"]) == (1, 0)
    recovered = json.loads(manifest.read_text(encoding="utf-8"))
    assert recovered["status"] == "success"
    assert recovered["checksum_sha256"] == checksum
    assert recovered["pdf_url"] == report.pdf_url
    assert any(
        getattr(record, "event", None) == "ingestion_manifest_rebuilt"
        for record in caplog.records
    )


def test_duplicate_legacy_manifest_is_recovered_while_run_stays_duplicate(
    tmp_path, monkeypatch, caplog
):
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    payload = _pdf_bytes()
    source_report = _report("https://www.brvm.org/files/source.pdf")
    duplicate_report = _report("https://www.brvm.org/files/duplicate.pdf")
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))

    source_path = storage.build_path(source_report)
    source_path.write_bytes(payload)
    checksum = QualityAgent().file_hash(source_path)
    storage.save_metadata(source_report, source_path, checksum, "success")

    duplicate_path = storage.build_path(duplicate_report)
    duplicate_path.write_bytes(payload)
    old_manifest = storage.save_metadata(
        duplicate_report,
        duplicate_path,
        checksum,
        "duplicate",
    )
    supervisor, _ = _make_supervisor(
        tmp_path,
        monkeypatch,
        [duplicate_report],
        storage=storage,
    )

    with caplog.at_level(logging.WARNING):
        result = supervisor.run()
    assert (result["success"], result["duplicates"]) == (0, 1)
    promoted = json.loads(old_manifest.read_text(encoding="utf-8"))
    assert promoted["status"] == "success"
    assert promoted["pdf_url"] == duplicate_report.pdf_url
    assert any(
        getattr(record, "event", None) == "ingestion_manifest_rebuilt"
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "mutation",
    ["status", "path", "checksum", "size"],
)
def test_manifest_validation_rejects_incoherent_fields(tmp_path, mutation, monkeypatch):
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    report = _report()
    path = storage.build_path(report)
    path.write_bytes(_pdf_bytes())
    checksum = QualityAgent().file_hash(path)
    manifest_path = storage.save_metadata(report, path, checksum, "success")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "status":
        payload["status"] = "duplicate"
    elif mutation == "path":
        payload["local_path"] = str(path.parent / "other.pdf")
    elif mutation == "checksum":
        payload["checksum_sha256"] = "f" * 64
    elif mutation == "size":
        payload["file_size_bytes"] += 1
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    assert not storage.has_valid_success_manifest(path, checksum)


def test_manifest_path_comparison_accepts_relative_and_absolute_forms(
    tmp_path, monkeypatch
):
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    storage = StorageAgent(root_dir="raw")
    report = _report()
    path = storage.build_path(report)
    path.write_bytes(_pdf_bytes())
    checksum = QualityAgent().file_hash(path)
    storage.save_metadata(report, path, checksum, "success")
    assert storage.has_valid_success_manifest(path.resolve(), checksum)


def test_storage_path_preserves_valid_brvm_components(tmp_path, monkeypatch):
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    path = storage.build_path(_report_with_path_fields())
    assert path.parent.parts[-4:] == (
        "brvm",
        "orange_ci",
        "2025",
        "annual_report",
    )
    assert path.parent.name == "annual_report"
    assert path.parent.parent.name == "2025"
    assert path.is_relative_to(tmp_path / "raw")


@pytest.mark.parametrize(
    ("year", "document_type", "expected_year", "expected_type"),
    [
        (None, "annual_report", "unknown_year", "annual_report"),
        ("unknown_year", "annual_report", "unknown_year", "annual_report"),
        ("2025", None, "2025", "other_report"),
        (None, None, "unknown_year", "other_report"),
    ],
)
def test_storage_path_uses_safe_defaults(
    tmp_path, monkeypatch, year, document_type, expected_year, expected_type
):
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    path = storage.build_path(
        _report_with_path_fields(year=year, document_type=document_type)
    )
    assert path.parent.parent.name == expected_year
    assert path.parent.name == expected_type
    assert path.is_relative_to(tmp_path / "raw")


@pytest.mark.parametrize(
    "year",
    [
        "../../../../tmp",
        "/tmp/escape",
        r"..\..\..\tmp",
        "2025/../../tmp",
        "2025\\..\\tmp",
        "20\x00 5",
        "2025\n",
    ],
)
def test_storage_rejects_unsafe_year_before_creating_report_directories(
    tmp_path, monkeypatch, year
):
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    root = tmp_path / "raw"
    storage = StorageAgent(root_dir=str(root))
    with pytest.raises(ValueError, match="Invalid report year"):
        storage.build_path(_report_with_path_fields(year=year))
    assert list(root.iterdir()) == []


@pytest.mark.parametrize(
    "document_type",
    [
        "../../../private",
        "..",
        ".",
        r"..\private",
        "annual/report",
        "annual\\report",
        "annual_report\x00",
        "annual_report\n",
    ],
)
def test_storage_rejects_unsafe_document_type_before_creating_report_directories(
    tmp_path, monkeypatch, document_type
):
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    root = tmp_path / "raw"
    storage = StorageAgent(root_dir=str(root))
    with pytest.raises(ValueError, match="Invalid report document type"):
        storage.build_path(
            _report_with_path_fields(document_type=document_type)
        )
    assert list(root.iterdir()) == []


@pytest.mark.parametrize(
    "symlink_parts",
    [
        ("brvm",),
        ("brvm", "orange_ci"),
        ("brvm", "orange_ci", "2025"),
        ("brvm", "orange_ci", "2025", "annual_report"),
    ],
)
def test_storage_rejects_existing_symlink_escape(
    tmp_path, monkeypatch, symlink_parts
):
    from app.ingest.storage import StorageAgent

    monkeypatch.chdir(tmp_path)
    root = tmp_path / "raw"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link_path = root.joinpath(*symlink_parts)
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(outside, target_is_directory=True)
    storage = StorageAgent(root_dir=str(root))

    with pytest.raises(ValueError, match="escapes its configured root"):
        storage.build_path(_report_with_path_fields())

    assert list(outside.iterdir()) == []


def test_ingestion_health_distinguishes_success_duplicate_invalid_and_errors():
    from app.ingest.ingestion_health import IngestionHealthMonitor

    report = IngestionHealthMonitor().analyze_ingestion_run(
        [
            {"status": "success"},
            {"status": "duplicate"},
            {"status": "invalid_pdf"},
            {"status": "error", "stage": "download"},
            {"status": "error", "stage": "discovery"},
        ]
    )
    metrics = report["metrics"]
    assert metrics["successful"] == 1
    assert metrics["duplicates_detected"] == 1
    assert metrics["invalid_pdfs"] == 1
    assert metrics["errors"] == 2
    assert report["overall_status"] == "CRITICAL"


@pytest.mark.parametrize("deny_redirect", [False, True])
def test_offline_html_discovery_download_validation_manifest_and_dedup(
    tmp_path, monkeypatch, deny_redirect
):
    from app.ingest import brvm_source
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent
    from app.ingest.supervisor import SupervisorAgent

    monkeypatch.chdir(tmp_path)
    listing_url = "https://www.brvm.org/fr/type-document/rapports-annuels"
    page_url = "https://www.brvm.org/fr/rapport-annuel"
    pdf_url = "https://www.brvm.org/files/report.pdf"
    monkeypatch.setattr(brvm_source, "BRVM_LISTING_PAGES", [listing_url])
    universe = tmp_path / "universe.yaml"
    universe.write_text("companies: []\n", encoding="utf-8")
    source = brvm_source.BRVMSourceAgent(
        companies=[],
        max_pages=1,
        sleep_seconds=0,
        universe_path=str(universe),
    )
    source.get_company_report_pages = lambda: []
    html_responses = {
        listing_url: FakeResponse(
            text='<a href="/fr/rapport-annuel">Rapport annuel</a>'
        ),
        page_url: FakeResponse(
            text=(
                "<h1>Rapport annuel exercice 2025</h1>"
                '<a href="/files/report.pdf">Télécharger le PDF</a>'
            )
        ),
    }
    source_session = RecordingSession(
        [
            html_responses[listing_url],
            html_responses[page_url],
            FakeResponse(text='<a href="/fr/rapport-annuel">Rapport annuel</a>'),
            FakeResponse(
                text=(
                    "<h1>Rapport annuel exercice 2025</h1>"
                    '<a href="/files/report.pdf">Télécharger le PDF</a>'
                )
            ),
        ]
    )
    source.session = source_session

    storage = StorageAgent(root_dir=str(tmp_path / "raw"))
    if deny_redirect:
        storage_response = FakeResponse(
            status_code=302,
            headers={"Location": "https://evil.example/report.pdf"},
        )
    else:
        storage_response = FakeResponse(content=_pdf_bytes())
    storage_session = RecordingSession([storage_response])
    storage.session = storage_session
    supervisor = SupervisorAgent(source, QualityAgent(), storage)

    first = supervisor.run()
    if deny_redirect:
        assert (first["success"], first["errors"]) == (0, 1)
        assert len(storage_session.calls) == 1
        assert storage_response.closed
        assert not list((tmp_path / "raw").rglob("*.pdf"))
        assert not list((tmp_path / "raw").rglob("*.part"))
        return

    assert (first["success"], first["duplicates"]) == (1, 0)
    assert [url for url, _ in source_session.calls] == [listing_url, page_url]
    assert all(kwargs["allow_redirects"] is False for _, kwargs in source_session.calls)
    assert all(response.closed for response in html_responses.values())
    result = first["results"][0]
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "success"
    assert manifest["pdf_url"] == pdf_url
    valid, _, _ = QualityAgent().validate_pdf(result["local_path"])
    assert valid

    second = supervisor.run()
    assert (second["success"], second["duplicates"]) == (0, 1)
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "success"
