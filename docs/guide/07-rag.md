# 第 5 步 · 检索与生成

> 本章目标:实现 RAG 的「A」和「G」 —— 把检索到的片段组装成约束严格的 Prompt,交给 LLM 生成有据可依的回答,并编排成一条完整流水线。

## Prompt 设计:`app/generation/generator.py`

### System Prompt:防幻觉的三重约束

```python
SYSTEM_PROMPT = (
    "你是一个严谨的问答助手。请仅依据下方提供的【上下文】回答用户问题,"
    "不要编造上下文之外的信息。若上下文不足以回答问题,请明确说明"
    "「根据现有资料无法回答该问题」。回答时使用与问题相同的语言,"
    "并优先给出直接结论。"
)
```

拆开看,每句话都有明确职责:

| 约束 | 目的 |
|---|---|
| 仅依据【上下文】回答 | 划定信息来源边界 |
| 不要编造 / 信息不足要明说 | 把「拒答」变成合法行为,抑制幻觉 |
| 用问题相同的语言 | 中文提问就要中文回答 |
| 优先给出直接结论 | 回答风格:先答案后解释 |

### User Prompt:片段 + 来源的组装

```python
def build_user_prompt(question: str, contexts: list[dict]) -> str:
    sections = [
        f"[片段 {i + 1}] 来源: {hit['source']}\n{hit['content']}"
        for i, hit in enumerate(contexts)
    ]
    context_block = "\n\n".join(sections)
    return f"【上下文】\n{context_block}\n\n【问题】\n{question}"
```

每个片段带序号与**来源文件名** —— 来源进入 Prompt 后,LLM 的回答可以自然地引用「根据 guide.pdf 中…」,溯源从机制上成立。

```python
class Generator:
    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider

    def generate(self, question: str, contexts: list[dict]) -> str:
        user_prompt = build_user_prompt(question, contexts)
        return self._llm.chat(SYSTEM_PROMPT, user_prompt)
```

同样只依赖 `LLMProvider` 接口。

## RAG 编排:`app/rag/pipeline.py`

`RAGPipeline` 把 Retriever 和 Generator 组装成一条流水线,并处理一个关键分支:

```python
NO_CONTEXT_ANSWER = "根据现有资料无法回答该问题(知识库中未检索到相关内容)。"


@dataclass
class RAGResult:
    answer: str
    sources: list[dict] = field(default_factory=list)


class RAGPipeline:
    def __init__(self, llm_provider, embedding_provider, vector_store, top_k: int = 4):
        self._retriever = Retriever(embedding_provider, vector_store)
        self._generator = Generator(llm_provider)
        self._top_k = top_k

    def answer(self, question: str, top_k: int | None = None) -> RAGResult:
        k = top_k or self._top_k
        hits = self._retriever.retrieve(question, top_k=k)
        if not hits:
            return RAGResult(answer=NO_CONTEXT_ANSWER)     # 关键分支

        answer = self._generator.generate(question, hits)
        sources = [
            {"source": hit["source"], "content": hit["content"], "similarity": hit["similarity"]}
            for hit in hits
        ]
        return RAGResult(answer=answer, sources=sources)
```

**检索空命中时不调用 LLM**,直接返回固定文案。三个理由:

1. **省成本**:一次 LLM 调用的 token 是真金白银,明知无依据就别调
2. **防幻觉**:System Prompt 里「信息不足要明说」依赖模型自觉;这里从**代码机制**上保证不会出现无依据回答
3. **语义明确**:「知识库中没有」和「知识库里有但模型没答好」是两类问题,前者无需动用 LLM

`RAGResult.sources` 携带 `{source, content, similarity}`,前端「引用展开」展示的就是它。

## 框架模式对照:`app/rag/framework_pipeline.py`

自研链路讲完了,现在请出「对照组」—— 同样的 RAG 流程,用 LangChain 再实现一遍(`mode=framework` 时启用):

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),                      # 与自研模式同一个 System Prompt
    ("human", "【上下文】\n{context}\n\n【问题】\n{question}"),
])
chain = prompt | _create_chat_model(settings) | StrOutputParser()

answer = chain.invoke({"context": context, "question": question})
```

`prompt | llm | parser` 就是 LangChain 的 LCEL 链式编排,等价于自研模式的 `build_user_prompt() → LLMProvider.chat()`,只是把「组装 Prompt + 调用 + 解析」交给框架的标准组件。

两种模式的分工:

| | 自研模式(`mode=custom`) | 框架模式(`mode=framework`) |
|---|---|---|
| 检索 | 自研 Retriever | 自研 Retriever(**共用同一知识库**) |
| Prompt 组装 | `build_user_prompt()` 手写 f-string | `ChatPromptTemplate` 模板 |
| LLM 调用 | 自研 `LLMProvider.chat()` | LangChain ChatModel(OpenAI 兼容接口 / ChatAnthropic) |
| 空命中处理 | 直接返回固定文案 | 同左(共用逻辑) |

设计要点:

- **System Prompt 与自研模式完全一致** —— 保证对比是公平的,差异只来自实现方式
- **检索环节刻意复用**自研 Retriever —— 两种模式共享同一 ChromaDB 知识库,变量只有生成链路
- **LangChain 是可选依赖**:import 放在构造函数内,未安装时框架模式返回 500 + 安装指引,服务启动与自研模式完全不受影响
- 智谱 / Ollama 走 OpenAI 兼容接口(`ChatOpenAI` + 自定义 `base_url`),anthropic 用官方 `langchain-anthropic`

**为什么要做这个对照?** 第 1 章说过自研的理由;但「框架到底帮你做了什么」光靠嘴说不够直观。同一问题、同一知识库、同一 Prompt,切换模式各问一遍,框架封装的便利与「黑盒感」就都体会到了。

## 至此后端核心闭环

到这里,「入库四件套」(loader / splitter / pipeline / vector_store)与「问答三件套」(retriever / generator / pipeline)已经齐了,外加一个可切换的 LangChain 框架模式 —— RAG 的全部业务逻辑已经完成。剩下的第 6、7 步是把它暴露成 HTTP 服务和可视界面。

下一步 → [第 6 步 · REST API](/guide/08-api)
