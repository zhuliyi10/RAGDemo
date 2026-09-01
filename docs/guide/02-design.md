# 原理与架构设计

> 本章目标:理解 RAG 的基本原理,以及本项目为什么这样分层、两条核心数据流如何运转。动手写代码之前先想清楚结构,后面 8 步只是把这个结构填满。

## RAG 的三个环节

```
① 检索(Retrieval)  问题向量化,在向量库中找出语义最相关的 top_k 片段
② 增强(Augmented)  把片段组装进 Prompt,作为回答的「依据」
③ 生成(Generation) LLM 只依据片段作答,不编造
```

落地上就是两个离线/在线各半的流程:

- **入库链路(离线准备)**:文档 → 解析 → 分块 → 向量化 → 存入向量库
- **问答链路(在线服务)**:问题 → 向量化 → 检索 → 组装 Prompt → LLM → 答案 + 来源

## 整体架构

```
┌─────────────────────────────── 前端 (React + TS + Vite) ───────────────────────────────┐
│  DocumentsPanel(上传/删除/列表)        ChatPanel(问答 + 引用展开)      HealthBadge     │
└──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │ /api/*(开发期 Vite 代理 → :8000)
┌──────────────────────────────────────▼─────────────────────────────────────────────────┐
│  api/routes.py        REST API 层(ingest / documents / query / health)                │
│  deps.py              依赖注入:Provider 与向量库的懒加载单例                           │
├───────────────────────────────────────────────────────────────────────────────────────┤
│  rag/pipeline.py           自研编排:Retriever → Generator → RAGResult                   │
│  rag/framework_pipeline.py 框架模式:LangChain LCEL 链(mode=framework 时启用)         │
├──────────────┬────────────────┬───────────────────┬───────────────────────────────────┤
│ ingestion/   │  retrieval/    │  generation/      │  core/(模型抽象层)                │
│ loader.py    │  retriever.py  │  generator.py     │  base.py   两个抽象接口           │
│ splitter.py  │  vector_store  │  (Prompt 构造)    │  factory.py 工厂注册表            │
│ pipeline.py  │  (ChromaDB)    │                   │  providers/ 四家实现              │
└──────────────┴────────────────┴───────────────────┴────────────┬──────────────────────┘
                                                                 │
                    ┌────────────┬───────────────┬───────────────┴────────┐
                    │  OpenAI    │   Anthropic   │  Ollama(httpx)         │
                    │  (SDK)     │   (SDK,智谱   │  /api/chat /api/embed  │
                    │            │   LLM 兼容复用)│                        │
                    └────────────┴───────────────┴────────────────────────┘
                                       ChromaDB ← data/chroma/(磁盘持久化)
```

分层原则:**上层依赖下层的接口,不依赖具体实现**。

- `rag/pipeline.py` 只认识 `Retriever`、`Generator`,不关心模型是哪家
- `retrieval/retriever.py` 只认识 `EmbeddingProvider` 接口,不知道背后是 OpenAI 还是智谱
- 唯一知道「具体用哪家」的是 `core/factory.py`,而它也只是照着配置分发

## 两条核心数据流

**入库链路**(POST /api/ingest):

```
文件(bytes)
  → load_document()       按扩展名解析为纯文本
  → split_document()      两级分块,得到 chunk 列表
  → embedding.embed()     批量向量化(一次请求)
  → vector_store.upsert() 写入 ChromaDB(ids = "{doc_id}::{chunk_index}")
```

**问答链路**(POST /api/query):

```
问题(question, mode)
  → mode=custom    → RAGPipeline:自研 Retriever + Generator
  → mode=framework → FrameworkRAGPipeline:自研 Retriever + LangChain LCEL 链
  共同:Retriever.retrieve()   问题向量化 → ChromaDB 查询 top_k 片段
       [空命中则直接返回固定文案,不调 LLM]
       生成回答 → RAGResult { answer, sources[] }   sources 含原文/来源文件/相似度
```

两种模式**共享同一向量库与检索组件**,变量只有生成链路(Prompt 组装 + LLM 调用),保证对照实验的公平性。

两个设计点提前说明:

1. **入库时批量 embed 一次**而不是逐 chunk 调用 —— 减少网络往返,各 Provider 的批量接口顺序与输入一致
2. **检索空命中不调 LLM** —— 直接返回「无法回答」,省成本且机制上杜绝无依据的编造

## 一次问答的完整时序

```
用户输入问题
  → 前端 ChatPanel → POST /api/query {question, top_k, mode}
  → routes.query() 依赖注入:get_settings / get_vector_store / get_llm_provider / get_embedding_provider
  → mode=custom:RAGPipeline.answer()  |  mode=framework:FrameworkRAGPipeline.answer()
      → Retriever.retrieve():EmbeddingProvider.embed([question]) → VectorStore.query(top_k)
      → 生成:自研 build_user_prompt() + LLMProvider.chat()
              或 LangChain ChatPromptTemplate + ChatModel(LCEL)
  → {answer, sources[], mode} → 前端渲染回答 + 模式徽标 + 可展开引用
```

接下来 → [第 1 步 · 初始化与配置](/guide/03-setup)
