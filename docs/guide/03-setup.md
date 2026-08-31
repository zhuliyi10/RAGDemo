# 第 1 步 · 初始化与配置

> 本章目标:搭好项目骨架 —— 虚拟环境、依赖清单,以及一个集中管理所有配置的 `Settings` 类。后续所有模块都从这里拿配置。

## 建立虚拟环境与依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` 分四类,每个依赖都有明确用途:

```
fastapi>=0.115.0            # Web 框架
uvicorn[standard]>=0.30.0   # ASGI 服务器
chromadb>=0.5.0             # 向量数据库(本地持久化)
openai>=1.40.0              # OpenAI 官方 SDK
anthropic>=0.34.0           # Anthropic 官方 SDK(智谱 LLM 也用它)
httpx>=0.27.0               # HTTP 客户端(Ollama / 智谱 Embedding)
pydantic>=2.8.0             # 数据校验
pydantic-settings>=2.4.0    # .env 配置加载
python-multipart>=0.0.9     # FastAPI 解析文件上传
pypdf>=4.3.0                # PDF 解析
python-docx>=1.1.0          # Word 解析
pytest>=8.2.0               # 测试
```

## 配置层:`app/config.py`

配置要解决三个问题:**从哪读**(环境变量 / `.env`)、**怎么校验**(类型、约束)、**谁持有**(全局单例)。

```python
"""全局配置:通过环境变量 / .env 文件加载。"""
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
        extra="ignore",          # 容忍 .env 里的多余变量
    )

    # LLM 提供商
    llm_provider: str = Field(default="openai", description="openai | anthropic | ollama | zhipu")
    llm_model: str = Field(default="gpt-4o-mini")

    # Embedding 提供商(注意:与 LLM 独立,可自由组合)
    embedding_provider: str = Field(default="openai", description="openai | ollama | zhipu")
    embedding_model: str = Field(default="text-embedding-3-small")

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    zhipu_api_key: str = ""

    # 各服务地址
    anthropic_base_url: str = "https://api.anthropic.com"
    zhipu_base_url: str = "https://open.bigmodel.cn/api/anthropic"
    zhipu_embedding_url: str = "https://open.bigmodel.cn/api/paas/v4/embeddings"
    ollama_base_url: str = "http://localhost:11434"

    # RAG 参数
    chunk_size: int = Field(default=800, ge=50)        # 分块大小(字符)
    chunk_overlap: int = Field(default=120, ge=0)      # 相邻分块重叠
    top_k: int = Field(default=4, ge=1, le=50)         # 检索片段数

    # 服务
    host: str = "0.0.0.0"
    port: int = 8000
    chroma_dir: Path = DATA_DIR / "chroma"

    def validate_overlap(self) -> None:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_overlap()
    return settings
```

三个要点:

1. **`lru_cache` 单例**:`get_settings()` 全项目只真正读一次 `.env`,之后都是拿缓存对象。FastAPI 的 `Depends(get_settings)` 注入的始终是同一份配置。
2. **启动即校验**:`chunk_overlap < chunk_size` 这类约束在首次读取时就检查,配置错误不会拖到业务运行中才炸。
3. **LLM 与 Embedding 是两组独立配置**:对话用 A 家、向量用 B 家是合法且常见的组合(例如智谱 `glm-4.5-air` + `embedding-3`,或 Ollama `qwen2.5` + `bge-m3`)。

## `.env` 设计

提交 `.env.example` 模板、忽略真实 `.env`(防止 API Key 泄漏):

```bash
LLM_PROVIDER=zhipu              # openai | anthropic | ollama | zhipu
LLM_MODEL=glm-4.5-air
EMBEDDING_PROVIDER=zhipu        # openai | ollama | zhipu
EMBEDDING_MODEL=embedding-3
ZHIPU_API_KEY=你的Key
```

验证点:`python -c "from app.config import get_settings; print(get_settings().llm_provider)"` 能打印出提供商即配置层就绪。

下一步 → [第 2 步 · 模型抽象层](/guide/04-provider)
