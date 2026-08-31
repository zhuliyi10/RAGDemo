"""检索器：查询向量化 + 语义检索。"""
from app.core.base import EmbeddingProvider
from app.retrieval.vector_store import VectorStore


class Retriever:
    """将用户问题向量化后在向量库中检索相关片段。"""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        """检索与查询最相关的 top_k 个片段。

        Returns:
            [{content, source, doc_id, chunk_index, similarity}, ...]，
            按相似度降序。
        """
        query_embedding = self._embedding_provider.embed([query])[0]
        return self._vector_store.query(query_embedding, top_k)
