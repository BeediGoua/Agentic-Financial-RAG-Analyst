"""G1 acceptance tests. Offline, synthetic; meant to FAIL on unfixed main.

Copy to tests/test_g1_contracts.py in Codespaces. No BRVM network calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz
import pytest

from app.ingest.quality import QualityAgent
from app.extraction.extraction_quality_agent import ExtractionQualityAgent
from app.extraction.pdf_text_agent import PDFTextExtractionAgent


def _pdf(path: Path, *, text: str = "Orange CI résultat net 2025", pages: int = 1) -> Path:
    d = fitz.open()
    for _ in range(pages):
        page = d.new_page()
        page.insert_text((50, 50), text)
    d.save(path)
    d.close()
    return path


def test_g1_valid_pdf_is_accepted(tmp_path):
    p = _pdf(tmp_path / 'valid.pdf')
    valid, reason, checks = QualityAgent(min_pdf_size=100).validate_pdf(p)
    assert valid, (reason, checks)


def test_g1_reject_pdf_header_with_corrupt_body(tmp_path):
    p = tmp_path / 'fake.pdf'
    p.write_bytes(b'%PDF-1.7\n' + b'NOT_A_VALID_PDF' * 200)
    valid, reason, checks = QualityAgent(min_pdf_size=100).validate_pdf(p)
    assert not valid, (reason, checks)


def test_g1_reject_encrypted_unreadable_pdf(tmp_path):
    p = tmp_path / 'protected.pdf'
    doc = fitz.open()
    doc.new_page()
    doc.save(p, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='secret')
    doc.close()
    valid, reason, _ = QualityAgent(min_pdf_size=100).validate_pdf(p)
    assert not valid, reason


def test_g1_reject_zero_page_pdf(tmp_path):
    # A 0-page doc is often rejected by PyMuPDF at creation. This is a malformed PDF specimen.
    p = tmp_path / 'empty.pdf'
    p.write_bytes(b'%PDF-1.5\n' + b'x' * 400)
    valid, _, _ = QualityAgent(min_pdf_size=100).validate_pdf(p)
    assert not valid


def test_g1_extraction_text_empty_is_not_healthy():
    result = ExtractionQualityAgent().evaluate_text_results([])
    assert result['status'] in {'UNHEALTHY', 'FAIL', 'EMPTY'}


def test_g1_extraction_cached_unknown_page_count_not_healthy():
    result = ExtractionQualityAgent().evaluate_text_results([
        {'status': 'already_exists', 'pages_output': '/nonexistent/pages.jsonl'}
    ])
    assert result['status'] in {'UNHEALTHY', 'FAIL', 'EMPTY'}


def test_g1_extraction_errors_cannot_be_healthy():
    result = ExtractionQualityAgent().evaluate_text_results([
        {'status': 'error', 'error': 'unexpected parser failure'}
    ])
    assert result['status'] in {'UNHEALTHY', 'DEGRADED', 'FAIL'}


def test_g1_extraction_table_empty_batch_is_not_healthy():
    result = ExtractionQualityAgent().evaluate_table_results([])
    assert result['status'] in {'UNHEALTHY', 'FAIL', 'EMPTY'}


def test_g1_extraction_tables_zero_count_is_legitimate():
    result = ExtractionQualityAgent().evaluate_table_results([
        {'status': 'success', 'tables_count': 0}
    ])
    assert result['status'] == 'HEALTHY'


def test_g1_ingestion_failure_must_propagate_exit(monkeypatch):
    from app.ingest import run_all
    monkeypatch.setattr(sys, 'argv', ['run_all', '--only-brvm'])
    def fail():
        raise RuntimeError('BRVM download failed')
    monkeypatch.setattr(run_all, 'run_brvm_reports', fail)
    with pytest.raises((RuntimeError, SystemExit)):
        run_all.main()


def test_g1_sika_failure_must_propagate_exit(monkeypatch):
    from app.ingest import run_all
    monkeypatch.setattr(sys, 'argv', ['run_all', '--only-sika'])
    def fail(*args, **kwargs):
        raise ConnectionError('certificate verify failed')
    monkeypatch.setattr(run_all, 'run_sika', fail)
    with pytest.raises((RuntimeError, SystemExit)):
        run_all.main()


def test_g1_macro_failure_must_propagate_exit(monkeypatch):
    from app.ingest import run_all
    monkeypatch.setattr(sys, 'argv', ['run_all', '--only-macro'])
    def fail(*args, **kwargs):
        raise FileNotFoundError('missing EDEN sources')
    monkeypatch.setattr(run_all, 'run_macro', fail)
    with pytest.raises((RuntimeError, SystemExit)):
        run_all.main()


def test_g1_corrupt_pdf_extraction_must_not_create_cache_file(tmp_path):
    raw = tmp_path / 'raw'
    out = tmp_path / 'out'
    raw.mkdir()
    pdf = raw / 'broken.pdf'
    pdf.write_bytes(b'%PDF-1.4\nnot actually a pdf\n' * 20)
    agent = PDFTextExtractionAgent(raw_dir=str(raw), output_dir=str(out), enable_ocr=False)
    result = agent.extract_pdf(pdf)
    assert result['status'] == 'error'
    assert not agent.build_output_path(pdf).exists(), 'Failed extraction wrote a cache file'


def test_g1_zero_length_cached_pages_are_not_accepted(tmp_path):
    raw, out = tmp_path / 'raw', tmp_path / 'out'
    raw.mkdir()
    pdf = _pdf(raw / 'working.pdf', text='Société BRVM 2025 performances de résultat net')
    agent = PDFTextExtractionAgent(raw_dir=str(raw), output_dir=str(out), enable_ocr=False)
    fake_cache = agent.build_output_path(pdf)
    fake_cache.write_text('', encoding='utf-8')
    result = agent.extract_pdf(pdf)
    assert result['status'] == 'success' or result['status'] == 'error', result
    assert result['status'] != 'already_exists'


def test_g1_force_extraction_failure_preserves_existing_good_output(tmp_path, monkeypatch):
    raw, out = tmp_path / 'raw', tmp_path / 'out'
    raw.mkdir()
    pdf = _pdf(raw / 'working.pdf')
    agent = PDFTextExtractionAgent(raw_dir=str(raw), output_dir=str(out), enable_ocr=False)
    good = agent.extract_pdf(pdf)
    assert good['status'] == 'success'
    path = agent.build_output_path(pdf)
    before = path.read_bytes()
    def crash(*args, **kwargs):
        raise RuntimeError('simulated crash after file opened')
    monkeypatch.setattr(agent, 'extract_page_text', crash)
    result = agent.extract_pdf(pdf, force=True)
    assert result['status'] == 'error'
    assert path.read_bytes() == before, 'Failed retry destroyed previous valid output'


def test_g1_no_disabled_tls_in_known_sources():
    project = Path(__file__).resolve().parents[1]
    source_paths = [
        'app/ingest/brvm_source.py',
        'app/ingest/storage.py',
        'app/ingest/sika_source.py',
    ]
    for rel in source_paths:
        path = project / rel
        assert path.is_file(), f'missing source: {rel}'
        source = path.read_text(encoding='utf-8')
        assert 'verify=False' not in source, f'TLS off in {rel}'
        assert 'session.verify = False' not in source, f'TLS off in {rel}'
        assert 'disable_warnings(' not in source, f'TLS warning suppressed in {rel}'


def test_g1_year_filter_accepts_list_and_range():
    from app.ingest.utils import parse_year_filter
    assert parse_year_filter(['2024', '2025']) == ['2024', '2025']
    assert parse_year_filter('2023-2025') == ['2023', '2024', '2025']


def test_g1_ingestion_no_results_is_not_healthy():
    from app.ingest.ingestion_health import IngestionHealthMonitor
    result = IngestionHealthMonitor().analyze_ingestion_run([])
    assert result['overall_status'] != 'HEALTHY'


def test_g1_ingestion_invalid_pdf_is_not_healthy():
    from app.ingest.ingestion_health import IngestionHealthMonitor
    result = IngestionHealthMonitor().analyze_ingestion_run([
        {'status': 'success'}, {'status': 'invalid_pdf', 'reason': 'truncated'}
    ])
    assert result['overall_status'] != 'HEALTHY'


def test_g1_brvm_discovery_errors_are_retained(monkeypatch, tmp_path):
    from app.ingest import brvm_source

    universe = tmp_path / 'universe.yaml'
    universe.write_text('companies: []\n', encoding='utf-8')
    monkeypatch.setattr(
        brvm_source,
        'BRVM_LISTING_PAGES',
        ['https://www.brvm.org/fr/type-document/rapports-annuels'],
    )
    agent = brvm_source.BRVMSourceAgent(
        companies=[],
        max_pages=1,
        sleep_seconds=0,
        universe_path=str(universe),
    )

    def fail(_url):
        raise ConnectionError('certificate verify failed')

    monkeypatch.setattr(agent, 'get_html', fail)
    assert agent.discover_reports() == []
    assert len(agent.discovery_errors) == 1
    assert 'certificate verify failed' in agent.discovery_errors[0]


def test_g1_macro_empty_observations_are_not_success(tmp_path):
    from app.ingest.macro_source import parse_eden_csv_fake_xls

    source = tmp_path / 'eden-empty.xls'
    source.write_text(
        'metadata\n' * 5 + 'CODE;LIBELLE;2025-01\n1;Rate;-\n',
        encoding='utf-8',
    )
    with pytest.raises(RuntimeError, match='No usable observations'):
        parse_eden_csv_fake_xls(str(source), 'taux_directeur')


def test_g1_ingestion_only_duplicates_is_not_new_success():
    from app.ingest.ingestion_health import IngestionHealthMonitor
    result = IngestionHealthMonitor().analyze_ingestion_run([
        {'status': 'duplicate'}
    ])
    assert result['metrics']['successful'] == 0
    assert result['metrics']['duplicates_detected'] == 1


def test_g1_extraction_supervisor_propagates_unhealthy_tables(tmp_path):
    from app.extraction.extraction_supervisor import ExtractionSupervisorAgent
    from app.extraction.extraction_quality_agent import ExtractionQualityAgent
    class FakeAgent:
        def __init__(self, results): self.results = results
        def run(self, **kw): return self.results
    sup = ExtractionSupervisorAgent(
        text_agent=FakeAgent([{'status':'success','pages_count':2,'empty_pages':0,'low_quality_pages':0}]),
        table_agent=FakeAgent([]),
        quality_agent=ExtractionQualityAgent(),
        quality_dir=str(tmp_path),
    )
    r = sup.run()
    assert r['overall_status'] != 'HEALTHY'


def test_g1_sika_ticker_errors_are_reported_after_all_tickers(monkeypatch, tmp_path):
    from app.ingest import sika_source
    import pandas as pd

    fake_module = tmp_path / 'workspace' / 'app' / 'ingest' / 'sika_source.py'
    fake_module.parent.mkdir(parents=True)
    monkeypatch.setattr(sika_source, '__file__', str(fake_module))
    monkeypatch.setattr(sika_source, 'load_config', lambda _: {'sika': {'rps': 100}})
    monkeypatch.setattr(
        sika_source,
        'extract_tickers_from_universe',
        lambda _: ['FAIL', 'GOOD'],
    )

    def fetch(ticker):
        if ticker == 'FAIL':
            raise ConnectionError('TLS verification failed')
        return pd.DataFrame([{
            'date': '2025-01-01',
            'open': 1.0,
            'high': 2.0,
            'low': 0.5,
            'close': 1.5,
            'volume': 10,
            'symbol': ticker,
        }])

    monkeypatch.setattr(sika_source, 'fetch_history_raw', fetch)
    with pytest.raises(RuntimeError, match='FAIL'):
        sika_source.run_ingestion(force=True)

    assert (tmp_path / 'workspace' / 'data' / 'raw' / 'sika_csv' / 'GOOD_raw.csv').is_file()
