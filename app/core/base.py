"""模型提供商抽象基类。"""
from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    """大语言模型提供商抽象。"""

    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """根据系统提示与用户提示生成回复。"""

    @abstractmethod
    def chat_stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """流式生成回复，逐段 yield 文本增量。"""


class EmbeddingProvider(ABC):
    """文本向量化提供商抽象。"""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为向量列表。"""
