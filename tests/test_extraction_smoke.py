"""Synthetic PDF test: verifies extraction + manifest without downloading files."""
import json
from pathlib import Path
import tempfile

import fitz
from app.extraction.pdf_text_agent import PDFTextExtractionAgent


def test_pdf_text_extraction_preserves_page_and_manifest():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        raw = root / 'raw'
        output = root / 'output'
        raw.mkdir()
        pdf = raw / 'orange_2025.pdf'
        document = fitz.open()
        page = document.new_page()
        text = 'Orange CI 2025 chiffre affaires et resultat net. ' * 15
        page.insert_text((30, 80), text[:92])
        document.save(str(pdf))
        document.close()
        pdf.with_suffix('.manifest.json').write_text(json.dumps({
            'source_url': 'https://example.org/orange_2025.pdf',
            'company': 'ORANGE CI',
            'year': '2025',
            'document_type': 'financial_statements',
        }))
        agent = PDFTextExtractionAgent(raw_dir=str(raw), output_dir=str(output), enable_ocr=False)
        result = agent.extract_pdf(pdf)
        assert result['status'] == 'success', result
        assert result['pages_count'] == 1
        rows = [json.loads(line) for line in Path(result['pages_output']).read_text().splitlines()]
        assert rows[0]['company'] == 'ORANGE CI'
        assert rows[0]['year'] == '2025'
        assert rows[0]['page_number'] == 1
        assert 'Orange CI' in rows[0]['text']
