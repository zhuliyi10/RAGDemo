import { defineConfig } from 'vitepress'

// RAGDemo 技术文档站:「从 0 到 1 实现 RAG」分章教程
export default defineConfig({
  lang: 'zh-CN',
  title: 'RAGDemo',
  description: '从 0 到 1 实现一个自研轻量 RAG(检索增强生成)服务',
  lastUpdated: true,

  themeConfig: {
    siteTitle: 'RAGDemo',
    outline: { level: [2, 3], label: '本页目录' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '目录',
    search: { provider: 'local' },

    nav: [
      { text: '教程', link: '/guide/01-overview' },
      { text: 'GitHub', link: 'https://github.com/zhuliyi10/RAGDemo' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: '开始之前',
          items: [
            { text: '项目概述:我们要做什么', link: '/guide/01-overview' },
            { text: '原理与架构设计', link: '/guide/02-design' },
          ],
        },
        {
          text: '从 0 到 1 实现',
          items: [
            { text: '第 1 步 · 初始化与配置', link: '/guide/03-setup' },
            { text: '第 2 步 · 模型抽象层', link: '/guide/04-provider' },
            { text: '第 3 步 · 文档解析与分块', link: '/guide/05-ingestion' },
            { text: '第 4 步 · 向量化与存储', link: '/guide/06-vector' },
            { text: '第 5 步 · 检索与生成', link: '/guide/07-rag' },
            { text: '第 6 步 · REST API', link: '/guide/08-api' },
            { text: '第 7 步 · 前端界面', link: '/guide/09-frontend' },
            { text: '第 8 步 · 测试与运行', link: '/guide/10-testing' },
          ],
        },
        {
          text: '进阶',
          items: [
            { text: '设计决策复盘', link: '/guide/11-advanced' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/zhuliyi10/RAGDemo' },
    ],
  },
})
