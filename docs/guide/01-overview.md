# 项目概述:我们要做什么

> 本章目标:明确这个项目要做一个什么样的 RAG 服务、最终长什么样、为什么选择自研而不是用现成框架。

## RAG 是什么

RAG(Retrieval-Augmented Generation,检索增强生成)= **先检索、再生成**:

```
用户提问 → 从知识库中检索出最相关的若干片段 → 把片段塞进 Prompt → LLM 依据片段回答
```

它解决大模型的两个根本问题:**知识过期**(模型不知道你的私有文档)与**幻觉**(模型一本正经地编造)。把答案依据「喂」给模型,回答就有了出处。

## 最终成品

一个完整可运行的服务,包含三部分:

| 组成 | 技术 | 形态 |
|---|---|---|
| 后端 | Python 3.14 + FastAPI | REST API,`uvicorn` 启动 |
| 向量存储 | ChromaDB | 纯本地磁盘持久化,零部署 |
| 前端 | React 18 + TypeScript + Vite | 文档管理 + 对话式问答界面 |

核心功能:

- **文档入库**:上传 txt / md / pdf / docx,自动解析、分块、向量化入库,支持多文件批量
- **语义问答**:提问后检索最相关的 `top_k` 个片段,LLM 生成回答并附**引用来源**(原文件 + 片段 + 相似度)
- **文档管理**:查看已入库文档及分块数、按文档删除
- **多模型切换**:LLM 与 Embedding 独立配置,支持 OpenAI / Anthropic / Ollama / 智谱

REST API 一览:

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ingest` | 上传文档入库(multipart 多文件) |
| GET | `/api/documents` | 列出已入库文档及分块数 |
| DELETE | `/api/documents/{doc_id}` | 删除文档及其全部向量 |
| POST | `/api/query` | RAG 问答:`{"question": "...", "top_k": 4}` |
| GET | `/api/health` | 健康检查 |

## 为什么自研,不用 LangChain?

本项目**不依赖任何 RAG 框架**(LangChain / LlamaIndex),分块、检索、Prompt 组装、编排全部手写:

1. **透明可控**:RAG 的效果瓶颈往往就在分块策略和 Prompt 设计上。用框架时这些细节被层层封装,出了问题难排查;自己写,每一行都清清楚楚。
2. **学习价值**:把「从 0 到 1」的过程走一遍,才能理解框架帮你做了什么。本教程站就是按这个思路分章展开的。
3. **体量很小**:核心逻辑约 700 行 Python,不需要框架的「重量」。

当然,底层基础设施仍然站在成熟组件的肩膀上:FastAPI(Web 框架)、ChromaDB(向量库)、各家官方 SDK / httpx(模型调用)、pypdf / python-docx(文档解析)—— **不重复造轮子,但 RAG 本身的轮子自己造**。

## 技术选型与理由

| 层面 | 选型 | 理由 |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | 异步、类型友好、自带 OpenAPI 交互文档 |
| 配置 | pydantic-settings | `.env` 加载 + 类型校验一步到位 |
| 向量存储 | ChromaDB PersistentClient | 纯本地零部署,原生 HNSW 与 metadata 过滤 |
| 模型调用 | openai / anthropic SDK + httpx | 官方 SDK 优先;无 SDK 的用 httpx 直调 |
| 文档解析 | pypdf / python-docx | 轻量,覆盖主流办公格式 |
| 前端 | React 18 + Vite 5 | 轻量组合,不引 UI 组件库 |
| 测试 | pytest | 核心算法逻辑可测 |

## 最终代码结构

```
app/
├── main.py              # FastAPI 入口:lifespan + CORS
├── config.py            # 配置(pydantic-settings)
├── deps.py              # 依赖注入:懒加载单例
├── api/routes.py        # REST API
├── core/
│   ├── base.py          # LLMProvider / EmbeddingProvider 抽象接口
│   ├── factory.py       # 注册表工厂
│   └── providers/       # openai / anthropic / ollama / zhipu
├── ingestion/           # loader.py + splitter.py + pipeline.py
├── retrieval/           # vector_store.py + retriever.py
├── generation/          # generator.py(Prompt 设计)
└── rag/pipeline.py      # RAG 编排:检索 → 增强 → 生成
```

接下来 → [原理与架构设计](/guide/02-design)
