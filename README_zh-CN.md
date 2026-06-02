# miniR: Local RAG Retrieval Backend for AI Agents

[English](README.md) | [简体中文](README_zh-CN.md)

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![FAISS](https://img.shields.io/badge/vector-FAISS-orange)
![License](https://img.shields.io/badge/license-MIT-green)

miniR 是一个轻量级、自托管的 RAG 检索后端，面向 AI Agent、聊天系统和内部知识库工具。它可以入库 Markdown、Word、PPT、Excel 和 PDF 文档，构建本地混合索引，并通过 REST API 或 Agent Skill 返回可直接用于回答的证据上下文。

![miniR 文档入库界面](assets/screenshots/web-ui-import.svg)

## 为什么是 miniR

miniR 只负责文档解析、分片、索引、检索和证据返回，不内置 LLM 调用。上层 Agent 可以通过 `/retrieve` 拿到稳定的文本证据和相关本地图片路径，再自行交给模型生成最终答案。

建议 GitHub topics：`rag`、`retrieval-augmented-generation`、`ai-agent`、`local-first`、`fastapi`、`faiss`、`hybrid-search`、`document-processing`、`knowledge-base`、`python`。

- 支持 `.md`、`.docx`、`.pptx`、`.xlsx`、`.pdf` 多格式入库
- 保留文档内引用或内嵌图片，支持 Web UI 预览
- 使用 SQLite 存储元数据，FAISS 存储向量索引
- 支持 BM25、Dense、Sparse 和可选 Reranker 的混合检索
- 支持入库前分片预览、人工审核、图片删除和确认入库
- 内置 `skill/minir-retrieval`，便于 Codex、Claude Code 等 Agent 接入

## 截图

![miniR 检索结果示例](assets/screenshots/retrieval-output.svg)

## 快速开始

建议使用 Python 3.12 或更新版本。当前项目已在本地 conda 环境中验证。

```bash
pip install -r requirements.txt
```

下载 Embedding 和 Reranker 模型：

```bash
modelscope download --model BAAI/bge-m3 --local_dir modelscope_models/bge-m3
modelscope download --model BAAI/bge-reranker-v2-m3 --local_dir modelscope_models/bge-reranker-v2-m3
```

启动检索 API：

```bash
python fastapi_server.py
```

API 文档地址：<http://localhost:8765/docs>

启动 Web 管理界面：

```bash
python web_ui.py
```

访问地址：<http://localhost:8001>

## 文档入库

推荐使用 Web UI 入库，因为它支持目录扫描、分片预览、图片预览和人工确认。

CLI 默认扫描 `doc/` 目录：

```bash
python scripts/add_documents.py
```

支持格式：

| 格式 | 后缀 | 说明 |
| --- | --- | --- |
| Markdown | `.md` | 保留 Markdown 文本和本地引用图片 |
| Word | `.docx` | 提取段落、表格和内嵌图片 |
| PowerPoint | `.pptx` | 提取幻灯片文本、备注和内嵌图片 |
| Excel | `.xlsx` | 将工作表转换为 Markdown 风格表格文本 |
| PDF | `.pdf` | 提取可读取页面文本和页面内图片 |

独立图片文件不会作为文档入库。图片只在被文档引用或内嵌时保留。v0.1.0 不做 OCR，也不做图片内容语义检索。

## 检索 API

```bash
curl -X POST http://localhost:8765/retrieve ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"部署文档里怎么配置模型路径？\",\"top_k\":5}"
```

响应格式面向 Agent 保持稳定：返回可引用文本、来源元数据，以及命中分片关联的图片路径。

## Agent Skill

miniR 内置可复用的 Agent Skill：

```text
skill/minir-retrieval/
```

可以把这个目录复制或引用到 Codex、Claude Code 等支持 Skill 的 Agent 中。目录内包含使用说明、API 契约和健康检查、检索格式化脚本。

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

## 测试

```bash
python -B -m unittest discover -s tests
```

GitHub Actions 会运行同一套测试，并只安装测试需要的轻量解析依赖。

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。版本变化见 [CHANGELOG.md](CHANGELOG.md)。

## License

miniR 使用 [MIT License](LICENSE) 开源。
