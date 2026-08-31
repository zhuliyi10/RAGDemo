---
layout: home

hero:
  name: RAGDemo
  text: 从 0 到 1 实现一个 RAG 服务
  tagline: 文档入库 → 分块 → 向量化 → 语义检索 → 增强生成。不用 LangChain,不用 LlamaIndex,每一行 RAG 代码都自己写、都讲清楚。
  actions:
    - theme: brand
      text: 开始阅读
      link: /guide/01-overview
    - theme: alt
      text: 查看源码
      link: https://github.com/zhuliyi10/RAGDemo

features:
  - icon: 🧭
    title: 8 步走完 RAG 全流程
    details: 从项目初始化到前端界面,按依赖顺序拆成 8 个步骤章节,每步讲清楚「做什么、为什么、怎么做」。
  - icon: 📄
    title: 自研解析与分块
    details: txt / md / pdf / docx 解析;段落聚合 + 递归分隔符切分的两级分块,重叠窗口防边界信息丢失。
  - icon: 🔀
    title: 多模型自由切换
    details: 抽象 Provider 接口 + 工厂,LLM 与 Embedding 独立选择 OpenAI / Anthropic / Ollama / 智谱。
  - icon: 🗄️
    title: 本地向量存储
    details: ChromaDB 持久化到磁盘,cosine 相似度检索,ID 约定支持按文档整体删除与来源溯源。
  - icon: 🛡️
    title: 工程化容错
    details: 模型未配置时服务照常启动(懒加载单例);多文件入库单文件失败不互相影响。
  - icon: 🧪
    title: 可测试
    details: 分块、解析、检索核心逻辑均由 pytest 覆盖,向量库与模型调用可 mock。
---
