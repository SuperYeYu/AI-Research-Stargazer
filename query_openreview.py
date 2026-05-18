from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import urllib.error
import urllib.parse
import urllib.request


API_BASE = "https://api2.openreview.net"
CSV_FIELDS = [
    "query",
    "title",
    "abstract",
    "keywords",
    "venue",
    "venue_id",
    "year",
    "note_id",
    "pdf_url",
    "matched_queries",
    "matched_fields",
]
INDEX_FIELDS = [
    "title",
    "abstract",
    "keywords",
    "venue",
    "venue_id",
    "year",
    "note_id",
    "pdf_url",
]


def _default_years() -> tuple[int, ...]:
    current_year = datetime.now(timezone.utc).year
    return tuple(range(current_year - 5, current_year))


DEFAULT_YEARS = _default_years()


def _conference_ids(prefix: str, years: Iterable[int]) -> dict[int, list[str]]:
    return {year: [f"{prefix}/{year}/Conference"] for year in years}


@dataclass(frozen=True)
class Target:
    label: str
    venue_id: str
    year: int
    filter_by_year: bool = False


VENUE_RULES: dict[str, dict[int, list[str]]] = {
    "AAAI": _conference_ids("AAAI.org", range(2021, 2026)),
    "ACL": _conference_ids("aclweb.org/ACL", range(2021, 2026)),
    "ACMMM": _conference_ids("acmmm.org/ACMMM", range(2021, 2026)),
    "CVPR": _conference_ids("thecvf.com/CVPR", range(2021, 2026)),
    "ECCV": _conference_ids("thecvf.com/ECCV", (2022, 2024)),
    "EMNLP": _conference_ids("EMNLP", range(2021, 2026)),
    "ICCV": _conference_ids("thecvf.com/ICCV", (2021, 2023, 2025)),
    "ICLR": _conference_ids("ICLR.cc", range(2021, 2026)),
    "ICML": _conference_ids("ICML.cc", range(2021, 2026)),
    "KDD": {
        2021: [
            "KDD.org/2021/Conference",
            "KDD.org/2021/Research Track",
            "KDD.org/2021/Applied Data Science Track",
        ],
        2022: [
            "KDD.org/2022/Conference",
            "KDD.org/2022/Research Track",
            "KDD.org/2022/Applied Data Science Track",
        ],
        2023: [
            "KDD.org/2023/Conference",
            "KDD.org/2023/Conference Research Track",
            "KDD.org/2023/Conference Applied Data Science Track",
        ],
        2024: [
            "KDD.org/2024/Research Track",
            "KDD.org/2024/Applied Data Science Track",
        ],
        2025: [
            "KDD.org/2025/Research Track February",
            "KDD.org/2025/Research Track August",
            "KDD.org/2025/ADS Track February",
            "KDD.org/2025/ADS Track August",
            "KDD.org/2025/Datasets and Benchmarks Track February",
        ],
    },
    "NeurIPS": _conference_ids("NeurIPS.cc", range(2021, 2026)),
    "TMLR": {
        2022: ["TMLR"],
        2023: ["TMLR"],
        2024: ["TMLR"],
        2025: ["TMLR"],
    },
}


def build_targets(years: Iterable[int] = DEFAULT_YEARS) -> list[Target]:
    targets: list[Target] = []
    wanted = set(years)
    for label, year_map in VENUE_RULES.items():
        for year in sorted(wanted):
            for venue_id in year_map.get(year, []):
                targets.append(
                    Target(
                        label=label,
                        venue_id=venue_id,
                        year=year,
                        filter_by_year=(venue_id == "TMLR"),
                    )
                )
    return targets


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def parse_queries_arg(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"--queries must be a JSON list string: {exc}") from exc
    if not isinstance(value, list):
        raise argparse.ArgumentTypeError('--queries must be a JSON list string, for example ["graph condensation"]')
    queries: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise argparse.ArgumentTypeError("--queries must contain strings only")
        item = item.strip()
        if item:
            queries.append(item)
    if not queries:
        raise argparse.ArgumentTypeError("--queries must not be an empty list")
    return queries


