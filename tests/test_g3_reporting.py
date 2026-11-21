import csv
import json

from app.evaluation.reporting import write_csv_atomic, write_json_atomic, write_markdown


def test_atomic_report_formats_and_unique_runs(tmp_path):
    first = tmp_path / "summary.json"
    payload = {"run_id": "a", "synthetic": True}
    write_json_atomic(first, payload)
    write_json_atomic(first, {"run_id": "b", "synthetic": True})
    assert json.loads(first.read_text())["run_id"] == "b"

    csv_path = tmp_path / "rows.csv"
    write_csv_atomic(csv_path, [{"configuration_id": "bm25", "hit": 1.0}])
    with csv_path.open() as stream:
        assert list(csv.DictReader(stream))[0]["configuration_id"] == "bm25"

    markdown = tmp_path / "report.md"
    write_markdown(markdown, payload)
    text = markdown.read_text()
    assert "synthetic" in text.lower()
    assert "not representative" in text
