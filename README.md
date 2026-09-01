# RAGDemo

**从 0 到 1 实现**的自研轻量 RAG（检索增强生成）服务：文档入库 → 分块 → 向量化 → 语义检索 → 增强生成。

核心链路不用 LangChain / LlamaIndex —— 分块、检索、Prompt 组装、编排全部手写，每一行 RAG 代码都透明可控；另内置 **LangChain 框架模式**作为对照组，同一知识库可一键切换体验两种实现。

## 从 0 到 1 文档站（VitePress）

技术实现以教程形式分章建站，按依赖顺序拆成 8 步，每步讲清楚「做什么、为什么、怎么做」：

> 项目概述 → 原理与架构 → ① 初始化与配置 → ② 模型抽象层 → ③ 文档解析与分块 → ④ 向量化与存储 → ⑤ 检索与生成 → ⑥ REST API → ⑦ 前端界面 → ⑧ 测试与运行 → 设计决策复盘

```bash
cd docs && npm install && npm run dev    # 文档站开发预览
npm run build                            # 产出 docs/.vitepress/dist，可静态托管
```

## 特性

- 自研文档解析与分块，不依赖 RAG 框架，代码透明可控
- 双模式问答：自研 pipeline 与 LangChain 框架模式一键切换，共享同一向量库（框架依赖可选，不装不影响自研模式）
- 多模型提供商可配置切换：OpenAI / Anthropic / Ollama / 智谱（LLM 与 Embedding 可独立选择）
- ChromaDB 本地持久化向量存储，支持按文档删除与溯源
- FastAPI 提供完整 REST API

## 快速开始

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置模型（复制模板并按需修改）
cp .env.example .env
# 修改 .env 中的 LLM_PROVIDER / EMBEDDING_PROVIDER 及 API Key

# 3. 启动服务
uvicorn app.main:app --reload
```

服务默认运行在 `http://localhost:8000`，交互式文档见 `http://localhost:8000/docs`。

## 配置说明（.env）

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LLM_PROVIDER` | 对话模型提供商：`openai` / `anthropic` / `ollama` / `zhipu` | `openai` |
| `LLM_MODEL` | 对话模型名 | `gpt-4o-mini` |
| `EMBEDDING_PROVIDER` | 向量化提供商：`openai` / `ollama` / `zhipu` | `openai` |
| `EMBEDDING_MODEL` | 向量化模型名 | `text-embedding-3-small` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `ZHIPU_API_KEY` | 智谱 API Key | - |
| `ZHIPU_BASE_URL` | 智谱 Anthropic 兼容对话接口 | `https://open.bigmodel.cn/api/anthropic` |
| `ZHIPU_OPENAI_BASE_URL` | 智谱 OpenAI 兼容对话接口（框架模式使用） | `https://open.bigmodel.cn/api/paas/v4` |
| `ZHIPU_EMBEDDING_URL` | 智谱 v4 Embeddings 接口 | `https://open.bigmodel.cn/api/paas/v4/embeddings` |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://localhost:11434` |
| `CHUNK_SIZE` | 分块大小（字符） | `800` |
| `CHUNK_OVERLAP` | 分块重叠（字符） | `120` |
| `TOP_K` | 默认检索片段数 | `4` |

使用 Ollama 示例（对话 qwen2.5 + 向量 bge-m3）：

```
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
```

使用智谱 AI 示例（对话 glm-4.5-air + 向量 embedding-3）：

```
LLM_PROVIDER=zhipu
LLM_MODEL=glm-4.5-air
EMBEDDING_PROVIDER=zhipu
EMBEDDING_MODEL=embedding-3
ZHIPU_API_KEY=你的智谱Key
```

## 前端页面

`frontend/` 为 React + TypeScript + Vite 工程，提供可视化界面：知识库文档管理（上传/删除）与对话式问答（含引用来源展开），问答工具栏支持**自研 / 框架模式切换**，每条回答标注所用模式。

```bash
# 终端 1：启动后端
cd RAGDemo && source .venv/bin/activate
uvicorn app.main:app --reload

# 终端 2：启动前端（自动代理 /api 到后端 8000）
cd frontend && npm install && npm run dev
# 打开终端提示的地址（默认 http://localhost:5173，被占用时自动切换）
```

生产构建：`npm run build` 产出 `dist/`，可由任意静态服务器或网关托管。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ingest` | 上传文档入库（multipart，支持多文件，txt/md/pdf/docx） |
| GET | `/api/documents` | 列出已入库文档及分块数 |
| DELETE | `/api/documents/{doc_id}` | 删除文档及其全部向量 |
| POST | `/api/query` | RAG 问答：`{"question": "...", "top_k": 4, "mode": "custom"}`，`mode` 可选 `custom`（自研）/ `framework`（LangChain） |
| GET | `/api/health` | 健康检查 |

### 示例

```bash
# 入库
curl -X POST http://localhost:8000/api/ingest \
  -F "files=@guide.pdf" -F "files=@notes.md"

# 问答（自研模式）
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "如何配置 Ollama？", "top_k": 3, "mode": "custom"}'

# 问答（框架模式，需安装 langchain-core / langchain-openai / langchain-anthropic）
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "如何配置 Ollama？", "top_k": 3, "mode": "framework"}'
```

## 架构

```
app/
├── main.py              # FastAPI 入口
├── config.py            # 配置（pydantic-settings）
├── deps.py              # Provider / 向量库懒加载单例
├── api/routes.py        # REST API
├── core/                # 模型提供商抽象与实现
│   ├── base.py          # LLMProvider / EmbeddingProvider 接口
│   ├── factory.py       # 按配置创建 Provider
│   └── providers/       # openai / anthropic / ollama / zhipu 实现
├── ingestion/           # 文档加载、分块、入库流水线
├── retrieval/           # ChromaDB 封装与语义检索
├── generation/          # Prompt 构造与生成
└── rag/
    ├── pipeline.py            # 自研 RAG 编排：检索 → 增强 → 生成
    └── framework_pipeline.py  # 框架模式：LangChain LCEL（可选依赖）
```

## 测试

```bash
pytest tests/ -v
```
