"""依赖管理：Provider 与向量库的懒加载单例。

模型 Provider 涉及外部 API Key / 本地服务，可能初始化失败，
因此采用按需创建 + 缓存成功实例的策略，保证服务在未配置模型时仍可启动。
"""
import logging

from fastapi import HTTPException

from app.config import Settings, get_settings
from app.core.base import EmbeddingProvider, LLMProvider
from app.core.factory import create_embedding_provider, create_llm_provider
from app.retrieval.vector_store import VectorStore, create_vector_store

logger = logging.getLogger(__name__)

_vector_store: VectorStore | None = None
_llm_provider: LLMProvider | None = None
_embedding_provider: EmbeddingProvider | None = None


def init_vector_store() -> VectorStore:
    """应用启动时初始化向量库（本地持久化，失败则无法继续）。"""
    global _vector_store
    if _vector_store is None:
        _vector_store = create_vector_store()
    return _vector_store


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = create_vector_store()
    return _vector_store


def get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = _create_with_http_error(create_llm_provider, "LLM")
    return _llm_provider


def get_embedding_provider() -> EmbeddingProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = _create_with_http_error(
            create_embedding_provider, "Embedding"
        )
    return _embedding_provider


def _create_with_http_error(factory, label: str):
    settings: Settings = get_settings()
    try:
        return factory(settings)
    except ValueError as exc:
        logger.error("%s Provider 初始化失败: %s", label, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
