"""Provider 工厂：根据配置创建 LLM 与 Embedding 实例。"""
from app.config import Settings, get_settings
from app.core.base import EmbeddingProvider, LLMProvider
from app.core.providers.anthropic_provider import create_anthropic_llm
from app.core.providers.ollama_provider import (
    create_ollama_embedding,
    create_ollama_llm,
)
from app.core.providers.openai_provider import (
    create_openai_embedding,
    create_openai_llm,
)
from app.core.providers.zhipu_provider import (
    create_zhipu_embedding,
    create_zhipu_llm,
)

_LLM_FACTORIES = {
    "openai": create_openai_llm,
    "anthropic": create_anthropic_llm,
    "ollama": create_ollama_llm,
    "zhipu": create_zhipu_llm,
}

_EMBEDDING_FACTORIES = {
    "openai": create_openai_embedding,
    "ollama": create_ollama_embedding,
    "zhipu": create_zhipu_embedding,
}


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    factory = _LLM_FACTORIES.get(settings.llm_provider)
    if factory is None:
        raise ValueError(f"不支持的 LLM 提供商: {settings.llm_provider}")
    return factory(settings)


def create_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    factory = _EMBEDDING_FACTORIES.get(settings.embedding_provider)
    if factory is None:
        raise ValueError(f"不支持的 Embedding 提供商: {settings.embedding_provider}")
    return factory(settings)
