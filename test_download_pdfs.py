from __future__ import annotations

import sys
import tempfile
from unittest import mock
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "openreview_local_index"))

import download_pdfs as app


class DownloadPdfsTests(unittest.TestCase):
    def test_http_bytes_retries_incomplete_read(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"%PDF-1.4"

        partial_exc = app.http.client.IncompleteRead(b"partial", 10)
        with mock.patch.object(app.urllib.request, "urlopen", side_effect=[partial_exc, FakeResponse()]):
            data = app._http_bytes("https://example.com/test.pdf", timeout=5, retries=2)
        self.assertEqual(data, b"%PDF-1.4")

    def test_make_pdf_filename_uses_title_year_venue_and_note_id(self) -> None:
        record = {
            "title": "Bonsai: Gradient-free Graph Condensation for Node Classification",
            "year": 2025,
            "venue": "ICLR",
            "note_id": "5x88lQ2MsH",
        }
        filename = app.make_pdf_filename(record)
        self.assertEqual(
            filename,
            "Bonsai_ Gradient-free Graph Condensation for Node Classification__2025__ICLR__5x88lQ2MsH.pdf",
        )

    def test_load_result_records_reads_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "results.jsonl"
            path.write_text(
                '{"title":"A","year":2025,"venue":"ICLR","note_id":"n1","pdf_url":"https://openreview.net/pdf?id=n1"}\n',
                encoding="utf-8",
            )
            records = app.load_result_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["note_id"], "n1")

    def test_load_result_records_reads_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "results.csv"
            path.write_text(
                "title,year,venue,note_id,pdf_url\nA,2025,ICLR,n1,https://openreview.net/pdf?id=n1\n",
                encoding="utf-8",
            )
            records = app.load_result_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["venue"], "ICLR")


if __name__ == "__main__":
    unittest.main()
