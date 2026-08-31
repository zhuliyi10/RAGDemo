"""检索器与 RAG 流水线测试：使用 mock Embedding/LLM + 临时 ChromaDB。"""
import hashlib

from app.core.base import EmbeddingProvider, LLMProvider
from app.ingestion.pipeline import ingest_document
from app.rag.pipeline import RAGPipeline
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import VectorStore

DIM = 512


class HashEmbeddingProvider(EmbeddingProvider):
    """基于字符哈希的确定性向量，语义相近文本向量相近（用于测试）。"""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * DIM
            for ch in text:
                h = int(hashlib.md5(ch.encode("utf-8")).hexdigest()[:8], 16)
                vec[h % DIM] += 1.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vectors.append([round(v / norm, 6) for v in vec])
        return vectors


class EchoLLMProvider(LLMProvider):
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        return f"基于上下文的回答: {user_prompt[:20]}"


def make_store(tmp_path) -> VectorStore:
    return VectorStore(persist_dir=tmp_path / "chroma_test")


class TestRetriever:
    def test_top_k_ordering(self, tmp_path):
        store = make_store(tmp_path)
        emb = HashEmbeddingProvider()
        ingest_document(
            "a.txt",
            "苹果是一种水果。苹果富含维生素。".encode("utf-8"),
            emb,
            store,
            chunk_size=200,
            chunk_overlap=0,
        )
        ingest_document(
            "b.txt",
            "汽车是一种交通工具。汽车使用汽油。".encode("utf-8"),
            emb,
            store,
            chunk_size=200,
            chunk_overlap=0,
        )

        retriever = Retriever(emb, store)
        hits = retriever.retrieve("苹果有什么特点？", top_k=2)
        assert len(hits) == 2
        # 苹果相关片段应排在汽车之前
        assert hits[0]["source"] == "a.txt"
        assert hits[0]["similarity"] >= hits[1]["similarity"]

    def test_query_on_empty_store(self, tmp_path):
        store = make_store(tmp_path)
        retriever = Retriever(HashEmbeddingProvider(), store)
        assert retriever.retrieve("任何问题", top_k=3) == []

    def test_delete_document(self, tmp_path):
        store = make_store(tmp_path)
        emb = HashEmbeddingProvider()
        result = ingest_document(
            "a.txt",
            "苹果是一种水果。".encode("utf-8"),
            emb,
            store,
            chunk_size=100,
            chunk_overlap=0,
        )
        assert result.chunks == 1
        assert store.count() == 1
        store.delete_document(result.doc_id)
        assert store.count() == 0
        assert store.list_documents() == []


class TestRAGPipeline:
    def test_answer_with_context(self, tmp_path):
        store = make_store(tmp_path)
        emb = HashEmbeddingProvider()
        ingest_document(
            "a.txt",
            "苹果是一种水果，富含维生素C。".encode("utf-8"),
            emb,
            store,
            chunk_size=200,
            chunk_overlap=0,
        )

        pipeline = RAGPipeline(EchoLLMProvider(), emb, store, top_k=1)
        result = pipeline.answer("苹果是什么？")
        assert result.answer.startswith("基于上下文的回答")
        assert len(result.sources) == 1
        assert result.sources[0]["source"] == "a.txt"

    def test_answer_without_context(self, tmp_path):
        store = make_store(tmp_path)
        pipeline = RAGPipeline(EchoLLMProvider(), HashEmbeddingProvider(), store)
        result = pipeline.answer("知识库为空时的问题")
        assert "无法回答" in result.answer
        assert result.sources == []
