"""API 路由：文档入库、查询、管理。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.deps import (
    get_embedding_provider,
    get_llm_provider,
    get_vector_store,
)
from app.ingestion.pipeline import IngestionResult, ingest_document
from app.rag.pipeline import RAGPipeline
from app.retrieval.vector_store import VectorStore
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, description="用户问题")
    top_k: int | None = Field(default=None, ge=1, le=20, description="检索片段数")


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


@router.post("/query")
def query(
    req: QueryRequest,
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
    llm_provider=Depends(get_llm_provider),
    embedding_provider=Depends(get_embedding_provider),
) -> dict:
    """RAG 问答：检索相关片段并生成回答，附引用来源。"""
    pipeline = RAGPipeline(
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        top_k=req.top_k or settings.top_k,
    )
    try:
        result = pipeline.answer(req.question)
    except Exception as exc:
        logger.exception("问答失败: %s", req.question)
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc
    return {"answer": result.answer, "sources": result.sources}
