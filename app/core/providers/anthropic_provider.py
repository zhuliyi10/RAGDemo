"""Anthropic 提供商：LLM 对话（Claude 系列，不支持 Embedding）。

支持自定义 base_url，可对接智谱等 Anthropic 兼容接口。
"""
import anthropic

from app.config import Settings
from app.core.base import LLMProvider


class AnthropicLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        if not api_key:
            raise ValueError("未配置 ANTHROPIC_API_KEY，请在 .env 中设置")
        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(
            block.text for block in resp.content if block.type == "text"
        ) or ""


def create_anthropic_llm(settings: Settings) -> AnthropicLLMProvider:
    return AnthropicLLMProvider(
        settings.anthropic_api_key,
        settings.llm_model,
        base_url=settings.anthropic_base_url,
    )
