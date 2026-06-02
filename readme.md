# miniR

轻量级、自托管的 RAG 知识库检索后端，面向 AI Agent、聊天系统和内部知识库工具。

miniR 只负责文档入库、索引构建、混合检索和证据召回，不内置 LLM 调用。上层 Agent 可以通过 REST API 或内置 Skill 调用 miniR，将检索结果交给模型生成最终答案。

```text
本地文档 -> 解析/分片 -> SQLite + FAISS + BM25 + Sparse -> /retrieve -> Agent/LLM
```

---

## 核心能力

- **多格式文档入库**：支持 Markdown、Word、PowerPoint、Excel、PDF；图片仅作为文档内引用或内嵌资源保留。
- **文本优先解析**：Office/PDF 会提取可读取文本和文档内图片；扫描 PDF 不做 OCR，图片内容不做语义识别。
- **混合检索**：BM25 + BGE-M3 Dense + BGE-M3 Sparse，经 RRF 融合后可选 BGE Reranker 精排。
- **本地自托管**：SQLite 存储元数据，FAISS 存储向量，模型和索引均可本地离线运行。
- **可视化入库**：Gradio Web UI 支持目录扫描、分片预览、人工审核、图片预览和确认入库。
- **文档管理**：支持文档列表、启用/停用、删除、统计、索引同步和一键清库。
- **Agent 友好**：提供 REST API 和 `skill/minir-retrieval`，Codex、Claude Code 等 Agent 可直接接入。

---

## 接入方式

| 场景 | 方式 |
| --- | --- |
| Agent/LLM 工具调用 | `POST /retrieve` 返回纯文本证据 |
| Codex / Claude Code 等 AI 编程工具 | 使用内置 `skill/minir-retrieval` |
| 本地管理和人工审核 | 启动 `web_ui.py` 使用 Gradio Web UI |
| 批量入库和维护 | 使用 `scripts/add_documents.py`、`scripts/manage_documents.py` |

---

## 快速开始

### 1. 安装依赖

建议使用 Python 3.12 环境。

```bash
pip install -r requirements.txt
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

- API 文档：http://localhost:8765/docs
- 健康检查：http://localhost:8765/health
- 主检索接口：`POST http://localhost:8765/retrieve`

### 4. 启动 Web 管理界面

```bash
python web_ui.py
```

访问：http://localhost:8001

Web UI 用于文档扫描、分片预览、人工审核、入库、检索测试和系统管理。

---

## 文档入库

### Web 入库

1. 启动 `python web_ui.py`。
2. 在“文档入库”页输入服务器上的文档目录。
3. 点击“扫描文件”，系统递归查找 `.md`、`.docx`、`.pptx`、`.xlsx`、`.pdf`。
4. 递归扫描会跳过子目录 `images/`，避免把解析出的图片资源当成新文档。
5. 选择分片策略并预览分片。
6. 在审核面板中修改文本、删除图片或还原分片。
7. 点击“确认入库”。

### CLI 入库

默认扫描 [doc/](doc/) 目录。

```bash
python scripts/add_documents.py --chunk-strategy title
```

或使用长度分片：

```bash
python scripts/add_documents.py --chunk-strategy length --chunk-size 512 --overlap-ratio 0.1
```

---

## 支持格式

当前版本采用纯 Python、文本优先解析。图片会作为文档内资源保留并在检索结果中返回本地绝对路径；图片文件本身不会作为独立文档入库。

| 格式 | 支持情况 |
| --- | --- |
| Markdown `.md` | 支持标题结构和 Markdown/HTML 图片引用 |
| Word `.docx` | 支持标题样式、段落文本和内嵌图片提取 |
| PowerPoint `.pptx` | 按 slide 提取标题、文本框、备注和内嵌图片 |
| Excel `.xlsx` | 按工作表提取非空单元格并转换为 Markdown 表格，保留工作表图片 |
| PDF `.pdf` | 按页提取可复制文本和页面图片；扫描版 PDF 不做 OCR |

Word、PPT、Excel、PDF 内嵌图片会提取到文档所在目录的 `images/` 文件夹，并在文本中使用占位符标记：

```text
<<IMAGE:a3f7b2c1>>
```

Web 审核界面会把占位符渲染为图片标签。检索召回时，图片路径会转换为本地绝对路径，方便上层 Agent/LLM 定位文件。

---

## 分片策略

### 标题分片

适合结构清晰的 Markdown、Word、PPT、Excel 或 PDF 文档。系统按标题、页、slide、sheet 等结构切分，每个结构单元形成一个 chunk。

```bash
python scripts/add_documents.py --chunk-strategy title
```

### 长度分片

适合论文、课件、长段落文本等标题结构不稳定的文档。

```bash
python scripts/add_documents.py --chunk-strategy length --chunk-size 512 --overlap-ratio 0.1
```

---

## 检索能力

miniR 的检索流程：

```text
用户查询
  -> BM25 全文检索
  -> Dense 向量检索（BGE-M3）
  -> Sparse 词权重检索（BGE-M3）
  -> RRF 融合
  -> 可选 Reranker 精排
  -> Top-K 文档片段
```

`POST /retrieve` 请求体：

```json
{
  "query": "问题内容",
  "top_k": 5,
  "use_rerank": true
}
```

响应为 `text/plain; charset=utf-8`，可直接放进 LLM 上下文：

```text
检索问题：DDPG 算法原理
命中片段数：1
检索耗时：0.532s

[证据 1]
文档：ddpg_guide.md
标题：DDPG 算法原理
分片ID：12
相关性分数：0.8200
内容：
文档片段内容...
```

调用示例：

