"""
FastAPI 服务
功能：提供面向 Agent/Skill/Tool 调用的知识库检索接口
"""

import os
import sys
import time
from typing import Optional

from pydantic import BaseModel, Field

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORKSPACE_ROOT)

from scripts.doc_retriever import DocRetriever

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import PlainTextResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("警告: FastAPI 未安装，API 服务不可用")
    print("请运行: pip install fastapi uvicorn")


class RetrieveRequest(BaseModel):
    query: str = Field(..., description="用户问题或改写后的检索查询")
    top_k: int = Field(5, ge=1, le=20, description="返回证据片段数量")
    use_rerank: bool = Field(True, description="是否启用 BGE Reranker 精排")


class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict


if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="miniR 检索服务",
        description="面向 Agent/Skill/Tool 调用的本地知识库检索服务",
        version="3.1.0",
    )

    doc_retriever: Optional[DocRetriever] = None

    def _reset_retrieval_service():
        global doc_retriever
        doc_retriever = DocRetriever()

    def _normalize_text(value: str) -> str:
        return "\n".join(line.rstrip() for line in str(value or "").strip().splitlines())

    def _format_score(doc: dict) -> str:
        if "rerank_score" not in doc:
            return ""
        try:
            return f"相关性分数：{float(doc['rerank_score']):.4f}\n"
        except (TypeError, ValueError):
            return f"相关性分数：{doc['rerank_score']}\n"

    def _format_images(images) -> str:
        if not images:
            return ""
        lines = ["图片："]
        for image in images[:5]:
            if isinstance(image, dict):
                path = image.get("abs_path") or image.get("path") or str(image)
            else:
                path = str(image)
            lines.append(f"- {path}")
        if len(images) > 5:
            lines.append(f"- 另有 {len(images) - 5} 张图片未列出")
        return "\n".join(lines) + "\n"

    def _format_retrieve_output(query: str, docs: list[dict], elapsed: float) -> str:
        query = _normalize_text(query)
        if not docs:
            return (
                f"检索问题：{query}\n"
                "检索结果：未在知识库中找到足够相关的证据片段。\n"
                "回答建议：请说明当前知识库没有提供足够依据，不要编造来源。\n"
            )

        parts = [
            f"检索问题：{query}",
            f"命中片段数：{len(docs)}",
            f"检索耗时：{elapsed:.3f}s",
            "",
            "以下内容是知识库召回的证据片段，可直接作为 LLM 上下文使用。回答时应优先依据这些证据；证据不足时请明确说明。",
        ]

        for idx, doc in enumerate(docs, 1):
            meta = doc.get("meta", {}) or {}
            doc_name = meta.get("doc_name") or meta.get("source") or "Unknown"
            title = meta.get("title") or "无标题"
            content = _normalize_text(doc.get("content", ""))
            images_text = _format_images(meta.get("images", []))

            parts.extend([
                "",
                f"[证据 {idx}]",
                f"文档：{doc_name}",
                f"标题：{title}",
                f"分片ID：{doc.get('doc_id', '')}",
                _format_score(doc).rstrip(),
                "内容：",
                content,
            ])
            if images_text:
                parts.append(images_text.rstrip())

        return "\n".join(part for part in parts if part is not None)

    @app.on_event("startup")
    async def startup_event():
        print("=" * 60)
        print("正在初始化 miniR 检索服务...")
        print("=" * 60)
        try:
            _reset_retrieval_service()
            print("检索服务初始化完成")
        except Exception as e:
            print(f"检索服务初始化失败: {e}")
            import traceback
            traceback.print_exc()

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        components = {
            "doc_retriever": "ok" if doc_retriever is not None else "error",
        }
        status = "healthy" if all(v == "ok" for v in components.values()) else "degraded"
        return HealthResponse(
            status=status,
            version="3.1.0",
            components=components,
        )

    @app.post("/retrieve", response_class=PlainTextResponse)
    async def retrieve(request: RetrieveRequest):
        """
        Agent 主检索接口。

        输入仍使用 JSON，输出为 text/plain 证据文本，便于 Tool/Skill 直接交给 LLM。
        """
        if doc_retriever is None:
            raise HTTPException(status_code=503, detail="检索服务未初始化")

        query = request.query.strip()
        if not query:
            raise HTTPException(status_code=400, detail="query 不能为空")

        try:
            start_time = time.time()
            print("\n" + "=" * 60)
            print(f"[API] 收到检索请求: {query}")
            print("=" * 60)

            docs = doc_retriever.retrieve(
                query=query,
                top_k=request.top_k,
                use_rerank=request.use_rerank,
            )
            elapsed = time.time() - start_time
            print(f"[API] 检索完成，返回 {len(docs)} 个片段，总耗时 {elapsed:.3f}s")

            return PlainTextResponse(
                content=_format_retrieve_output(query, docs, elapsed),
                media_type="text/plain; charset=utf-8",
            )

        except HTTPException:
            raise
        except Exception as e:
            print(f"[API] 检索失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/", response_class=PlainTextResponse)
    async def root():
        return PlainTextResponse(
            content="miniR 检索服务已启动。Agent 主接口：POST /retrieve",
            media_type="text/plain; charset=utf-8",
        )

else:
    class DummyApp:
        pass
    app = DummyApp()


def main():
    if not FASTAPI_AVAILABLE:
        print("错误: FastAPI 未安装，无法启动服务")
        print("请运行: pip install fastapi uvicorn")
        return

    print("=" * 60)
    print("启动 miniR FastAPI 检索服务")
    print("=" * 60)
    print("API 文档: http://localhost:8765/docs")
    print("健康检查: http://localhost:8765/health")
    print("Agent 主接口: POST http://localhost:8765/retrieve")
    print("=" * 60)

    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8765,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
