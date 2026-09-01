# 第 6 步 · REST API

> 本章目标:用 FastAPI 把 RAG 能力暴露成 HTTP 服务。重点在于 `deps.py` 的**懒加载单例**设计 —— 让模型未配置时服务也能正常启动。

## 依赖注入:`app/deps.py`

### 问题:Provider 构造依赖外部资源

`create_llm_provider()` 需要 API Key,缺 Key 会抛 `ValueError`。如果在**应用启动时**就创建 Provider,那么没配 Key 的用户连健康检查都用不了 —— 体验很糟。

### 解法:按需创建 + 只缓存成功实例

```python
_vector_store: VectorStore | None = None
_llm_provider: LLMProvider | None = None
_embedding_provider: EmbeddingProvider | None = None


def init_vector_store() -> VectorStore:
    """应用启动时初始化向量库(本地持久化,失败则无法继续)。"""
    global _vector_store
    if _vector_store is None:
        _vector_store = create_vector_store()
    return _vector_store


def get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = _create_with_http_error(create_llm_provider, "LLM")
    return _llm_provider


def _create_with_http_error(factory, label: str):
    try:
        return factory(get_settings())
    except ValueError as exc:                     # 缺 Key 等配置错误
        logger.error("%s Provider 初始化失败: %s", label, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

两类资源区别对待:

| 资源 | 初始化时机 | 理由 |
|---|---|---|
| 向量库 | 应用 `lifespan` 启动时 | 纯本地,失败说明环境有问题,早死早超生 |
| LLM / Embedding Provider | **首次被请求时** | 依赖外部 Key,未配置不应拖垮整个服务 |

效果:模型没配,服务照常启动,`/api/health` 永远绿色;用户真正调用 `/ingest` 或 `/query` 时才收到 500 + 明确的缺失提示(如「未配置 ZHIPU_API_KEY」)。

## 路由:`app/api/routes.py`

```python
router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, description="用户问题")
    top_k: int | None = Field(default=None, ge=1, le=20, description="检索片段数")
    mode: str = Field(default="custom", description="问答模式: custom=自研 / framework=LangChain 框架")

    @field_validator("mode")
    @classmethod
    def check_mode(cls, v: str) -> str:
        if v not in ("custom", "framework"):
            raise ValueError("mode 仅支持 custom 或 framework")
        return v


@router.post("/query")
def query(req: QueryRequest,
          settings: Settings = Depends(get_settings),
          vector_store: VectorStore = Depends(get_vector_store),
          llm_provider=Depends(get_llm_provider),
          embedding_provider=Depends(get_embedding_provider)) -> dict:
    if req.mode == "framework":
        try:
            pipeline = FrameworkRAGPipeline(settings, embedding_provider, vector_store,
                                            top_k=req.top_k or settings.top_k)
        except (RuntimeError, ValueError) as exc:   # 未装依赖 / 提供商或 Key 配置问题
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    else:
        pipeline = RAGPipeline(llm_provider, embedding_provider, vector_store,
                               top_k=req.top_k or settings.top_k)
    try:
        result = pipeline.answer(req.question)
    except Exception as exc:
        logger.exception("问答失败: %s", req.question)
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc
    return {"answer": result.answer, "sources": result.sources, "mode": req.mode}
```

要点:

- **请求校验交给 pydantic**:`question` 非空、`top_k` 范围 1~20、`mode` 仅接受 `custom` / `framework`,不合法自动 422
- **每请求组装 Pipeline**:RAGPipeline 无状态,`top_k` 可以按请求覆盖(默认回落到全局配置)
- **mode 切换实现**:`custom` 走自研 pipeline,`framework` 走 LangChain 编排;两种模式共享同一向量库与请求参数,仅生成链路不同,响应回传 `mode` 供前端标注
- **框架模式是可选能力**:LangChain 未安装时选 `framework` 返回 500 + 安装指引,不影响自研模式
- **异常收口**:`logger.exception` 记录完整堆栈,对外只暴露 500 + 简明 detail

入库端点体现「单文件失败不扩散」:

```python
@router.post("/ingest", response_model=list[IngestionResult])
def ingest(files: list[UploadFile], settings=Depends(get_settings),
           vector_store=Depends(get_vector_store),
           embedding_provider=Depends(get_embedding_provider)):
    results = []
    for file in files:
        result = ingest_document(
            filename=file.filename or "unnamed",
            content=file.file.read(),
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        results.append(result)
    return results
```

## 应用入口:`app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_vector_store()                           # 启动时初始化向量库
    logger.info("向量库已初始化: provider=%s model=%s",
                get_settings().embedding_provider, get_settings().embedding_model)
    yield


app = FastAPI(title="RAGDemo", version="0.1.0", lifespan=lifespan)

# 仅放行本地前端(任意端口)跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)
```

CORS 用**正则**限定 `localhost/127.0.0.1` 任意端口:本地前后端分端口开发无需关心跨域,同时不会把服务裸放到公网。

## 手动验证

```bash
uvicorn app.main:app --reload           # 默认 8000 端口,/docs 有交互式文档

# 入库
curl -X POST http://localhost:8000/api/ingest \
  -F "files=@guide.pdf" -F "files=@notes.md"

# 问答(自研模式)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "如何配置 Ollama?", "top_k": 3, "mode": "custom"}'

# 问答(框架模式,需安装 langchain-core / langchain-openai / langchain-anthropic)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "如何配置 Ollama?", "top_k": 3, "mode": "framework"}'
```

下一步 → [第 7 步 · 前端界面](/guide/09-frontend)
