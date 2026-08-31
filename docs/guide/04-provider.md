# 第 2 步 · 模型抽象层

> 本章目标:定义两个抽象接口把「上层业务」与「具体模型厂商」解耦,再用工厂按配置实例化。这一步做完,换模型厂商只改 `.env`,一行业务代码都不用动。

## 为什么第一块写它

RAG 全流程中,只有两个地方要「碰模型」:把文本变向量(Embedding)、用向量生成回答(LLM)。先把这两个能力抽象出来,后面每个模块都可以对着接口开发、对着接口 mock 测试 —— 这是依赖倒置:上层依赖接口,不依赖实现。

## 接口定义:`app/core/base.py`

```python
"""模型提供商抽象基类。"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """大语言模型提供商抽象。"""

    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """根据系统提示与用户提示生成回复。"""


class EmbeddingProvider(ABC):
    """文本向量化提供商抽象。"""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为向量列表。"""
```

刻意保持最小面:`chat` 是同步单轮(够用且简单),`embed` 是**批量**接口(入库时几十个 chunk 一次请求)。

## 工厂:`app/core/factory.py`

注册表字典模式,配置字符串 → 构造函数:

```python
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
```

注意 Embedding 只有 3 家 —— Anthropic 官方不提供向量接口。新增厂商 = 写一个 Provider 文件 + 注册表加一行。

## 四家实现要点

### OpenAI —— 官方 SDK

```python
class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("未配置 OPENAI_API_KEY,请在 .env 中设置")
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
```

Embedding 同理,`embeddings.create(model=..., input=texts)` 批量返回。**构造函数缺 Key 就抛 `ValueError`**,错误在初始化时暴露,而不是等到第一次调用。

### Anthropic —— 官方 SDK

```python
def chat(self, system_prompt: str, user_prompt: str) -> str:
    resp = self._client.messages.create(
        model=self._model,
        max_tokens=2048,
        system=system_prompt,                      # Anthropic 的 system 是独立参数
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(
        block.text for block in resp.content if block.type == "text"
    ) or ""
```

两个协议差异:system prompt 不在 messages 里而是独立参数;返回是内容块列表,要过滤 `type == "text"` 拼接。

### Ollama —— httpx 直调本地服务

```python
def chat(self, system_prompt: str, user_prompt: str) -> str:
    payload = {"model": self._model, "stream": False, "messages": [...]}
    resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "")
```

Embedding 走 `/api/embed`,`input` 传列表即可批量。`timeout=120` 给本地大模型推理留足时间。

### 智谱 —— 协议兼容即代码复用

智谱提供 **Anthropic 兼容接口**(`open.bigmodel.cn/api/anthropic`),所以 LLM 直接继承复用:

```python
class ZhipuLLMProvider(AnthropicLLMProvider):
    """基于智谱 Anthropic 兼容接口的对话模型。"""

    def __init__(self, api_key: str, model: str, base_url: str):
        if not api_key:
            raise ValueError("未配置 ZHIPU_API_KEY,请在 .env 中设置")
        super().__init__(api_key, model, base_url=base_url)
```

`chat()` 逻辑一行未写,只校验自己的 Key 并换 base_url。Embedding 无兼容层,用 httpx 调 v4 接口:

```python
def embed(self, texts: list[str]) -> list[list[float]]:
    payload = {"model": self._model, "input": texts}
    headers = {"Authorization": f"Bearer {self._api_key}"}
    resp = httpx.post(self._url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    data.sort(key=lambda item: item.get("index", 0))   # 关键:按 index 排序
    return [item["embedding"] for item in data]
```

**为什么按 `index` 排序**:批量接口返回顺序不保证与输入一致,而分块与向量是按下标严格对齐的,乱序等于数据错位。排序一行,换来顺序确定性。

## 本章小结

| 组件 | 职责 |
|---|---|
| `base.py` | 两个抽象接口,全系统的模型契约 |
| `factory.py` | 配置字符串 → 实例,新增厂商只加一行 |
| `providers/` | 各厂商实现,缺 Key 即抛错、失败尽早暴露 |

下一步 → [第 3 步 · 文档解析与分块](/guide/05-ingestion)
