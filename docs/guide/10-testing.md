# 第 8 步 · 测试与运行

> 本章目标:用 pytest 给核心算法上保险,并完成前后端联调验收。RAG 里「纯逻辑」的部分(分块、解析、检索编排)完全可测,这也是自研不依赖重框架的额外红利。

## 测试结构

```
tests/
├── test_loader.py      # 文档解析
├── test_splitter.py    # 分块算法
└── test_retriever.py   # 检索编排(mock)
```

```bash
pytest tests/ -v
```

## 各层测什么

### 分块算法 —— 最值得测的纯函数

`splitter.py` 是无副作用纯函数,边界条件丰富,是单元测试的黄金对象:

- **大小约束**:任意输入,所有 chunk 长度 ≤ `chunk_size`
- **重叠生效**:相邻 chunk 的尾部/头部确有重叠(长度 = `chunk_overlap`)
- **进度保证**:切分点必须前进,任何输入都不会死循环
- **边界条件**:空文本返回 `[]`、短文本(≤ chunk_size)原样返回单个 chunk、`chunk_overlap >= chunk_size` 抛 `ValueError`
- **语义保护**:中文句末标点(`。!?`)不落单、优先在段落/行边界切分

### 文档解析

- 各格式正路径:txt/md 解码、pdf 逐页提取、docx 段落 + 表格
- 负路径:不支持的扩展名抛 `UnsupportedFormatError`,错误消息包含支持列表
- 容错:坏字节 UTF-8 解码不抛异常

### 检索编排 —— 用 mock 隔离外部依赖

```python
class FakeEmbedding(EmbeddingProvider):
    def embed(self, texts):
        return [[0.1, 0.2] for _ in texts]

class FakeVectorStore:
    def query(self, embedding, top_k):
        return [{"content": "片段", "source": "a.md",
                 "doc_id": "d1", "chunk_index": 0, "similarity": 0.9}]
```

因为第 2 步定义了接口,这里可以直接用假实现替换真模型/真库 —— 不联网、不花钱、毫秒级跑完。验证点:

- `Retriever.retrieve` 正确串起「向量化 → 查询」
- `RAGPipeline.answer` 空命中时**不调用 LLM**、返回固定文案
- 有命中时 `sources` 结构完整(source / content / similarity)

## 启动与联调

```bash
# 终端 1:后端
source .venv/bin/activate
uvicorn app.main:app --reload            # http://localhost:8000

# 终端 2:前端
cd frontend && npm run dev               # http://localhost:5173
```

## 验收清单

按顺序走一遍,即完成从 0 到 1 的全流程验证:

| # | 操作 | 预期 |
|---|---|---|
| 1 | 打开 `http://localhost:8000/docs` | Swagger 交互文档可用 |
| 2 | 前端页面顶部徽标 | 绿色(health 通过) |
| 3 | 上传 1 个 md + 1 个 pdf | 列表出现两个文档,各自显示分块数 |
| 4 | 再上传一个 `.exe` | 该条目报「不支持的文件格式」,其他文件不受影响 |
| 5 | 提问「文档里有什么内容?」 | 回答附引用来源,可展开看到片段与相似度 |
| 6 | 提问一个知识库肯定没有的问题 | 返回「根据现有资料无法回答…」(空命中路径) |
| 7 | 删除一个文档,再问相关问题 | 该文档不再出现在引用中 |
| 8 | 重启后端服务 | 文档列表还在(ChromaDB 持久化生效) |

## 一图回顾:全部 8 步

```
第 1 步  配置层          config.py + .env
第 2 步  模型抽象层      base.py / factory.py / providers/*
第 3 步  解析与分块      loader.py / splitter.py / ingestion/pipeline.py
第 4 步  向量化与存储    retrieval/vector_store.py / retriever.py
第 5 步  检索与生成      generation/generator.py / rag/pipeline.py
第 6 步  REST API        api/routes.py / deps.py / main.py
第 7 步  前端界面        frontend/(React + TS + Vite)
第 8 步  测试与运行      pytest + 联调验收
```

下一步 → [进阶 · 设计决策复盘](/guide/11-advanced)
