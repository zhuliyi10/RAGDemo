"""Ollama 提供商：通过 HTTP 调用本地 Ollama 服务的 LLM 对话与 Embedding。"""
import json
from collections.abc import Iterator

import httpx

from app.config import Settings
from app.core.base import EmbeddingProvider, LLMProvider


class OllamaLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = httpx.post(
            f"{self._base_url}/api/chat", json=payload, timeout=120
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        payload = {
            "model": self._model,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.stream(
            "POST", f"{self._base_url}/api/chat", json=payload, timeout=120
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():          # NDJSON：每行一个 JSON 对象
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self._model, "input": texts}
        resp = httpx.post(
            f"{self._base_url}/api/embed", json=payload, timeout=120
        )
        resp.raise_for_status()
        return resp.json().get("embeddings", [])


def create_ollama_llm(settings: Settings) -> OllamaLLMProvider:
    return OllamaLLMProvider(settings.ollama_base_url, settings.llm_model)


def create_ollama_embedding(settings: Settings) -> OllamaEmbeddingProvider:
    return OllamaEmbeddingProvider(settings.ollama_base_url, settings.embedding_model)
