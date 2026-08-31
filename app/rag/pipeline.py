"""RAG 主流程：检索 → 增强 → 生成。"""
from dataclasses import dataclass, field

from app.core.base import EmbeddingProvider, LLMProvider
from app.generation.generator import Generator
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import VectorStore

NO_CONTEXT_ANSWER = "根据现有资料无法回答该问题（知识库中未检索到相关内容）。"


@dataclass
class RAGResult:
    """RAG 问答结果。"""

    answer: str
    sources: list[dict] = field(default_factory=list)


class RAGPipeline:
    """编排完整的 RAG 问答流程。"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        top_k: int = 4,
    ):
        self._retriever = Retriever(embedding_provider, vector_store)
        self._generator = Generator(llm_provider)
        self._top_k = top_k

    def answer(self, question: str, top_k: int | None = None) -> RAGResult:
        """回答问题，返回答案与引用来源。"""
        k = top_k or self._top_k
        hits = self._retriever.retrieve(question, top_k=k)
        if not hits:
            return RAGResult(answer=NO_CONTEXT_ANSWER)

        answer = self._generator.generate(question, hits)
        sources = [
            {
                "source": hit["source"],
                "content": hit["content"],
                "similarity": hit["similarity"],
            }
            for hit in hits
        ]
        return RAGResult(answer=answer, sources=sources)
