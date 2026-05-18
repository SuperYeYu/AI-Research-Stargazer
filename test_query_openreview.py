from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "openreview_local_index"))

import query_openreview as app


SAMPLE_NOTE = {
    "id": "note-1",
    "content": {
        "title": {"value": "Graph Condensation with Transport Matching"},
        "abstract": {"value": "We study graph condensation for efficient graph learning."},
        "keywords": {"value": ["graph condensation", "graph learning"]},
    },
}


class QueryOpenReviewTests(unittest.TestCase):
    def test_default_years_are_last_five_complete_years(self) -> None:
        current_year = datetime.now(timezone.utc).year
        self.assertEqual(app.DEFAULT_YEARS, tuple(range(current_year - 5, current_year)))

    def test_parse_queries_json_list(self) -> None:
        queries = app.parse_queries_arg('["graph condensation", "graph distillation"]')
        self.assertEqual(queries, ["graph condensation", "graph distillation"])

    def test_parse_queries_json_list_single_query(self) -> None:
        queries = app.parse_queries_arg('["graph condensation"]')
        self.assertEqual(queries, ["graph condensation"])

    def test_build_targets_contains_expected_ids(self) -> None:
        targets = app.build_targets([2023, 2024, 2025])
        ids = {target.venue_id for target in targets}

        self.assertIn("ICLR.cc/2025/Conference", ids)
        self.assertIn("thecvf.com/ICCV/2025/Conference", ids)
        self.assertNotIn("PAKDD.org/2025/Conference", ids)

    def test_build_targets_default_range_includes_2021_and_2022_entries(self) -> None:
        targets = app.build_targets(app.DEFAULT_YEARS)
        ids = {target.venue_id for target in targets}

        self.assertIn("ICLR.cc/2021/Conference", ids)
        self.assertIn("NeurIPS.cc/2022/Conference", ids)
        self.assertIn("thecvf.com/ECCV/2022/Conference", ids)

    def test_note_matches_queries_reports_fields(self) -> None:
        matched_queries, matched_fields = app.note_matches_queries(
            SAMPLE_NOTE,
            ["graph condensation", "diffusion model"],
        )

        self.assertEqual(matched_queries, ["graph condensation"])
        self.assertEqual(set(matched_fields), {"title", "abstract", "keywords"})

    def test_export_records_writes_jsonl_and_csv(self) -> None:
        record = {
            "query": "graph condensation",
            "title": "Graph Condensation with Transport Matching",
            "abstract": "We study graph condensation for efficient graph learning.",
            "keywords": "graph condensation; graph learning",
            "venue": "ICLR",
            "venue_id": "ICLR.cc/2025/Conference",
            "year": 2025,
            "note_id": "note-1",
            "pdf_url": "https://openreview.net/pdf?id=note-1",
            "matched_queries": "graph condensation",
            "matched_fields": "title;abstract;keywords",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            jsonl_path, csv_path = app.export_records([record], Path(tmpdir))

            self.assertTrue(jsonl_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertGreater(jsonl_path.stat().st_size, 0)
            self.assertGreater(csv_path.stat().st_size, 0)

    def test_write_run_report_writes_json(self) -> None:
        report = {
            "queries": ["graph condensation"],
            "years": [2021, 2022, 2023, 2024, 2025],
            "count": 1,
            "venues": [
                {
                    "query": "graph condensation",
                    "venue": "AAAI",
                    "venue_id": "AAAI.org/2025/Conference",
                    "year": 2025,
                    "status": "empty",
                    "matched_count": 0,
                    "error": "",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = app.write_run_report(report, Path(tmpdir))
            self.assertTrue(report_path.exists())
            self.assertGreater(report_path.stat().st_size, 0)

    def test_parse_args_accepts_queries_list(self) -> None:
        args = app.parse_args(["--queries", '["graph condensation", "graph distillation"]'])
        self.assertEqual(args.queries, ["graph condensation", "graph distillation"])

    def test_merge_semicolon_values_trims_and_deduplicates(self) -> None:
        merged = app.merge_semicolon_values(" graph condensation; condensed graph", "condensed graph; graph distillation")
        self.assertEqual(merged, ["condensed graph", "graph condensation", "graph distillation"])

    def test_query_index_records_matches_local_metadata(self) -> None:
        index_records = [
            {
                "title": "Structure-free Graph Condensation",
                "abstract": "Graph condensation reduces the size of large graphs.",
                "keywords": "graph condensation; graph learning",
                "venue": "NeurIPS",
                "venue_id": "NeurIPS.cc/2023/Conference",
                "year": 2023,
                "note_id": "note-1",
                "pdf_url": "https://openreview.net/pdf?id=note-1",
            }
        ]
        results = app.query_index_records(index_records, ["graph condensation", "graph distillation"])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["matched_queries"], "graph condensation")
        self.assertEqual(results[0]["venue"], "NeurIPS")

    def test_load_index_records_reads_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.jsonl"
            path.write_text(
                '{"title":"A","abstract":"B","keywords":"C","venue":"ICLR","venue_id":"ICLR.cc/2024/Conference","year":2024,"note_id":"n1","pdf_url":"https://openreview.net/pdf?id=n1"}\n',
                encoding="utf-8",
            )
            records = app.load_index_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["note_id"], "n1")

    def test_target_cache_roundtrip(self) -> None:
        target = app.Target(label="ICLR", venue_id="ICLR.cc/2025/Conference", year=2025)
        records = [
            {
                "title": "A",
                "abstract": "B",
                "keywords": "C",
                "venue": "ICLR",
                "venue_id": "ICLR.cc/2025/Conference",
                "year": 2025,
                "note_id": "n1",
                "pdf_url": "https://openreview.net/pdf?id=n1",
            }
        ]
        report = {
            "venue": "ICLR",
            "venue_id": "ICLR.cc/2025/Conference",
            "year": 2025,
            "status": "ok",
            "candidate_count": 1,
            "indexed_count": 1,
            "error": "",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            app.write_target_cache(cache_dir, target, records, report)
            cached_records, cached_report = app.load_target_cache(cache_dir, target)
            self.assertEqual(cached_records, records)
            self.assertEqual(cached_report["status"], "ok")


if __name__ == "__main__":
    unittest.main()
