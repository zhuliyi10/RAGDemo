"""框架模式：基于 LangChain 的 RAG 流程，与自研 pipeline 形成对照。

检索环节复用自研 Retriever（两种模式共享同一 ChromaDB 知识库），
Prompt 组装与 LLM 调用改由 LangChain 的 ChatModel + LCEL 链完成，
便于在相同知识库、相同约束下横向对比两种实现的回答效果。

LangChain 为可选依赖，未安装时在构造阶段抛出带安装指引的错误，
保证服务在不装框架依赖时仍可正常启动并使用自研模式。
"""
from collections.abc import Iterator

from pydantic import SecretStr

from app.config import Settings
from app.core.base import EmbeddingProvider
from app.generation.generator import SYSTEM_PROMPT
from app.rag.pipeline import NO_CONTEXT_ANSWER, RAGResult
from app.retrieval.retriever import Retriever
from app.retrieval.vector_store import VectorStore

INSTALL_HINT = (
    "框架模式需要 LangChain 依赖，请先安装: "
    "pip install langchain-core langchain-openai langchain-anthropic"
)


def _create_chat_model(settings: Settings):
    """按配置创建 LangChain ChatModel（提供商与自研模式一一对应）。

    openai / zhipu / ollama 均走 OpenAI 兼容接口（ChatOpenAI），
    anthropic 使用官方 langchain-anthropic 集成。
    """
    provider = settings.llm_provider
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            api_key=SecretStr(settings.anthropic_api_key),
            base_url=settings.anthropic_base_url,
        )
    if provider == "ollama":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=SecretStr("ollama"),  # 本地服务不校验 Key
            base_url=f"{settings.ollama_base_url}/v1",
        )
    if provider == "zhipu":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=SecretStr(settings.zhipu_api_key),
            base_url=settings.zhipu_openai_base_url,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=SecretStr(settings.openai_api_key),
        )
    raise ValueError(f"不支持的 LLM 提供商: {provider}")


class FrameworkRAGPipeline:
    """用 LangChain 编排的 RAG 流程：检索复用自研组件，生成走 LCEL 链。"""

    def __init__(
        self,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        top_k: int = 4,
    ):
        try:
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError as exc:
            raise RuntimeError(INSTALL_HINT) from exc

        self._retriever = Retriever(embedding_provider, vector_store)
        self._top_k = top_k

        # System Prompt 与自研模式完全一致，保证两种模式的对比是公平的
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "【上下文】\n{context}\n\n【问题】\n{question}"),
            ]
        )
        self._chain = prompt | _create_chat_model(settings) | StrOutputParser()

    def answer(self, question: str, top_k: int | None = None) -> RAGResult:
        """与 RAGPipeline.answer 语义一致：返回答案与引用来源。"""
        k = top_k or self._top_k
        hits = self._retriever.retrieve(question, top_k=k)
        if not hits:
            return RAGResult(answer=NO_CONTEXT_ANSWER)

        context = "\n\n".join(
            f"[片段 {i + 1}] 来源: {hit['source']}\n{hit['content']}"
            for i, hit in enumerate(hits)
        )
        answer = self._chain.invoke({"context": context, "question": question})
        sources = [
            {
                "source": hit["source"],
                "content": hit["content"],
                "similarity": hit["similarity"],
            }
            for hit in hits
        ]
        return RAGResult(answer=answer, sources=sources)

    def answer_stream(self, question: str, top_k: int | None = None) -> Iterator[tuple]:
        """流式问答，事件协议与 RAGPipeline.answer_stream 完全一致。"""
        k = top_k or self._top_k
        hits = self._retriever.retrieve(question, top_k=k)
        if not hits:
            yield ("delta", NO_CONTEXT_ANSWER)
            yield ("done", None)
            return

        yield (
            "sources",
            [
                {
                    "source": hit["source"],
                    "content": hit["content"],
                    "similarity": hit["similarity"],
                }
                for hit in hits
            ],
        )
        context = "\n\n".join(
            f"[片段 {i + 1}] 来源: {hit['source']}\n{hit['content']}"
            for i, hit in enumerate(hits)
        )
        for chunk in self._chain.stream({"context": context, "question": question}):
            if chunk:
                yield ("delta", chunk)
        yield ("done", None)
