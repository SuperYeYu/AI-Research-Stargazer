English | [简体中文](./README.zh-CN.md)

# OpenReview-Crawler4ML

Build a local metadata index for selected OpenReview venues and run offline keyword queries against that index.

This project is designed for repeated literature searches:

1. Fetch metadata once from OpenReview and build a local index.
2. Run many queries offline against the local index.

That avoids hitting the OpenReview search endpoint for every query and makes iterative filtering much faster.

## Features

- Fixed venue/year whitelist for major ML, NLP, vision, and data mining venues
- Default range: the latest 5 complete years
- Local index in `jsonl` and `csv`
- Offline querying over `title`, `abstract`, and `keywords`
- Multi-query support via JSON list input
- Per-venue build report and query report
- Resumable index building with cached shards

## Venue Whitelist

The current built-in whitelist includes these venues and journals:

- `AAAI`
- `ACL`
- `ACMMM`
- `CVPR`
- `EMNLP`
- `ECCV`
- `ICCV`
- `ICLR`
- `ICML`
- `KDD`
- `NeurIPS`
- `TMLR`

Notes on year patterns:

- Most venues are attempted for the latest 5 complete years.
- `ECCV` is only attempted for even years.
- `ICCV` is only attempted for odd years.
- `TMLR` is attempted from `2022` onward.

Important:

- The whitelist defines what the tool will attempt to index.
- Actual OpenReview availability still depends on whether a given `venue/year` has public records on OpenReview.
- The build report will show whether each target ended up as `ok`, `empty`, or `skipped`.

## Project Layout

- `build_openreview_index.py`: build or resume the local index
- `query_openreview.py`: run offline queries against a local index
- `test_query_openreview.py`: unit tests

## Requirements

- Python 3.10+
- No third-party Python dependencies

## Quick Start

### 1. Build the index

PowerShell:

```powershell
python openreview_local_index/build_openreview_index.py
```

Bash:

```bash
python openreview_local_index/build_openreview_index.py
```

By default this builds the latest 5 complete years.

For example, if the current date is `2026-05-18`, the default range is:

```text
2021 2022 2023 2024 2025
```

### 2. Query the local index

Single query in PowerShell:

```powershell
python openreview_local_index/query_openreview.py --queries '["graph condensation"]'
```

Multiple queries in PowerShell:

```powershell
python openreview_local_index/query_openreview.py --queries '["graph condensation", "graph distillation", "condensed graph"]'
```

Bash:

```bash
python openreview_local_index/query_openreview.py --queries "[\"graph condensation\", \"graph distillation\"]"
```

Legacy repeated flags are still supported:

```bash
python openreview_local_index/query_openreview.py --query "llm reasoning" --query "chain of thought"
```

## Outputs

### Index build

Running `build_openreview_index.py` writes:

- `outputs/openreview_index.jsonl`
- `outputs/openreview_index.csv`
- `outputs/openreview_index_build_report.json`
- `outputs/openreview_index_shards/`

The shard directory enables resume behavior. If a venue/year shard has already been built, rerunning the same command will reuse it.

To force a clean rebuild:

```bash
python openreview_local_index/build_openreview_index.py --no-resume
```

### Query results

Running `query_openreview.py` writes:

- `<stem>.jsonl`
- `<stem>.csv`
- `<stem>_run_report.json`

Each result row contains:

- `title`
- `abstract`
- `keywords`
- `venue`
- `venue_id`
- `year`
- `note_id`
- `pdf_url`
- `matched_queries`
- `matched_fields`

## Query Semantics

Queries are matched locally against:

- `title`
- `abstract`
- `keywords`

Matching is:

- case-insensitive
- whitespace-normalized
- substring-based

This is intentionally simple and transparent. It is not embedding search or semantic retrieval.

## Typical Workflow

1. Build a local index for the target year range.
2. Run a broad set of topic queries.
3. Review the `csv/jsonl` result set.
4. Apply second-stage filtering manually or with another script.
5. Download PDFs only for the final subset if needed.

## Example Commands

Build only 2025:

```bash
python openreview_local_index/build_openreview_index.py --years 2025 --stem openreview_index_2025
```

Query only 2024 and 2025 from an existing index:

```bash
python openreview_local_index/query_openreview.py --queries '["retrieval augmented generation", "rag"]' --years 2024 2025 --index openreview_local_index/outputs/openreview_index.jsonl --stem rag_2024_2025
```

## Notes

- Some venue/year combinations may legitimately return no records in OpenReview.
- Build reports distinguish `ok`, `empty`, and `skipped`.
- `skipped` usually means a request failed or should be retried later.
- The index stores metadata only. It does not download PDFs.
