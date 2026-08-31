# 进阶 · 设计决策复盘

> 本章目标:把前面章节里「为什么这么做」集中复盘,并给出继续演进的路线图。适合回头翻阅,不必顺序阅读。

## 关键设计决策

| # | 决策 | 权衡 |
|---|---|---|
| 1 | 不用 RAG 框架,自研分块/检索/编排 | 换来透明可控与学习价值;代价是暂无 rerank、混合检索等高级能力 |
| 2 | 分块按字符数而非 token | 中文场景直观、无需 tokenizer 依赖;代价是各提供商 token 用量不完全均匀 |
| 3 | ID 编码 `{doc_id}::{chunk_index}` + metadata 过滤删除 | 单一 collection 实现按文档管理,无额外索引表;代价是依赖字符串约定 |
| 4 | 检索空命中不调 LLM | 省成本、防幻觉;代价是「答案在库里但未召回」时直接拒答(调大 top_k 可缓解) |
| 5 | Provider 懒加载单例 | 未配置模型时服务可启动、健康检查可用;代价是配置错误延迟到首次调用才暴露 |
| 6 | 智谱 LLM 复用 Anthropic Provider | 零成本接入协议兼容服务;代价是依赖智谱保持兼容端点稳定 |
| 7 | 智谱 Embedding 结果按 index 排序 | 保证批量向量与输入顺序严格对齐;代价是多一行防御代码 |
| 8 | 删除文档 = 先查后删(两步) | 幂等、无需维护额外索引;代价是两次 ChromaDB 调用 |

## 错误处理策略总览

```
loader.py      抛 ValueError(格式不支持)          ← 可预期业务异常
    ↓
ingestion/pipeline.py   逐步捕获,失败写进 result.errors,不中断批量
    ↓
api/routes.py           未知异常统一 500 + logger.exception 记录堆栈
    ↓
前端 api.ts             网络失败固定文案;HTTP 错误优先透出后端 detail
```

- **分层捕获**:越往外层,错误越「收口」;越往内层,错误越「具体」
- **批量隔离**:多文件入库,单文件任何一步失败只影响自己的 `errors`
- **配置前置校验**:分块参数在 `get_settings()` 加载时校验;Provider 缺 Key 在构造时抛出
- **两套 500 语义区分**:「未配置模型」(deps 层,明确提示缺什么)vs「运行时失败」(routes 层,日志留全栈)

## 扩展指南

### 新增模型提供商(如 DeepSeek)

1. `app/core/providers/` 新建 `deepseek_provider.py`:若兼容 OpenAI 协议,直接继承 `OpenAILLMProvider` 改 base_url;否则实现 `LLMProvider`
2. `factory.py` 注册表加一行 `"deepseek": create_deepseek_llm`
3. `config.py` 增加 `base_url` / API Key 字段,`.env.example` 与 README 同步

### 新增文档格式(如 HTML)

1. `loader.py` 的 `SUPPORTED_EXTENSIONS` 加扩展名
2. `_parse()` 加分支与解析函数(建议依赖延迟 import,保持启动轻量)

### 改进检索质量(按投入产出排序)

1. **调参**:`chunk_size` / `chunk_overlap` / `top_k` 都在 `.env`,先扫参
2. **rerank**:对 `top_k` 结果用重排模型二次排序,取前 N 进 Prompt
3. **混合检索**:关键词(BM25)+ 向量双路召回合并
4. **查询改写**:多轮场景把「它呢?」改写成完整问题再检索

### 其他演进方向

- **体验**:流式输出(SSE)、多轮对话上下文、会话持久化
- **工程**:并发 embed 限流、同 source 覆盖更新入库、Dockerfile 部署
- **观测**:问答日志与「引用命中率」统计,为调参提供数据

## 结语

整个项目约 700 行 Python + 一个 React 前端,没有一行 RAG 逻辑来自框架。回头看会发现:RAG 的「神秘感」其实由四件事构成 —— **好的分块、准确的向量检索、约束严格的 Prompt、清晰的编排**。这四件事,你都已经亲手写过一遍了。
