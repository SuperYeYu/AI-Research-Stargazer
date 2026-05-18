from __future__ import annotations

import argparse
import json
from pathlib import Path

import query_openreview as core


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local OpenReview metadata index on the fixed venue/year whitelist."
    )
    parser.add_argument("--years", nargs="+", type=int, default=list(core.DEFAULT_YEARS))
    parser.add_argument("--outdir", default=str(Path(__file__).resolve().parent / "outputs"))
    parser.add_argument("--stem", default="openreview_index")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--no-resume", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records, jsonl_path, csv_path, report = core.build_index(
        years=args.years,
        outdir=Path(args.outdir),
        stem=args.stem,
        page_size=args.page_size,
        resume=not args.no_resume,
    )
    report_path = core.write_run_report(report, Path(args.outdir), filename=f"{args.stem}_build_report.json")
    summary = {
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