def merge_semicolon_values(*values: str) -> list[str]:
    merged: set[str] = set()
    for value in values:
        for chunk in value.split(";"):
            chunk = chunk.strip()
            if chunk:
                merged.add(chunk)
    return sorted(merged)


def _content_value(note: dict, key: str) -> str:
    content = note.get("content") or {}
    value = content.get(key, "")
    if isinstance(value, dict):
        value = value.get("value", "")
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _content_keywords(note: dict) -> list[str]:
    content = note.get("content") or {}
    value = content.get("keywords", "")
    if isinstance(value, dict):
        value = value.get("value", "")
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    return [chunk.strip() for chunk in str(value).split(";") if chunk.strip()]


def _note_year(note: dict) -> int | None:
    for key in ("tcdate", "cdate", "tmdate", "pdate"):
        raw = note.get(key)
        if isinstance(raw, (int, float)) and raw > 0:
            seconds = raw / 1000 if raw > 10_000_000_000 else raw
            return datetime.fromtimestamp(seconds, tz=timezone.utc).year
    return None


def match_queries_in_fields(fields: dict[str, str], queries: list[str]) -> tuple[list[str], list[str]]:
    normalized_fields = {name: _normalize(value) for name, value in fields.items()}
    matched_queries: list[str] = []
    matched_fields: list[str] = []
    for query in queries:
        normalized_query = _normalize(query)
        if not normalized_query:
            continue
        query_hit = False
        for field_name, field_value in normalized_fields.items():
            if normalized_query in field_value:
                query_hit = True
                if field_name not in matched_fields:
                    matched_fields.append(field_name)
        if query_hit:
            matched_queries.append(query)
    return matched_queries, matched_fields


def note_matches_queries(note: dict, queries: list[str]) -> tuple[list[str], list[str]]:
    fields = {
        "title": _content_value(note, "title"),
        "abstract": _content_value(note, "abstract"),
        "keywords": "; ".join(_content_keywords(note)),
    }
    return match_queries_in_fields(fields, queries)


def _http_json(url: str, retries: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt + 1 == retries:
                raise
            time.sleep(2.0 + attempt * 2.0)
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt + 1 == retries:
                raise
            time.sleep(1.0 + attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError("unexpected http state")


def fetch_forum_notes(venue_id: str, page_size: int = 200) -> list[dict]:
    notes: list[dict] = []
    offset = 0
    while True:
        params = urllib.parse.urlencode(
            {
                "content.venueid": venue_id,
                "limit": page_size,
                "offset": offset,
            }
        )
        data = _http_json(f"{API_BASE}/notes?{params}")
        batch = data.get("notes") or []
        if not batch:
            break
        notes.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return notes


def should_keep(note: dict, target: Target) -> bool:
    if not target.filter_by_year:
        return True
    return _note_year(note) == target.year


def flatten_index_record(note: dict, target: Target) -> dict:
    return {
        "title": _content_value(note, "title"),
        "abstract": _content_value(note, "abstract"),
        "keywords": "; ".join(_content_keywords(note)),
        "venue": target.label,
        "venue_id": target.venue_id,
        "year": target.year,
        "note_id": note.get("id", ""),
        "pdf_url": f"https://openreview.net/pdf?id={note.get('id', '')}",
    }


def flatten_query_record(index_record: dict, matched_queries: list[str], matched_fields: list[str]) -> dict:
    return {
        "query": "; ".join(matched_queries),
        "title": index_record.get("title", ""),
        "abstract": index_record.get("abstract", ""),
        "keywords": index_record.get("keywords", ""),
        "venue": index_record.get("venue", ""),
        "venue_id": index_record.get("venue_id", ""),
        "year": index_record.get("year", ""),
        "note_id": index_record.get("note_id", ""),
        "pdf_url": index_record.get("pdf_url", ""),
        "matched_queries": "; ".join(matched_queries),
        "matched_fields": ";".join(matched_fields),
    }


def export_records(records: list[dict], outdir: Path, stem: str = "results", fields: list[str] | None = None) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    jsonl_path = outdir / f"{stem}.jsonl"
    csv_path = outdir / f"{stem}.csv"
    fieldnames = fields or CSV_FIELDS
    with jsonl_path.open("w", encoding="utf-8", newline="") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field, "") for field in fieldnames})
    return jsonl_path, csv_path


