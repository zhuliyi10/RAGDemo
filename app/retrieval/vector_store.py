"""向量存储：ChromaDB 持久化封装。"""
import logging
from pathlib import Path

from chromadb import PersistentClient
from chromadb.api.models.Collection import Collection

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "rag_docs"


class VectorStore:
    """基于 ChromaDB PersistentClient 的向量存储。

    collection 的元数据约定：
    - document: chunk 正文
    - ids: "{doc_id}::{chunk_index}"，保证 doc_id 维度可整体删除
    - metadatas: {doc_id, source, chunk_index}
    """

    def __init__(self, persist_dir: Path, collection_name: str = COLLECTION_NAME):
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = PersistentClient(path=str(persist_dir))
        self._collection: Collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_document(
        self,
        doc_id: str,
        source: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        """写入/覆盖一个文档的全部 chunk。"""
        ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": doc_id, "source": source, "chunk_index": i}
            for i in range(len(chunks))
        ]
        self._collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("文档 %s 已写入 %d 个 chunk", doc_id, len(chunks))

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[dict]:
        """语义检索，返回按相似度降序的命中列表。"""
        if self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return self._to_hits(result)

    def delete_document(self, doc_id: str) -> None:
        """删除一个文档的全部 chunk。"""
        hits = self._collection.get(where={"doc_id": doc_id}, include=[])
        if hits["ids"]:
            self._collection.delete(ids=hits["ids"])
            logger.info("文档 %s 已删除 %d 个 chunk", doc_id, len(hits["ids"]))

    def list_documents(self) -> list[dict]:
        """列出所有已入库文档及分块数。"""
        hits = self._collection.get(include=["metadatas"])
        stats: dict[str, dict] = {}
        for meta in hits["metadatas"]:
            doc_id = meta["doc_id"]
            entry = stats.setdefault(
                doc_id,
                {"doc_id": doc_id, "source": meta["source"], "chunks": 0},
            )
            entry["chunks"] += 1
        return sorted(stats.values(), key=lambda e: e["doc_id"])

    def count(self) -> int:
        """返回当前 chunk 总数。"""
        return self._collection.count()

    @staticmethod
    def _to_hits(result: dict) -> list[dict]:
        """将 ChromaDB 查询结果转换为统一结构。"""
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits = []
        for chunk_id, doc, meta, distance in zip(ids, documents, metadatas, distances):
            hits.append(
                {
                    "chunk_id": chunk_id,
                    "content": doc,
                    "doc_id": meta["doc_id"],
                    "source": meta["source"],
                    "chunk_index": meta["chunk_index"],
                    # cosine 距离转相似度
                    "similarity": round(1 - distance, 4),
                }
            )
        return hits


def create_vector_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    return VectorStore(settings.chroma_dir)
