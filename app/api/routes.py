"""API 路由：文档入库、查询、管理。"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.deps import (
    get_embedding_provider,
    get_llm_provider,
    get_vector_store,
)
from app.ingestion.pipeline import IngestionResult, ingest_document
from app.rag.framework_pipeline import FrameworkRAGPipeline
from app.rag.pipeline import RAGPipeline
from app.retrieval.vector_store import VectorStore
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, description="用户问题")
    top_k: int | None = Field(default=None, ge=1, le=20, description="检索片段数")
    mode: str = Field(default="custom", description="问答模式: custom=自研 / framework=LangChain 框架")

    @field_validator("mode")
    @classmethod
    def check_mode(cls, v: str) -> str:
        if v not in ("custom", "framework"):
            raise ValueError("mode 仅支持 custom 或 framework")
        return v


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/ingest", response_model=list[IngestionResult])
def ingest(
    files: list[UploadFile],
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
    embedding_provider=Depends(get_embedding_provider),
) -> list[IngestionResult]:
    """上传一个或多个文档入库，返回每个文档的处理结果。"""
    results: list[IngestionResult] = []
    for file in files:
        content = file.file.read()
        result = ingest_document(
            filename=file.filename or "unnamed",
            content=content,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        results.append(result)
    return results


@router.get("/documents")
def list_documents(
    vector_store: VectorStore = Depends(get_vector_store),
) -> dict:
    """列出已入库文档及各自的分块数。"""
    return {"documents": vector_store.list_documents()}


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: str,
    vector_store: VectorStore = Depends(get_vector_store),
) -> dict:
    """删除指定文档及其全部向量。"""
    vector_store.delete_document(doc_id)
    return {"status": "deleted", "doc_id": doc_id}


def _build_pipeline(
    req: QueryRequest,
    settings: Settings,
    vector_store: VectorStore,
    llm_provider,
    embedding_provider,
):
    """按 mode 构建对应 pipeline；框架模式构造失败时给出明确 500。"""
    if req.mode == "framework":
        try:
            return FrameworkRAGPipeline(
                settings=settings,
                embedding_provider=embedding_provider,
                vector_store=vector_store,
                top_k=req.top_k or settings.top_k,
            )
        except (RuntimeError, ValueError) as exc:  # 未装依赖 / 提供商或 Key 配置问题
            logger.warning("框架模式初始化失败: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RAGPipeline(
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        top_k=req.top_k or settings.top_k,
    )


@router.post("/query")
def query(
    req: QueryRequest,
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
    llm_provider=Depends(get_llm_provider),
    embedding_provider=Depends(get_embedding_provider),
) -> dict:
    """RAG 问答：检索相关片段并生成回答，附引用来源。

    mode 指定实现：custom 走自研 pipeline，framework 走 LangChain 编排；
    两种模式共享同一向量库，仅生成链路不同。
    """
    pipeline = _build_pipeline(req, settings, vector_store, llm_provider, embedding_provider)
    try:
        result = pipeline.answer(req.question)
    except Exception as exc:
        logger.exception("问答失败: %s", req.question)
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc
    return {"answer": result.answer, "sources": result.sources, "mode": req.mode}


def _sse(payload: dict) -> str:
    """构造一条 SSE 事件帧（单行 JSON，ensure_ascii=False 保留中文可读性）。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/query/stream")
def query_stream(
    req: QueryRequest,
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
    llm_provider=Depends(get_llm_provider),
    embedding_provider=Depends(get_embedding_provider),
) -> StreamingResponse:
    """流式 RAG 问答（SSE）：先推 sources，再逐段推 delta，最后推 done。"""
    pipeline = _build_pipeline(req, settings, vector_store, llm_provider, embedding_provider)

    def event_gen():
        try:
            for kind, payload in pipeline.answer_stream(req.question):
                if kind == "sources":
                    yield _sse({"type": "sources", "sources": payload})
                elif kind == "delta":
                    yield _sse({"type": "delta", "text": payload})
                elif kind == "done":
                    yield _sse({"type": "done", "mode": req.mode})
        except Exception as exc:
            logger.exception("流式问答失败: %s", req.question)
            yield _sse({"type": "error", "detail": f"问答失败: {exc}"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
