[English](./README.md) | 简体中文

# OpenReview-Crawler4ML

这个项目用于为指定的 OpenReview 会议/期刊构建本地元数据索引，并基于该索引离线执行关键词查询。

它适合反复进行文献调研的场景：

1. 先从 OpenReview 抓取一次元数据并构建本地索引。
2. 后续针对本地索引离线运行很多组查询。

这样可以避免每次查询都重复请求 OpenReview 搜索接口，显著降低限流风险，并提升多轮筛选效率。

## 功能

- 针对主要 ML、NLP、CV、数据挖掘 venue 的固定 `venue/year` 白名单
- 默认覆盖最近 5 个完整年份
- 本地索引导出为 `jsonl` 和 `csv`
- 基于 `title`、`abstract`、`keywords` 的离线查询
- 支持 JSON 列表形式的多 query 输入
- 支持索引构建报告和查询报告
- 支持分片缓存和断点续跑

## 当前支持的会议与期刊

当前内置白名单包括以下会议/期刊：

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

关于年份有几点需要说明：

- 大多数 venue 会按最近 5 个完整年份尝试抓取。
- `ECCV` 只会尝试偶数年。
- `ICCV` 只会尝试奇数年。
- `TMLR` 从 `2022` 年开始尝试。

需要注意：

- 白名单只决定“工具会尝试抓哪些目标”。
- 某个具体 `venue/year` 最终是否真的有数据，仍然取决于 OpenReview 上是否存在公开记录。
- 最终结果以构建报告为准，报告里会明确标记 `ok`、`empty` 或 `skipped`。

## 目录结构

- `build_openreview_index.py`：构建或续跑本地索引
- `query_openreview.py`：基于本地索引执行离线查询
- `download_pdfs.py`：从筛选后的 `.csv` 或 `.jsonl` 结果文件下载 PDF
- `test_query_openreview.py`：单元测试

## 运行要求

- Python 3.10+
- 不依赖第三方 Python 包

## 快速开始

### 1. 构建本地索引

PowerShell：

```powershell
python openreview_local_index/build_openreview_index.py
```

Bash：

```bash
python openreview_local_index/build_openreview_index.py
```

默认会构建最近 5 个完整年份的数据。

例如，如果当前日期是 `2026-05-18`，默认年份范围为：

```text
2021 2022 2023 2024 2025
```

### 2. 基于本地索引查询

PowerShell，单个 query：

```powershell
python openreview_local_index/query_openreview.py --queries '["graph condensation"]'
```

PowerShell，多个 query：

```powershell
python openreview_local_index/query_openreview.py --queries '["graph condensation", "graph distillation", "condensed graph"]'
```

Bash：

```bash
python openreview_local_index/query_openreview.py --queries "[\"graph condensation\", \"graph distillation\"]"
```

也兼容旧的重复参数写法：

```bash
python openreview_local_index/query_openreview.py --query "llm reasoning" --query "chain of thought"
```

## 输出文件

### 索引构建输出

运行 `build_openreview_index.py` 后会生成：

- `outputs/openreview_index.jsonl`
- `outputs/openreview_index.csv`
- `outputs/openreview_index_build_report.json`
- `outputs/openreview_index_shards/`

其中 `openreview_index_shards/` 是分片缓存目录，用于断点续跑。如果某个 `venue/year` 分片已经成功构建，再次执行相同命令时会直接复用。

如果你要强制重新构建：

```bash
python openreview_local_index/build_openreview_index.py --no-resume
```

### 查询输出

运行 `query_openreview.py` 后会生成：

- `<stem>.jsonl`
- `<stem>.csv`
- `<stem>_run_report.json`

每条结果至少包含：

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

## 查询语义

查询会在本地对以下字段执行匹配：

- `title`
- `abstract`
- `keywords`

当前匹配规则是：

- 大小写不敏感
- 空白归一化
- 基于子串匹配

这是一个刻意保持简单、可解释的实现。它不是 embedding 检索，也不是语义检索。

## 推荐工作流

1. 先为目标年份范围构建本地索引。
2. 用一组相对宽松的 query 进行初筛。
3. 检查导出的 `csv/jsonl`。
4. 根据需要继续做第二阶段过滤。
5. 最后只为最终子集下载 PDF。

## 从筛选结果下载 PDF

当你已经有筛选后的结果文件时，可以把 PDF 下载到一个单层平铺目录里。

下载器适合放在整个工作流的最后一步：

1. 先构建本地元数据索引
2. 再执行离线查询
3. 如有需要，再做第二轮筛选
4. 最后只为筛选后的结果下载 PDF

支持的输入格式：

- `.csv`
- `.jsonl`

每条记录至少需要这些字段：

- `title`
- `year`
- `venue`
- `note_id`
- `pdf_url` 或 `note_id`

如果记录里没有 `pdf_url`，下载器会根据 `note_id` 自动拼出 OpenReview 的 PDF 链接。

下面是一个基于筛选后 CSV 的下载示例：

PowerShell：

```powershell
python openreview_local_index/download_pdfs.py --input openreview_local_index/outputs/local_index_graph_gc_gd_5y.csv --outdir openreview_local_index/downloads
```

Bash：

```bash
python openreview_local_index/download_pdfs.py --input openreview_local_index/outputs/local_index_graph_gc_gd_5y.jsonl --outdir openreview_local_index/downloads
```

默认行为：

- 所有 PDF 直接下载到同一层目录
- 如果目标文件已存在，则默认跳过
- 会在下载目录中额外生成一份下载报告

文件命名规则：

```text
title__year__venue__note_id.pdf
```

例如：

```text
Bonsai_ Gradient-free Graph Condensation for Node Classification__2025__ICLR__5x88lQ2MsH.pdf
```

如果你希望覆盖已有文件：

```bash
python openreview_local_index/download_pdfs.py --input openreview_local_index/outputs/results.csv --outdir openreview_local_index/downloads --overwrite
```

如果你想先小规模试跑几条：

```bash
python openreview_local_index/download_pdfs.py --input openreview_local_index/outputs/results.csv --outdir openreview_local_index/downloads --limit 5
```

每次下载后都会额外生成一份报告文件：

```text
<input_stem>_download_report.json
```

报告中会包含：

- 本次处理的总记录数
- 成功下载数
- 跳过数
- 失败数
- 每个文件的状态和错误信息

## 示例命令

只构建 `2025` 年索引：

```bash
python openreview_local_index/build_openreview_index.py --years 2025 --stem openreview_index_2025
```

基于已有索引，只查询 `2024` 和 `2025`：

```bash
python openreview_local_index/query_openreview.py --queries '["retrieval augmented generation", "rag"]' --years 2024 2025 --index openreview_local_index/outputs/openreview_index.jsonl --stem rag_2024_2025
```

## 说明

- 某些 `venue/year` 组合在 OpenReview 上可能确实没有公开记录。
- 构建报告会区分 `ok`、`empty` 和 `skipped`。
- `skipped` 通常表示该请求失败，或者适合稍后重试。
- 本地索引只保存元数据，不下载 PDF。
