"""文档入库流水线：加载 → 分块 → 向量化 → 写入向量库。"""
import logging
import uuid
from dataclasses import dataclass, field

from app.core.base import EmbeddingProvider
from app.ingestion.loader import Document, load_document
from app.ingestion.splitter import split_document
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """单文档入库结果。"""

    doc_id: str
    source: str
    chunks: int = 0
    errors: list[str] = field(default_factory=list)


def ingest_document(
    filename: str,
    content: bytes,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> IngestionResult:
    """入库单个文档：解析、分块、向量化并写入向量库。

    Args:
        filename: 原始文件名。
        content: 文件二进制内容。
        embedding_provider: Embedding 提供商实例。
        vector_store: 向量库封装实例。
        chunk_size: 分块大小（字符）。
        chunk_overlap: 分块重叠（字符）。

    Returns:
        IngestionResult：doc_id、来源、分块数与入库过程中的错误。
    """
    result = IngestionResult(doc_id=uuid.uuid4().hex, source=filename)

    try:
        document: Document = load_document(filename, content)
    except ValueError as exc:
        result.errors.append(str(exc))
        logger.warning("文档解析失败 %s: %s", filename, exc)
        return result

    chunks = split_document(document.text, chunk_size, chunk_overlap)
    if not chunks:
        result.errors.append("文档内容为空")
        return result

    try:
        embeddings = embedding_provider.embed(chunks)
        vector_store.upsert_document(
            doc_id=result.doc_id,
            source=filename,
            chunks=chunks,
            embeddings=embeddings,
        )
        result.chunks = len(chunks)
    except Exception as exc:  # 网络/提供商异常统一上报
        result.errors.append(str(exc))
        logger.exception("文档入库失败 %s", filename)

    return result
