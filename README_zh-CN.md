# miniR: Local RAG Retrieval Backend for AI Agents

[English](README.md) | [简体中文](README_zh-CN.md)

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![FAISS](https://img.shields.io/badge/vector-FAISS-orange)
![License](https://img.shields.io/badge/license-MIT-green)

miniR 是一个轻量级、自托管的 RAG 检索后端，面向 AI Agent、聊天系统和内部知识库工具。它可以入库 Markdown、Word、PPT、Excel 和 PDF 文档，构建本地混合索引，并通过 REST API 或 Agent Skill 返回可直接用于回答的证据上下文。

![miniR 文档入库界面](assets/screenshots/web-ui-import.svg)

## 核心定位

miniR 只负责文档解析、分片、索引、检索和证据返回，不内置 LLM 调用。上层 Agent 可以通过 `/retrieve` 拿到稳定的文本证据和相关本地图片路径，再自行交给模型生成最终答案。

```text
本地文档 -> 解析/分片 -> SQLite + FAISS + BM25 + Sparse -> /retrieve -> Agent/LLM
```

建议 GitHub topics：`rag`、`retrieval-augmented-generation`、`ai-agent`、`local-first`、`fastapi`、`faiss`、`hybrid-search`、`document-processing`、`knowledge-base`、`python`。

## 核心能力

- **多格式文档入库**：支持 Markdown、Word、PowerPoint、Excel、PDF；图片仅作为文档内引用或内嵌资源保留。
- **文本优先解析**：Office/PDF 会提取可读取文本和文档内图片；扫描 PDF 不做 OCR，图片内容不做语义识别。
- **混合检索**：BM25 + BGE-M3 Dense + BGE-M3 Sparse，经 RRF 融合后可选 BGE Reranker 精排。
- **本地自托管**：SQLite 存储元数据，FAISS 存储向量，模型和索引均可本地离线运行。
- **可视化入库**：Gradio Web UI 支持目录扫描、分片预览、人工审核、图片预览和确认入库。
- **文档管理**：支持文档列表、启用/停用、删除、统计、索引同步和一键清库。
- **Agent 友好**：提供 REST API 和 `skill/minir-retrieval`，Codex、Claude Code 等 Agent 可直接接入。

## 截图

![miniR 检索测试界面](assets/screenshots/retrieval-output.svg)

## 接入方式

| 场景 | 方式 |
| --- | --- |
| Agent/LLM 工具调用 | `POST /retrieve` 返回可引用证据 |
| Codex / Claude Code 等 AI 编程工具 | 使用内置 `skill/minir-retrieval` |
| 本地管理和人工审核 | 启动 `web_ui.py` 使用 Gradio Web UI |
| 批量入库和维护 | 使用 `scripts/add_documents.py`、`scripts/manage_documents.py` |

## 快速开始

### 1. 安装依赖

建议使用 Python 3.12 环境。

```bash
pip install -r requirements.txt
```

如果只运行解析层单元测试，可以安装轻量依赖：

```bash
pip install numpy python-docx python-pptx openpyxl PyMuPDF
```

### 2. 下载模型

将模型放到 `modelscope_models/` 下：

```bash
modelscope download --model BAAI/bge-m3 --local_dir modelscope_models/bge-m3
modelscope download --model BAAI/bge-reranker-v2-m3 --local_dir modelscope_models/bge-reranker-v2-m3
```

默认模型路径来自 [config/paths.json](config/paths.json)：

```json
{
  "model_path": "modelscope_models/bge-m3",
  "reranker_path": "modelscope_models/bge-reranker-v2-m3"
}
```

### 3. 启动 API 服务

```bash
python fastapi_server.py
```

- API 文档：<http://localhost:8765/docs>
- 健康检查：<http://localhost:8765/health>
- 主检索接口：`POST http://localhost:8765/retrieve`

### 4. 启动 Web 管理界面

```bash
python web_ui.py
```

访问：<http://localhost:8001>

Web UI 用于文档扫描、分片预览、人工审核、入库、检索测试和系统管理。

## 文档入库

### Web 入库

1. 启动 `python web_ui.py`。
2. 在“文档入库”页输入服务器上的文件夹路径。
3. 点击“扫描文件”，系统递归查找 `.md`、`.docx`、`.pptx`、`.xlsx`、`.pdf`。
4. 递归扫描会跳过子目录 `images/`，避免把解析出的图片资源当成新文档。
5. 选择分片策略并预览分片。
6. 在审核面板中修改文本、删除图片或还原分片。
7. 点击“确认入库”。

### CLI 入库

默认扫描 [doc/](doc/) 目录：

```bash
python scripts/add_documents.py
```

常用参数请查看脚本帮助：

```bash
python scripts/add_documents.py --help
```

### 支持格式

| 格式 | 后缀 | 解析内容 | 图片处理 |
| --- | --- | --- | --- |
| Markdown | `.md` | Markdown 文本、标题结构 | 保留文档引用的本地图片 |
| Word | `.docx` | 段落、表格、标题 | 提取内嵌图片到 `doc/images/` |
| PowerPoint | `.pptx` | slide 标题、文本框、备注 | 提取 slide 内嵌图片 |
| Excel | `.xlsx` | 按工作表转换为 Markdown 表格/键值文本 | 尽量提取工作表图片 |
| PDF | `.pdf` | 可读取页面文本 | 提取页面内嵌图片 |

独立图片文件不会作为文档入库。图片只在被文档引用或内嵌时保留，并随命中分片作为图片路径返回。v0.1.0 不支持 OCR，也不支持图片内容语义检索。

## 分片策略

miniR 当前保留两类分片策略：

| 策略 | 说明 | 适用格式 |
| --- | --- | --- |
| `length` | 按字符长度切分，支持重叠比例 | 所有文本型格式 |
| `title` | 尽量按标题、页、slide 或 sheet 结构切分 | Markdown、Word、PPT、PDF；Excel 默认按 sheet |

Excel 默认按工作表分片，不做复杂表格区域识别。空文档、空 Excel sheet、损坏或加密 PDF 会跳过或输出明确日志。

## 检索能力

miniR 的检索链路由多路召回和融合排序组成：

```text
query
  -> BM25 关键词召回
  -> BGE-M3 Dense 向量召回
  -> BGE-M3 Sparse 向量召回
  -> RRF 融合
  -> 可选 BGE Reranker 精排
  -> 返回文本证据 + 来源 + 图片路径
```

### REST API

```bash
curl -X POST http://localhost:8765/retrieve ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"部署文档里怎么配置模型路径？\",\"top_k\":5,\"use_rerank\":true}"
```

响应格式面向 Agent 保持稳定：返回可引用文本、来源元数据，以及命中分片关联的图片路径。图片路径使用本地可定位路径，上层 Agent 或 LLM 客户端可以据此找到原始图片。

### Agent 回答约束

建议上层 Agent 使用 miniR 结果时遵守以下约束：

- 只能基于检索证据回答，不要编造未检索到的内容。
- 回答时标注关键来源，例如文件名、页码、slide 或 sheet。
- 如果证据不足，明确说明“当前知识库未检索到足够信息”。
- 如果结果包含图片路径，保留或展示图片路径，便于用户打开本地图片。

## Agent Skill

miniR 内置可复用的 Agent Skill：

```text
skill/minir-retrieval/
```

目录内容：

| 路径 | 作用 |
| --- | --- |
| `SKILL.md` | 给 Agent 的主说明 |
| `agents/openai.yaml` | OpenAI/Codex 风格工具配置示例 |
| `scripts/health_check.py` | 检查 miniR API 是否可用 |
| `scripts/retrieve.py` | 调用 `/retrieve` 的命令行工具 |
| `scripts/format_context.py` | 将检索结果格式化为 Agent 上下文 |
| `references/api.md` | API 契约说明 |
| `references/retrieval-contract.md` | 检索结果使用约束 |
| `references/examples.md` | 调用示例 |

可将该目录复制到 Codex、Claude Code 或其他支持本地 Skill 的 Agent 配置中。

## 文档管理

常用命令：

```bash
python scripts/manage_documents.py list
python scripts/manage_documents.py detail <document_id>
python scripts/manage_documents.py disable <document_id>
python scripts/manage_documents.py enable <document_id>
python scripts/manage_documents.py delete <document_id>
```

重建索引：

```bash
python scripts/rebuild_index.py
```

清空本地数据库和索引前，请确认 `doc/` 里的原始文档仍然保留。

## 配置

核心路径配置位于 [config/paths.json](config/paths.json)。常见目录：

| 路径 | 说明 | Git 状态 |
| --- | --- | --- |
| `doc/` | 本地待入库文档 | 仅保留 `.gitkeep` |
| `doc/images/` | 解析出的文档图片 | 忽略 |
| `faiss_index/` | FAISS、BM25、Sparse 索引文件 | 仅保留 `.gitkeep` |
| `modelscope_models/` | 本地模型文件 | 仅保留 `.gitkeep` |
| `rag_data.db` | SQLite 数据库 | 忽略 |

## 项目结构

```text
mini-rag/
├── fastapi_server.py        # REST 检索服务
├── web_ui.py                # Gradio 入库和管理界面
├── scripts/                 # 入库、索引和文档管理脚本
├── skill/minir-retrieval/   # Agent Skill 包
├── tests/                   # 解析和入库测试
├── config/                  # 模型和运行路径配置
├── doc/                     # 本地文档，Git 忽略
└── faiss_index/             # 生成的索引文件，Git 忽略
```

## 技术栈

- Python 3.12+
- FastAPI
- Gradio
- SQLite
- FAISS
- BGE-M3 Embedding
- BGE Reranker
- BM25
- python-docx / python-pptx / openpyxl / PyMuPDF

## 测试

```bash
python -B -m unittest discover -s tests
```

GitHub Actions 会运行同一套测试，并只安装测试需要的轻量解析依赖。

## 常见问题

### 为什么不支持独立图片入库？

第一版的图片能力目标是保留文档中的图片、预览图片、在检索结果中返回图片路径。独立图片没有 OCR 或多模态描述时很难被文本 query 召回，因此不会作为文档入库。

### 扫描 PDF 图片中的文字能检索吗？

不能。当前只提取 PDF 中可读取文本，不做 OCR。

### 同名不同格式的文档会被识别为同一个文档吗？

不会。文档去重使用相对路径和格式信息，不再只按文件名判断。

### 可以离线运行吗？

可以。模型、数据库和索引都在本地。首次准备模型时需要下载依赖和模型文件。

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。版本变化见 [CHANGELOG.md](CHANGELOG.md)。

## License

miniR 使用 [MIT License](LICENSE) 开源。
