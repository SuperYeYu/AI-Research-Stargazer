[English](./README.md) | 简体中文

# <img src="./image/观星者_compressed.png" height="40" style="vertical-align: middle;" /> AI Research Stargazer

**AI Research Stargazer** 是一个面向 OpenReview 的实用型命令行工具，用于：

- 构建**本地论文元数据索引**
- 基于本地索引执行**离线关键词查询**
- 为最终筛选结果**批量下载 PDF**

它适合反复进行文献调研的场景：

1. **先抓一次索引**
2. **后续本地反复查询**
3. **只下载最终需要的论文**

这种两阶段设计可以减少重复调用 OpenReview 搜索接口，降低限流压力，并显著提升多轮筛选效率。

## ✨ 核心特性

- 📚 将 OpenReview 元数据构建为本地 `jsonl` / `csv` 索引
- 🔎 基于 `title`、`abstract`、`keywords` 执行离线查询
- 🧩 支持 JSON 列表形式的多 query 输入
- ♻️ 支持按 `venue/year` 分片缓存和断点续跑
- 📄 支持从筛选后的 `csv` / `jsonl` 结果中下载 PDF
- 🧾 自动生成构建报告、查询报告、下载报告

## 🗂️ 当前支持的会议与期刊

当前内置白名单包括：`AAAI` `ACL` `ACMMM` `CVPR` `EMNLP` `ECCV` `ICCV` `ICLR` `ICML` `KDD` `NeurIPS` `TMLR`

年份规则如下：

- 大多数 venue 会尝试最近 **5 个完整年份**
- `ECCV` 只尝试**偶数年**
- `ICCV` 只尝试**奇数年**
- `TMLR` 从 **2022 年**开始尝试

需要注意：

- 白名单只表示工具会**尝试抓取**这些目标
- 某个具体 `venue/year` 是否真的有公开记录，仍然取决于 OpenReview 实际数据
- 最终覆盖情况以构建报告中的 `ok`、`empty`、`skipped` 为准

## 🧱 项目结构

- `build_openreview_index.py` —— 构建或续跑本地索引
- `query_openreview.py` —— 基于本地索引执行离线查询
- `download_pdfs.py` —— 从筛选结果文件中下载 PDF
- `test_query_openreview.py` —— 索引与查询测试
- `test_download_pdfs.py` —— PDF 下载测试

## ⚙️ 安装指南

### 环境要求

- Python `3.10+`
- 不依赖第三方 Python 包

### 分步骤安装

1. 克隆仓库：

```bash
git clone <your-repo-url>
cd <your-repo>/openreview_local_index
```

2. 检查 Python 版本：

```bash
python --version
```

3. 可选：运行测试确认环境正常：

```bash
python test_query_openreview.py
python test_download_pdfs.py
```

## 🚦快速开始

### 第 1 步：构建本地索引

PowerShell：

```powershell
python build_openreview_index.py
```

Bash：

```bash
python build_openreview_index.py
```

默认会构建最近 **5 个完整年份** 的索引。

例如，如果今天是 `2026-05-19`，默认范围为：

```text
2021 2022 2023 2024 2025
```

### 第 2 步：查询本地索引

PowerShell，单个 query：

```powershell
python query_openreview.py --queries "graph condensation"
```

Bash：

也兼容旧的重复参数写法：

```bash
python query_openreview.py --query "llm reasoning" --query "chain of thought"
```

### 第 3 步：下载筛选后的 PDF

从筛选后的 CSV 下载：

```bash
python download_pdfs.py --input outputs/results.csv --outdir downloads
```

从筛选后的 JSONL 下载：

```bash
python download_pdfs.py --input outputs/results.jsonl --outdir downloads
```

## 🧪 详细使用示例

### 只构建 2025 年索引

```bash
python build_openreview_index.py --years 2025 --stem openreview_index_2025
```

### 强制重新构建

```bash
python build_openreview_index.py --no-resume
```

### 使用更大的分页

```bash
python build_openreview_index.py --page-size 1000
```

### 指定已有索引文件进行查询

```bash
python query_openreview.py \
  --queries "[\"retrieval augmented generation\", \"rag\"]" \
  --years 2024 2025 \
  --index outputs/openreview_index.jsonl \
  --stem rag_2024_2025
```

### 先小规模试下载几篇

```bash
python download_pdfs.py --input outputs/results.csv --outdir downloads --limit 5
```

### 覆盖已存在的 PDF

```bash
python download_pdfs.py --input outputs/results.csv --outdir downloads --overwrite
```

## 📦 输出文件说明

### 索引构建输出

运行 `build_openreview_index.py` 后会生成：

- `outputs/openreview_index.jsonl`
- `outputs/openreview_index.csv`
- `outputs/openreview_index_build_report.json`
- `outputs/openreview_index_shards/`

其中 `openreview_index_shards/` 保存分片缓存，用于支持断点续跑。

### 查询输出

运行 `query_openreview.py` 后会生成：`<stem>.jsonl` `<stem>.csv` `<stem>_run_report.json`

每条结果包含：`title` `abstract` `keywords` `venue` `venue_id` `year` `note_id` `pdf_url` `matched_queries` `matched_fields`

### 下载输出

运行 `download_pdfs.py` 后会生成：

- 单层平铺的 PDF 文件
- `<input_stem>_download_report.json`

文件命名规则：

```text
title__year__venue__note_id.pdf
```

例如：

```text
Bonsai_ Gradient-free Graph Condensation for Node Classification__2025__ICLR__5x88lQ2MsH.pdf
```

## 🔍 查询语义

查询会在以下字段上进行本地匹配：`title` `abstract` `keywords`

## 📝 推荐工作流

1. 先构建一次本地索引
2. 再执行较宽松的主题查询
3. 检查导出的 `csv/jsonl`
4. 如有需要，继续做第二阶段筛选
5. 最后只下载最终子集的 PDF

## ⚠️ 注意事项

- 某些 `venue/year` 组合在 OpenReview 上可能确实没有公开记录
- `empty` 不一定表示 venue 不存在，只表示该目标没有返回记录
- `skipped` 通常表示请求失败，适合稍后重试
- 本地索引只保存**元数据**，不保存 PDF
