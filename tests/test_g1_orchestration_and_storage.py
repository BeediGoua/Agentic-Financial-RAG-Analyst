"""G1 integration contracts. Never call real network or real BRVM.

These tests target the *live repository* in Codespaces, not the partial local
reconstruction that was used to prototype the four P0 fixes.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import fitz
import pytest

from app.ingest.schemas import ReportDocument


def _report() -> ReportDocument:
    return ReportDocument(
        title='Orange CI — rapport annuel 2025',
        page_url='https://www.brvm.org/fr/example',
        pdf_url='https://www.brvm.org/sites/default/files/orange_ci_2025.pdf',
        company='ORANGE CI', year='2025', document_type='annual_report'
    )


def _good_pdf_bytes() -> bytes:
    with fitz.open() as doc:
        page = doc.new_page()
        for i in range(8):
            page.insert_text((50, 50 + 16*i), f'Orange CI financial report 2025 line {i}')
        return doc.tobytes()


class FakeResponse:
    def __init__(self, content: bytes, content_type: str='application/pdf', fail_mid_stream: bool=False):
        self.content = content
        self.headers = {'Content-Type':content_type}
        self.fail_mid_stream = fail_mid_stream

    def raise_for_status(self): return None
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def iter_content(self, chunk_size=8192):
        if self.fail_mid_stream:
            yield self.content[:150]
            raise ConnectionError('simulated network interruption')
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index:index+chunk_size]


def test_g1_download_validates_content_not_url_extension(tmp_path, monkeypatch):
    from app.ingest.storage import StorageAgent
    storage = StorageAgent(root_dir=str(tmp_path / 'raw'))
    monkeypatch.setattr(storage.session, 'get', lambda *a, **kw: FakeResponse(b'<html>LOGIN REQUIRED</html>'*150, 'application/pdf'))
    report = _report()
    with pytest.raises(Exception):
        storage.download(report)
    path = storage.build_path(report)
    assert not path.exists(), 'Invalid downloaded HTML was persisted as a PDF'


def test_g1_cached_invalid_pdf_must_not_be_reused(tmp_path, monkeypatch):
    from app.ingest.storage import StorageAgent
    storage = StorageAgent(root_dir=str(tmp_path / 'raw'))
    report = _report()
    path = storage.build_path(report)
    path.write_bytes(b'%PDF-1.7\n' + b'BROKEN'*300)
    payload = _good_pdf_bytes()
    calls=[]
    def get(*a,**kwargs):
        calls.append(kwargs)
        return FakeResponse(payload)
    monkeypatch.setattr(storage.session, 'get', get)
    result = storage.download(report)
    assert calls, 'Existing invalid cache bypassed revalidation'
    assert result == path
    with fitz.open(path) as pdf:
        assert pdf.page_count == 1


def test_g1_download_interruption_leaves_no_partial_pdf(tmp_path, monkeypatch):
    from app.ingest.storage import StorageAgent
    storage = StorageAgent(root_dir=str(tmp_path / 'raw'))
    report = _report()
    payload=_good_pdf_bytes()
    monkeypatch.setattr(storage.session, 'get', lambda *a,**kw: FakeResponse(payload, fail_mid_stream=True))
    with pytest.raises(Exception):
        storage.download(report)
    final = storage.build_path(report)
    assert not final.exists()
    assert not list(final.parent.glob('*.part'))
    assert not list(final.parent.glob('*.tmp'))


def test_g1_storage_tls_is_on_by_default(tmp_path):
    from app.ingest.storage import StorageAgent
    storage=StorageAgent(root_dir=str(tmp_path / 'raw'))
    assert storage.session.verify is not False


def test_g1_brvm_source_tls_is_on_by_default(tmp_path):
    from app.ingest.brvm_source import BRVMSourceAgent
    universe = tmp_path / 'universe.yaml'
    universe.write_text('companies: []\n', encoding='utf-8')
    agent=BRVMSourceAgent(universe_path=str(universe), sleep_seconds=0)
    assert agent.session.verify is not False


def test_g1_sika_request_does_not_disable_tls(monkeypatch):
    from app.ingest import sika_source
    observed=[]
    def get(url, **kwargs):
        observed.append(kwargs)
        raise RuntimeError('intentional test stop')
    monkeypatch.setattr(sika_source.requests, 'get', get)
    with pytest.raises(RuntimeError, match='intentional'):
        sika_source.fetch_history_raw('ORAC')
    assert len(observed) == 1
    assert observed[0].get('verify', True) is not False


def test_g1_run_reports_cli_nonzero_on_failed_ingestion(monkeypatch,tmp_path):
    from app.ingest import run_reports
    monkeypatch.setattr(sys,'argv', ['run_reports', '--root-dir', str(tmp_path)])
    monkeypatch.setattr(run_reports.SupervisorAgent, 'run', lambda self,limit=None: {
        'discovered_reports': 1, 'processed_reports':1, 'success':0,
        'duplicates':0, 'invalid_pdfs':0, 'errors':1, 'success_rate':0,
        'overall_status':'CRITICAL','log_path':'run.json','health_report_path':'health.json',
        'results':[{'status':'error','error':'tls failed'}]
    })
    with pytest.raises(SystemExit) as exc:
        run_reports.main()
    assert exc.value.code not in (None,0)


def test_g1_run_reports_cli_nonzero_on_empty_discovery(monkeypatch,tmp_path):
    from app.ingest import run_reports
    monkeypatch.setattr(sys,'argv', ['run_reports', '--root-dir', str(tmp_path)])
    monkeypatch.setattr(run_reports.SupervisorAgent, 'run', lambda self,limit=None: {
        'discovered_reports':0, 'processed_reports':0, 'success':0,
        'duplicates':0, 'invalid_pdfs':0, 'errors':0, 'success_rate':0,
        'overall_status':'EMPTY','log_path':'run.json','health_report_path':'health.json',
        'results':[]
    })
    with pytest.raises(SystemExit) as exc:
        run_reports.main()
    assert exc.value.code not in (None,0)


def test_g1_run_reports_allows_only_explicit_empty_discovery(monkeypatch, tmp_path):
    from app.ingest import run_reports

    monkeypatch.setattr(
        sys,
        'argv',
        ['run_reports', '--root-dir', str(tmp_path), '--allow-empty'],
    )
    monkeypatch.setattr(
        run_reports.SupervisorAgent,
        'run',
        lambda self, limit=None: {
            'discovered_reports': 0,
            'processed_reports': 0,
            'success': 0,
            'duplicates': 0,
            'invalid_pdfs': 0,
            'errors': 0,
            'success_rate': 0,
            'overall_status': 'CRITICAL',
            'log_path': 'run.json',
            'health_report_path': 'health.json',
            'results': [],
        },
    )
    run_reports.main()


def test_g1_extraction_cli_nonzero_on_failure(monkeypatch):
    from app.extraction import run_extraction
    monkeypatch.setattr(sys,'argv',['run_extraction','--disable-ocr'])
    monkeypatch.setattr(run_extraction.ExtractionSupervisorAgent,'run',lambda self, **kw: {
        'overall_status':'UNHEALTHY',
        'text_quality':{'status':'UNHEALTHY','success_files':0,'total_pages':0,'empty_pages':0,'ocr_pages':0,'low_quality_pages':0,'empty_page_rate':0,'ocr_rate':0},
        'table_quality':{'status':'UNHEALTHY','success_files':0,'total_tables':0},
        'quality_report_path':'none.json'
    })
    with pytest.raises(SystemExit) as exc:
        run_extraction.main()
    assert exc.value.code not in (None,0)


def test_g1_extraction_audit_cli_nonzero_on_failure(monkeypatch):
    from app.extraction import extraction_audit
    monkeypatch.setattr(sys,'argv',['extraction_audit'])
    monkeypatch.setattr(extraction_audit.ExtractionAuditAgent,'run',lambda self,**kw:{
        'overall_status':'FAIL','companies':'all','years':'all','audit_path':'none.json',
        'pages_audit':{'documents_count':0,'total_pages':0,'empty_pages':0,'low_quality_pages':0,'ocr_pages':0,'empty_rate':0,'low_quality_rate':0},
        'tables_audit':{'documents_count':0,'total_tables':0,'avg_rows':0,'avg_columns':0}
    })
    with pytest.raises(SystemExit) as exc:
        extraction_audit.main()
    assert exc.value.code not in (None,0)


def test_g1_macro_ingestion_missing_required_inputs_raises(monkeypatch,tmp_path):
    from app.ingest import macro_source
    # Run code from a copied module to avoid changing the actual repository data dirs.
    from types import SimpleNamespace
    fake_module_path = tmp_path / 'a' / 'b' / 'macro_source.py'
    fake_module_path.parent.mkdir(parents=True)
    fake_module_path.write_text('# test dummy\n')
    monkeypatch.setattr(macro_source, '__file__', str(fake_module_path))
    with pytest.raises(FileNotFoundError):
        macro_source.run_macro_ingestion()


def test_g1_table_extraction_failure_preserves_previous_output(tmp_path, monkeypatch):
    from app.extraction.table_extraction_agent import TableExtractionAgent
    raw=tmp_path/'raw';raw.mkdir()
    output=tmp_path/'tables'
    pdf=raw/'one.pdf'
    pdf.write_bytes(_good_pdf_bytes())
    agent=TableExtractionAgent(raw_dir=str(raw),output_dir=str(output))
    result=agent.extract_tables(pdf)
    assert result['status']=='success'
    path=agent.build_output_path(pdf)
    # A previously committed table result must survive a failed forced retry.
    path.write_text(json.dumps({
        'source_pdf': str(pdf), 'page_number': 1, 'table_index': 0,
        'rows': [['Item', 'Value'], ['Profit', '100']],
        'row_count': 2, 'column_count': 2,
    }) + '\n', encoding='utf-8')
    existing=path.read_bytes()

    class ExplodingPage:
        def extract_tables(self): raise RuntimeError('simulated table parser crash')
    class ExplodingDocument:
        pages=[ExplodingPage()]
        def __enter__(self): return self
        def __exit__(self,*args): return False
    import app.extraction.table_extraction_agent as table_module
    monkeypatch.setattr(table_module.pdfplumber,'open',lambda *args,**kwargs: ExplodingDocument())
    retry=agent.extract_tables(pdf,force=True)
    assert retry['status']=='error'
    assert path.read_bytes()==existing, 'A failed forced re-extraction must not destroy old data'


def test_g1_table_extraction_not_accept_missing_or_stale_cached_file(tmp_path):
    from app.extraction.table_extraction_agent import TableExtractionAgent
    raw=tmp_path/'raw';raw.mkdir()
    output=tmp_path/'tables'
    pdf=raw/'one.pdf'
    pdf.write_bytes(_good_pdf_bytes())
    agent=TableExtractionAgent(raw_dir=str(raw),output_dir=str(output))
    path=agent.build_output_path(pdf)
    path.write_text('not jsonl',encoding='utf-8')
    outcome=agent.extract_tables(pdf)
    assert outcome['status'] in {'success','error'}, outcome
    assert outcome['status']!='already_exists'


@pytest.mark.parametrize(
    ('failed_phase', 'start_from', 'expected_phases'),
    [
        ('ingestion', 'ingestion', ['ingestion']),
        ('extraction', 'extraction', ['extraction']),
    ],
)
def test_g1_pipeline_stops_after_ingestion_or_extraction_failure(
    tmp_path, monkeypatch, failed_phase, start_from, expected_phases
):
    from app.pipeline.run_data_pipeline import DataPipelineRunner

    runner = DataPipelineRunner(reports_dir=str(tmp_path))
    calls = []

    def make_phase(name):
        def phase():
            calls.append(name)
            return {'phase': name, 'status': 'error' if name == failed_phase else 'success'}
        return phase

    runner.phase_ingestion = make_phase('ingestion')
    runner.phase_extraction = make_phase('extraction')
    runner.phase_extraction_audit = make_phase('audit')
    runner.phase_processing = make_phase('processing')

    report = runner.run(start_from=start_from, stop_after='processing')
    assert calls == expected_phases
    assert report['overall_status'] == 'error'


def test_g1_success_manifest_requires_valid_pdf_and_exact_hash(tmp_path):
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent

    storage = StorageAgent(root_dir=str(tmp_path / 'raw'))
    report = _report()
    pdf_path = storage.build_path(report)
    pdf_path.write_bytes(_good_pdf_bytes())
    checksum = QualityAgent().file_hash(pdf_path)

    manifest_path = storage.save_metadata(report, pdf_path, checksum, 'success')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert manifest['checksum_sha256'] == checksum
    assert manifest['local_path'] == str(pdf_path)
    assert checksum in storage.load_existing_checksums()

    with pytest.raises(ValueError, match='checksum'):
        storage.save_metadata(report, pdf_path, '0' * 64, 'success')

    manifest['checksum_sha256'] = '0' * 64
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    assert checksum not in storage.load_existing_checksums()


def test_g1_synthetic_pdf_download_and_extraction_preserve_metadata(
    tmp_path, monkeypatch
):
    from app.extraction.pdf_text_agent import PDFTextExtractionAgent
    from app.ingest.quality import QualityAgent
    from app.ingest.storage import StorageAgent

    storage = StorageAgent(root_dir=str(tmp_path / 'raw'))
    report = _report()
    monkeypatch.setattr(
        storage.session,
        'get',
        lambda *args, **kwargs: FakeResponse(_good_pdf_bytes()),
    )
    pdf_path = storage.download(report)
    checksum = QualityAgent().file_hash(pdf_path)
    storage.save_metadata(report, pdf_path, checksum, 'success')

    extractor = PDFTextExtractionAgent(
        raw_dir=str(tmp_path / 'raw'),
        output_dir=str(tmp_path / 'pages'),
        enable_ocr=False,
    )
    result = extractor.extract_pdf(pdf_path)
    rows = [
        json.loads(line)
        for line in Path(result['pages_output']).read_text(encoding='utf-8').splitlines()
    ]

    assert result['status'] == 'success'
    assert result['pages_count'] == 1
    assert rows[0]['company'] == 'ORANGE CI'
    assert rows[0]['year'] == '2025'
    assert rows[0]['source_pdf'] == str(pdf_path)


def test_g1_macro_cli_fails_in_an_isolated_project_copy(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    shutil.copytree(
        project_root / 'app',
        tmp_path / 'app',
        ignore=shutil.ignore_patterns('__pycache__'),
    )
    env = os.environ.copy()
    env['PYTHONPATH'] = str(tmp_path)
    if env.get('PYTHONPATH'):
        env['PYTHONPATH'] += os.pathsep + str(project_root)

    completed = subprocess.run(
        [sys.executable, '-m', 'app.ingest.run_all', '--only-macro'],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert 'Required EDEN macro inputs missing' in completed.stderr
    assert not (tmp_path / 'data' / 'bronze').exists()
