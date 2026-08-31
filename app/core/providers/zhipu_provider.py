"""智谱 AI 提供商（bigmodel.cn）。

- LLM：复用 Anthropic 兼容接口（https://open.bigmodel.cn/api/anthropic），
  通过 anthropic SDK 调用，模型如 glm-4.5-air。
- Embedding：调用智谱 v4 Embeddings API，模型如 embedding-3。
"""
import httpx

from app.config import Settings
from app.core.base import EmbeddingProvider, LLMProvider
from app.core.providers.anthropic_provider import AnthropicLLMProvider


class ZhipuLLMProvider(AnthropicLLMProvider):
    """基于智谱 Anthropic 兼容接口的对话模型。"""

    def __init__(self, api_key: str, model: str, base_url: str):
        if not api_key:
            raise ValueError("未配置 ZHIPU_API_KEY，请在 .env 中设置")
        super().__init__(api_key, model, base_url=base_url)


class ZhipuEmbeddingProvider(EmbeddingProvider):
    """调用智谱 v4 Embeddings API 的向量化模型。"""

    def __init__(self, api_key: str, model: str, url: str):
        if not api_key:
            raise ValueError("未配置 ZHIPU_API_KEY，请在 .env 中设置")
        self._api_key = api_key
        self._model = model
        self._url = url

    def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self._model, "input": texts}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        resp = httpx.post(self._url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        # 按 index 排序，保证返回顺序与输入一致
        data.sort(key=lambda item: item.get("index", 0))
        return [item["embedding"] for item in data]


def create_zhipu_llm(settings: Settings) -> ZhipuLLMProvider:
    return ZhipuLLMProvider(
        settings.zhipu_api_key,
        settings.llm_model,
        settings.zhipu_base_url,
    )


def create_zhipu_embedding(settings: Settings) -> ZhipuEmbeddingProvider:
    return ZhipuEmbeddingProvider(
        settings.zhipu_api_key,
        settings.embedding_model,
        settings.zhipu_embedding_url,
    )
