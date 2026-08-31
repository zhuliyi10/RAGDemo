"""全局配置：通过环境变量 / .env 文件加载。"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM 提供商
    llm_provider: str = Field(default="openai", description="openai | anthropic | ollama | zhipu")
    llm_model: str = Field(default="gpt-4o-mini")

    # Embedding 提供商
    embedding_provider: str = Field(default="openai", description="openai | ollama | zhipu")
    embedding_model: str = Field(default="text-embedding-3-small")

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    zhipu_api_key: str = ""

    # Anthropic（含智谱 Anthropic 兼容接口）
    anthropic_base_url: str = "https://api.anthropic.com"

    # 智谱 AI（bigmodel.cn）
    zhipu_base_url: str = "https://open.bigmodel.cn/api/anthropic"
    zhipu_embedding_url: str = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # 分块参数
    chunk_size: int = Field(default=800, ge=50)
    chunk_overlap: int = Field(default=120, ge=0)

    # 检索参数
    top_k: int = Field(default=4, ge=1, le=50)

    # 服务
    host: str = "0.0.0.0"
    port: int = 8000

    # 持久化目录
    chroma_dir: Path = DATA_DIR / "chroma"

    def validate_overlap(self) -> None:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_overlap()
    return settings