def write_run_report(report: dict, outdir: Path, filename: str = "run_report.json") -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    report_path = outdir / filename
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def target_cache_key(target: Target) -> str:
    safe_venue_id = target.venue_id.replace("/", "__").replace(" ", "_")
    return f"{target.year}__{target.label}__{safe_venue_id}"


def target_cache_paths(cache_dir: Path, target: Target) -> tuple[Path, Path]:
    key = target_cache_key(target)
    return cache_dir / f"{key}.jsonl", cache_dir / f"{key}.report.json"


def write_target_cache(cache_dir: Path, target: Target, records: list[dict], report: dict) -> tuple[Path, Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    data_path, report_path = target_cache_paths(cache_dir, target)
    with data_path.open("w", encoding="utf-8", newline="") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return data_path, report_path


def load_target_cache(cache_dir: Path, target: Target) -> tuple[list[dict], dict] | tuple[None, None]:
    data_path, report_path = target_cache_paths(cache_dir, target)
    if not report_path.exists():
        return None, None
    records: list[dict] = []
    if data_path.exists():
        with data_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return records, report


def build_index(
    years: list[int],
    outdir: Path,
    stem: str = "openreview_index",
    page_size: int = 1000,
    resume: bool = True,
) -> tuple[list[dict], Path, Path, dict]:
    records_by_note_id: dict[str, dict] = {}
    venue_reports: list[dict] = []
    cache_dir = outdir / f"{stem}_shards"
    for target in build_targets(years):
        if resume:
            cached_records, cached_report = load_target_cache(cache_dir, target)
            if cached_report is not None:
                for record in cached_records:
                    note_id = record.get("note_id", "")
                    if note_id:
                        records_by_note_id[note_id] = record
                cached_report = dict(cached_report)
                cached_report["status"] = f"cached:{cached_report.get('status', 'ok')}"
                venue_reports.append(cached_report)
                continue
        try:
            notes = fetch_forum_notes(target.venue_id, page_size=page_size)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            venue_reports.append(
                {
                    "venue": target.label,
                    "venue_id": target.venue_id,
                    "year": target.year,
                    "status": "skipped",
                    "candidate_count": 0,
                    "indexed_count": 0,
                    "error": str(exc),
                }
            )
            continue
        indexed_count = 0
        target_records: list[dict] = []
        for note in notes:
            if not should_keep(note, target):
                continue
            note_id = note.get("id", "")
            if not note_id:
                continue
            indexed_count += 1
            record = flatten_index_record(note, target)
            target_records.append(record)
            records_by_note_id[note_id] = record
        venue_report = {
            "venue": target.label,
            "venue_id": target.venue_id,
            "year": target.year,
            "status": "ok" if indexed_count > 0 else "empty",
            "candidate_count": len(notes),
            "indexed_count": indexed_count,
            "error": "",
        }
        write_target_cache(cache_dir, target, target_records, venue_report)
        venue_reports.append(venue_report)
    records = sorted(records_by_note_id.values(), key=lambda item: (item["year"], item["venue"], item["title"]))
    jsonl_path, csv_path = export_records(records, outdir, stem=stem, fields=INDEX_FIELDS)
    report = {
        "years": years,
        "count": len(records),
        "jsonl": str(jsonl_path),
        "csv": str(csv_path),
        "cache_dir": str(cache_dir),
        "venues": venue_reports,
    }
    return records, jsonl_path, csv_path, report


def load_index_records(index_path: Path) -> list[dict]:
    records: list[dict] = []
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def query_index_records(index_records: list[dict], queries: list[str], years: list[int] | None = None) -> list[dict]:
    year_filter = set(years) if years else None
    results: list[dict] = []
    for record in index_records:
        record_year = int(record.get("year", 0))
        if year_filter is not None and record_year not in year_filter:
            continue
        fields = {
            "title": str(record.get("title", "")),
            "abstract": str(record.get("abstract", "")),
            "keywords": str(record.get("keywords", "")),
        }
        matched_queries, matched_fields = match_queries_in_fields(fields, queries)
        if not matched_queries:
            continue
        results.append(flatten_query_record(record, matched_queries, matched_fields))
    return sorted(results, key=lambda item: (item["year"], item["venue"], item["title"]))


def build_query_report(
    results: list[dict],
    queries: list[str],
    years: list[int],
    index_path: Path,
    indexed_count: int,
) -> dict:
    venue_counts: dict[tuple[str, str, int], int] = {}
    for record in results:
        key = (record["venue"], record["venue_id"], int(record["year"]))
        venue_counts[key] = venue_counts.get(key, 0) + 1
    venues = [
        {
            "venue": venue,
            "venue_id": venue_id,
            "year": year,
            "matched_count": count,
        }
        for (venue, venue_id, year), count in sorted(venue_counts.items(), key=lambda item: (item[0][2], item[0][0]))
    ]
    return {
        "queries": queries,
        "years": years,
        "count": len(results),
        "index_path": str(index_path),
        "indexed_count": indexed_count,
        "venues": venues,
    }


def run_query(
    queries: list[str],
    years: list[int],
    outdir: Path,
    stem: str = "results",
    index_path: Path | None = None,
) -> tuple[list[dict], Path, Path, dict]:
    resolved_index_path = index_path or (Path(__file__).resolve().parent / "outputs" / "openreview_index.jsonl")
    index_records = load_index_records(resolved_index_path)
    records = query_index_records(index_records, queries, years=years)
    jsonl_path, csv_path = export_records(records, outdir, stem=stem, fields=CSV_FIELDS)
    report = build_query_report(records, queries, years, resolved_index_path, indexed_count=len(index_records))
    return records, jsonl_path, csv_path, report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query a local OpenReview metadata index on a fixed venue/year whitelist and export matching results."
    )
    parser.add_argument("--query", action="append", help="Query phrase to match in title, abstract, or keywords.")
    parser.add_argument("--queries", type=parse_queries_arg, help='JSON list string, e.g. ["graph condensation", "graph distillation"]')
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--index", default=str(Path(__file__).resolve().parent / "outputs" / "openreview_index.jsonl"))
    parser.add_argument("--outdir", default=str(Path(__file__).resolve().parent / "outputs"))
    parser.add_argument("--stem", default="results")
    args = parser.parse_args(argv)
    merged_queries: list[str] = []
    if args.queries:
        merged_queries.extend(args.queries)
    if args.query:
        merged_queries.extend(args.query)
    if not merged_queries:
        parser.error("you must provide --queries or at least one --query")
    args.queries = merged_queries
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        records, jsonl_path, csv_path, report = run_query(
            queries=args.queries,
            years=args.years,
            outdir=Path(args.outdir),
            stem=args.stem,
            index_path=Path(args.index),
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Index file not found: {exc}") from exc
    report_path = write_run_report(report, Path(args.outdir), filename=f"{args.stem}_run_report.json")
    summary = {
        "queries": args.queries,
        "years": args.years,
        "count": len(records),
        "jsonl": str(jsonl_path),
        "csv": str(csv_path),
        "report": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
