# miniR

轻量级、自托管的 RAG 知识库检索后端。

miniR 只负责文档入库、索引构建、混合检索和结果召回，不内置 LLM 调用。它更适合作为 AI Agent、聊天系统或内部工具的“知识库检索工具”，由上层应用决定如何把检索结果交给模型生成最终答案。

---

## 核心定位

- **面向 Agent 集成**：通过 REST API 返回整理后的文本证据，方便作为 Tool/Skill 直接交给 LLM。
- **纯检索后端**：不绑定任何 LLM、Agent 框架或 Prompt 编排方式。
- **混合检索**：BM25 + BGE-M3 Dense + BGE-M3 Sparse，经 RRF 融合后可选 BGE Reranker 精排。
- **本地自托管**：FAISS + SQLite，本地模型、本地文档、本地索引。
- **文档管理**：支持文档启用、停用、删除和索引同步。
- **可视化入库**：Gradio Web UI 支持扫描、分片预览、人工审核、图片预览和入库。

---

## Agent 集成

### 调用方式

启动 API 服务后，Agent 通过 `POST /retrieve` 调用 miniR：

```bash
curl -s -X POST http://localhost:8765/retrieve \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"$USER_QUERY\",\"top_k\":5,\"use_rerank\":true}"
```

请求使用 JSON，响应为 `text/plain; charset=utf-8`，返回可直接放进 LLM 上下文的证据文本：

```text
检索问题：DDPG 算法原理
命中片段数：1
检索耗时：0.532s

以下内容是知识库召回的证据片段，可直接作为 LLM 上下文使用。回答时应优先依据这些证据；证据不足时请明确说明。

[证据 1]
文档：ddpg_guide.md
标题：DDPG 算法原理
分片ID：12
相关性分数：0.8200
内容：
文档片段内容...
```

### Agent 工具描述建议

可以把 miniR 描述为一个知识库检索工具：

```text
当用户问题可能需要本地知识库信息时，先调用 miniR 检索工具。
工具返回整理后的证据文本及来源信息。回答时优先依据检索结果；
如果结果不足或没有命中，应明确说明知识库中没有足够依据。
```

推荐流程：

1. Agent 接收用户问题。
2. 调用 `POST /retrieve`，传入原始问题或改写后的检索 query。
3. 将返回的纯文本证据整体作为上下文交给 LLM。
4. LLM 基于证据回答，并在需要时引用文档名或标题。

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

建议使用 Python 3.12 环境。

### 2. 下载模型

将模型放到 `modelscope_models/` 下：

```bash
modelscope download --model BAAI/bge-m3 --local_dir modelscope_models/bge-m3
modelscope download --model BAAI/bge-reranker-v2-m3 --local_dir modelscope_models/bge-reranker-v2-m3
```

默认路径来自 [config/paths.json](config/paths.json)：

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
- Agent 主接口：`POST http://localhost:8765/retrieve`

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
3. 点击“扫描文件”，系统递归查找 `.md` 和 `.docx`。
4. 选择分片策略并预览分片。
5. 在审核面板中修改文本、删除图片或还原分片。
6. 点击“确认入库”。

### CLI 入库

```bash
python scripts/add_documents.py --chunk-strategy title
```

或使用长度分片：

```bash
python scripts/add_documents.py --chunk-strategy length --chunk-size 512 --overlap-ratio 0.1
```

默认扫描 [doc/](doc/) 目录，支持 Markdown 和 Word 文档。

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

可通过请求参数控制返回数量和是否启用 Rerank：

```json
{
  "query": "问题内容",
  "top_k": 5,
  "use_rerank": true
}
```

---

## API 接口

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/retrieve` | POST | Agent/Skill/Tool 推荐使用的主检索接口，返回纯文本证据 |
| `/health` | GET | 健康检查 |

`/retrieve` 请求体：

```json
{
  "query": "问题内容",
  "top_k": 5,
  "use_rerank": true
}
```

`top_k` 范围为 1-20，`use_rerank` 默认为 `true`。

---

## 文档格式

### Markdown

推荐使用标准 Markdown 标题和图片语法：

```markdown
# 1 概述
正文内容...

![架构图](images/architecture.png)
```

图片路径会按文档所在目录解析，并在检索结果中返回。

### Word `.docx`

Word 标题样式会被转换为 Markdown 标题层级。文档内图片会提取到同目录 `images/` 文件夹，并在文本中使用占位符标记：

```text
<<IMAGE:a3f7b2c1>>
```

Web 审核界面会把占位符渲染为图片标签，检索结果中会尽量内联展示图片。

---

## 分片策略

### 标题分片

适合结构清晰的 Markdown 或 Word 文档。系统按标题层级切分，每个标题下的正文形成一个 chunk。

```bash
python scripts/add_documents.py --chunk-strategy title
```

### 长度分片

适合论文、课件、长段落文本等标题结构不稳定的文档。

```bash
python scripts/add_documents.py --chunk-strategy length --chunk-size 512 --overlap-ratio 0.1
```

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
├── config/
│   └── paths.json
├── doc/                       # 默认源文档目录
├── faiss_index/               # 默认索引目录
├── modelscope_models/         # 默认模型目录
└── requirements.txt
```

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
| 文档解析 | python-docx + lxml |
| 存储 | SQLite |

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
