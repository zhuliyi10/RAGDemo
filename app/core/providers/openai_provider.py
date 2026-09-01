"""OpenAI 提供商：LLM 对话与 Embedding。"""
from collections.abc import Iterator

import openai

from app.config import Settings
from app.core.base import EmbeddingProvider, LLMProvider


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("未配置 OPENAI_API_KEY，请在 .env 中设置")
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("未配置 OPENAI_API_KEY，请在 .env 中设置")
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]


def create_openai_llm(settings: Settings) -> OpenAILLMProvider:
    return OpenAILLMProvider(settings.openai_api_key, settings.llm_model)


def create_openai_embedding(settings: Settings) -> OpenAIEmbeddingProvider:
    return OpenAIEmbeddingProvider(settings.openai_api_key, settings.embedding_model)