```bash
curl -s -X POST http://localhost:8765/retrieve \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"DDPG 算法原理\",\"top_k\":5,\"use_rerank\":true}"
```

---

## Agent Skill

仓库内置 [skill/minir-retrieval](skill/minir-retrieval)，用于让 Codex、Claude Code 或其他 Agent 直接接入 miniR。

```text
skill/minir-retrieval/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── health_check.py
│   ├── retrieve.py
│   └── format_context.py
└── references/
    ├── api.md
    ├── retrieval-contract.md
    └── examples.md
```

Agent 可以直接读取 `SKILL.md`，或把整个 `skill/minir-retrieval` 目录复制到自己的 skill/工具目录中。

检查服务状态：

```bash
python skill/minir-retrieval/scripts/health_check.py
```

检索证据：

```bash
python skill/minir-retrieval/scripts/retrieve.py --query "DDPG 算法原理" --top-k 5 --rerank
```

使用自定义服务地址：

```bash
python skill/minir-retrieval/scripts/retrieve.py \
  --base-url http://localhost:8765 \
  --query "设备调试步骤" \
  --top-k 8
```

Skill 脚本只依赖 Python 标准库，便于不同 Agent 环境复用。miniR 服务本身仍需先通过 `python fastapi_server.py` 启动。

---

## Agent 回答约束

可以把 miniR 描述为一个知识库检索工具：

```text
当用户问题可能需要本地知识库信息时，先调用 miniR 检索工具。
工具返回整理后的证据文本及来源信息。回答时优先依据检索结果；
如果结果不足或没有命中，应明确说明知识库中没有足够依据。
```

推荐流程：

1. Agent 接收用户问题。
2. 调用 `POST /retrieve` 或 `skill/minir-retrieval/scripts/retrieve.py`。
3. 将返回证据整体作为上下文交给 LLM。
4. LLM 基于证据回答，并在需要时引用文档名或标题。
5. 如果返回图片路径，将其视为本地文件路径；不要在未读取图片的情况下推断图片内容。

---

## 文档管理

Web UI 支持：

- 查看文档列表和分片数量
- 启用或停用文档
- 删除文档并同步 FAISS、Sparse、BM25 和 SQLite 记录
- 查看系统统计
- 清空数据库和索引

CLI 管理工具：

```bash
python scripts/manage_documents.py list
python scripts/manage_documents.py detail <corpus_id>
python scripts/manage_documents.py toggle <corpus_id>
python scripts/manage_documents.py delete <corpus_id> -y
python scripts/manage_documents.py stats
```

---

## 配置

主要配置文件：[config/paths.json](config/paths.json)

```json
{
  "project_root": "${PROJECT_ROOT}",
  "md_directories": ["doc"],
  "faiss_index_path": "faiss_index",
  "model_path": "modelscope_models/bge-m3",
  "reranker_path": "modelscope_models/bge-reranker-v2-m3",
  "db_path": "rag_data.db"
}
```

说明：

- `md_directories`：默认文档目录，可配置多个目录。
- `faiss_index_path`：FAISS、Sparse、BM25 等索引文件目录。
- `db_path`：SQLite 数据库路径。
- `model_path`：BGE-M3 embedding 模型路径。
- `reranker_path`：BGE reranker 模型路径。

---

## 项目结构

```text
miniR/
├── fastapi_server.py          # FastAPI Agent 检索接口
├── web_ui.py                  # Gradio 管理界面
├── scripts/
│   ├── add_documents.py       # 文档入库、解析、分片、向量生成
│   ├── bm25_indexer.py        # BM25 索引
│   ├── config_manager.py      # 路径配置
│   ├── db_manager.py          # 数据库入口
│   ├── db_manager_sqlite.py   # SQLite 实现
│   ├── doc_retriever.py       # 混合检索器
│   ├── manage_documents.py    # 文档管理 CLI
│   ├── rebuild_index.py       # 索引重建
│   └── reranker.py            # BGE Reranker
├── skill/
│   └── minir-retrieval/       # Agent Skill 接入包
├── tests/                     # 解析层回归测试
├── config/
│   └── paths.json
├── doc/                       # 默认源文档目录
├── faiss_index/               # 默认索引目录
├── modelscope_models/         # 默认模型目录
└── requirements.txt
```

---

## 技术栈

| 类别 | 技术 |
| --- | --- |
| API | FastAPI + Uvicorn |
| Web UI | Gradio |
| 向量索引 | FAISS |
| Embedding | BGE-M3 / FlagEmbedding |
| Sparse 检索 | BGE-M3 lexical weights |
| 全文检索 | rank_bm25 + jieba |
| Rerank | BGE-Reranker-v2-M3 |
| 文档解析 | python-docx + python-pptx + openpyxl + PyMuPDF + lxml |
| 存储 | SQLite |

---

## 测试

```bash
python -B -m unittest discover -s tests
```

Windows 示例：

```powershell
D:\anaconda3\envs\Ben_llm\python.exe -B -m unittest discover -s tests
```

---

## 常见问题

### 中文显示乱码

项目文件使用 UTF-8 编码。Windows PowerShell 读取中文文件时建议显式指定编码：

```powershell
Get-Content -Encoding UTF8 readme.md
```

### 修改文档后检索不到新内容

重新入库或执行索引重建：

```bash
python scripts/rebuild_index.py
```

如果 API 服务已经启动，重建索引后建议重启 API 服务，让检索器重新加载索引。

### 同名不同格式文档如何处理

miniR 按文件路径判断是否已入库。同名但格式不同的文档，例如 `manual.docx` 和 `manual.pdf`，会作为不同文档处理。
