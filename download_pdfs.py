from __future__ import annotations

import argparse
import csv
import http.client
import json
import re
from pathlib import Path
import time
import urllib.error
import urllib.request


def sanitize_filename_component(text: str, fallback: str = "unknown") -> str:
    text = str(text or "").strip()
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    return text or fallback


def make_pdf_filename(record: dict) -> str:
    title = sanitize_filename_component(record.get("title", ""), fallback="untitled")
    year = sanitize_filename_component(record.get("year", ""), fallback="unknown_year")
    venue = sanitize_filename_component(record.get("venue", ""), fallback="unknown_venue")
    note_id = sanitize_filename_component(record.get("note_id", ""), fallback="unknown_id")
    return f"{title}__{year}__{venue}__{note_id}.pdf"


def load_jsonl_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_csv_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_result_records(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return load_jsonl_records(path)
    if suffix == ".csv":
        return load_csv_records(path)
    raise ValueError(f"Unsupported input file type: {path.suffix}")


def resolve_pdf_url(record: dict) -> str:
    pdf_url = str(record.get("pdf_url", "")).strip()
    if pdf_url:
        return pdf_url
    note_id = str(record.get("note_id", "")).strip()
    if not note_id:
        raise ValueError("Record missing both pdf_url and note_id")
    return f"https://openreview.net/pdf?id={note_id}"


def _http_bytes(url: str, timeout: int = 120, retries: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"Accept": "application/pdf,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (http.client.IncompleteRead, urllib.error.URLError) as exc:
            last_error = exc
            if attempt + 1 == retries:
                raise
            time.sleep(1.0 + attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError("unexpected download state")


def download_records(
    records: list[dict],
    outdir: Path,
    overwrite: bool = False,
    limit: int | None = None,
    timeout: int = 120,
) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0
    files: list[dict] = []

    selected_records = records[:limit] if limit is not None else records
    for record in selected_records:
        filename = make_pdf_filename(record)
        path = outdir / filename
        pdf_url = resolve_pdf_url(record)

        if path.exists() and not overwrite:
            skipped += 1
            files.append({"path": str(path), "status": "skipped", "pdf_url": pdf_url, "note_id": record.get("note_id", "")})
            continue

        try:
            pdf_bytes = _http_bytes(pdf_url, timeout=timeout)
            path.write_bytes(pdf_bytes)
            downloaded += 1
            files.append({"path": str(path), "status": "downloaded", "pdf_url": pdf_url, "note_id": record.get("note_id", "")})
        except Exception as exc:
            failed += 1
            files.append(
                {
                    "path": str(path),
                    "status": "failed",
                    "pdf_url": pdf_url,
                    "note_id": record.get("note_id", ""),
                    "error": str(exc),
                }
            )

    return {
        "count": len(selected_records),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "files": files,
    }


def write_report(report: dict, outdir: Path, filename: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / filename
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download PDFs from filtered OpenReview result files.")
    parser.add_argument("--input", required=True, help="Path to a filtered result file in .csv or .jsonl format.")
    parser.add_argument("--outdir", required=True, help="Flat output directory for downloaded PDFs.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files instead of skipping them.")
    parser.add_argument("--limit", type=int, help="Only download the first N records from the input file.")
    parser.add_argument("--timeout", type=int, default=120, help="Per-file download timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    outdir = Path(args.outdir)
    records = load_result_records(input_path)
    report = download_records(
        records=records,
        outdir=outdir,
        overwrite=args.overwrite,
        limit=args.limit,
        timeout=args.timeout,
    )
    report.update(
        {
            "input": str(input_path),
            "outdir": str(outdir),
        }
    )
    report_path = write_report(report, outdir, f"{input_path.stem}_download_report.json")
    summary = {
        "input": str(input_path),
        "outdir": str(outdir),
        "count": report["count"],
        "downloaded": report["downloaded"],
        "skipped": report["skipped"],
        "failed": report["failed"],
        "report": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
