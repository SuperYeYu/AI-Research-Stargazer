English | [简体中文](./README.zh-CN.md)

#  <img src="./image/观星者_compressed.png" height="40" style="vertical-align: middle;" /> AI Research Stargazer

**AI Research Stargazer** is a practical command-line tool for building a **local metadata index** from selected OpenReview venues, running **offline keyword queries**, and downloading PDFs for the final filtered subset.

It is built for repeated literature discovery workflows:

1. **Index once** from OpenReview
2. **Query many times** locally
3. **Download only the papers you actually need**

This design reduces repeated calls to the OpenReview search API, lowers rate-limit pressure, and makes iterative filtering much faster.

## ✨ Core Features

- 📚 Build a local metadata index in `jsonl` and `csv`
- 🔎 Run offline queries over `title`, `abstract`, and `keywords`
- 🧩 Support multiple queries through a JSON list
- ♻️ Resume index building with cached venue/year shards
- 📄 Download PDFs from filtered `csv` or `jsonl` result files
- 🧾 Generate build reports, query reports, and download reports

## 🗂️ Supported Venues

The current built-in whitelist includes:

`AAAI` `ACL` `ACMMM` `CVPR` `EMNLP` `ECCV` `ICCV` `ICLR` `ICML` `KDD` `NeurIPS` `TMLR`

Year rules:

- Most venues are attempted for the latest **5 complete years**
- `ECCV` is attempted for **even years only**
- `ICCV` is attempted for **odd years only**
- `TMLR` is attempted from **2022 onward**

Important:

- The whitelist defines what the tool **tries** to index
- Actual availability still depends on whether a given `venue/year` has public records on OpenReview
- Final coverage is reported as `ok`, `empty`, or `skipped` in the build report

## 🧱 Project Structure

- `build_openreview_index.py` — build or resume the local metadata index
- `query_openreview.py` — query the local index offline
- `download_pdfs.py` — download PDFs from filtered result files
- `test_query_openreview.py` — tests for indexing and querying
- `test_download_pdfs.py` — tests for PDF downloading

## ⚙️ Installation

### Requirements

- Python `3.10+`
- No third-party Python packages required

### Step-by-step Setup

1. Clone the repository:

```bash
git clone <your-repo-url>
cd <your-repo>/openreview_local_index
```

2. Verify Python:

```bash
python --version
```

3. Optionally run tests:

```bash
python test_query_openreview.py
python test_download_pdfs.py
```

## 🚦 Quick Start

### Step 1: Build the local index

PowerShell:

```powershell
python build_openreview_index.py
```

Bash:

```bash
python build_openreview_index.py
```

By default, the tool indexes the latest **5 complete years**.

For example, if today is `2026-05-19`, the default range is:

```text
2021 2022 2023 2024 2025
```

### Step 2: Query the local index

Single query in PowerShell:

```powershell
python query_openreview.py --queries "graph condensation"
```

Legacy repeated flags are also supported:

```bash
python query_openreview.py --query "llm reasoning" --query "chain of thought"
```

### Step 3: Download PDFs from filtered results

From a filtered CSV:

```bash
python download_pdfs.py --input outputs/results.csv --outdir downloads
```

From a filtered JSONL:

```bash
python download_pdfs.py --input outputs/results.jsonl --outdir downloads
```

## 🧪 Detailed Usage Examples

### Build index for a single year

```bash
python build_openreview_index.py --years 2025 --stem openreview_index_2025
```

### Force a clean rebuild

```bash
python build_openreview_index.py --no-resume
```

### Use a larger page size

```bash
python build_openreview_index.py --page-size 1000
```

### Query a specific index file

```bash
python query_openreview.py \
  --queries "[\"retrieval augmented generation\", \"rag\"]" \
  --years 2024 2025 \
  --index outputs/openreview_index.jsonl \
  --stem rag_2024_2025
```

### Download only the first few PDFs as a smoke test

```bash
python download_pdfs.py --input outputs/results.csv --outdir downloads --limit 5
```

### Overwrite existing PDFs

```bash
python download_pdfs.py --input outputs/results.csv --outdir downloads --overwrite
```

## 📦 Output Files

### Index build outputs

Running `build_openreview_index.py` writes:

- `outputs/openreview_index.jsonl`
- `outputs/openreview_index.csv`
- `outputs/openreview_index_build_report.json`
- `outputs/openreview_index_shards/`

The shard directory stores per-venue/year caches and enables resume behavior.

### Query outputs

Running `query_openreview.py` writes: `<stem>.jsonl` `<stem>.csv` `<stem>_run_report.json`

Each result includes: `title` `abstract` `keywords` `venue` `venue_id` `year` `note_id` `pdf_url` `matched_queries` `matched_fields`

### Download outputs

Running `download_pdfs.py` writes:

- downloaded PDF files in a **flat directory**
- `<input_stem>_download_report.json`

Filename format:

```text
title__year__venue__note_id.pdf
```

Example:

```text
Bonsai_ Gradient-free Graph Condensation for Node Classification__2025__ICLR__5x88lQ2MsH.pdf
```

## 🔍 Query Semantics

Queries are matched locally against: `title` `abstract` `keywords`

## 📝 Typical Workflow

1. Build a local index once
2. Run broad topic queries
3. Inspect the `csv/jsonl` results
4. Optionally apply second-stage filtering
5. Download PDFs for the final subset

## ⚠️ Notes

- Some venue/year combinations may legitimately return no public records
- `empty` does not necessarily mean the venue does not exist; it means no records were returned for that target
- `skipped` usually means a failed request and may be worth retrying later
- The index stores **metadata only**; it does not store PDFs
