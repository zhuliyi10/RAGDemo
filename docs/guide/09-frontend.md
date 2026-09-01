# 第 7 步 · 前端界面

> 本章目标:给 RAG 服务加一个可视化界面 —— 左侧管理文档,右侧对话问答,回答可展开引用来源。技术栈 React 18 + TypeScript + Vite,不引 UI 组件库,样式手写 CSS。

## 工程结构

```
frontend/
├── package.json           # react 18 + vite 5 + typescript
├── vite.config.ts         # 开发期把 /api 代理到后端 8000
└── src/
    ├── api.ts             # 后端 API 封装(统一错误处理)
    ├── types.ts           # 与后端响应结构对应的类型
    ├── App.tsx            # 布局 + 全局状态(健康/文档列表)
    ├── main.tsx
    ├── styles.css
    └── components/
        ├── DocumentsPanel.tsx   # 文档上传 / 列表 / 删除
        ├── ChatPanel.tsx        # 对话输入与消息列表
        ├── Message.tsx          # 单条消息 + 引用来源展开
        └── HealthBadge.tsx      # 后端健康状态徽标
```

## 前后端如何联通

两条通道,开发与生产各一条:

**开发期 —— Vite 代理**(`vite.config.ts`):

```ts
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

**后端 —— CORS 正则放行本地端口**(`main.py`):

```python
allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+"
```

前端代码里只写 `const BASE = '/api'`,不感知端口与协议:开发时被 Vite 代理,生产部署时由静态服务器/网关反代 `/api`。

## 统一请求封装:`api.ts`

```ts
class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError('无法连接后端服务,请确认服务已启动')
  }
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`
    try {
      const body = await resp.json()
      if (typeof body?.detail === 'string') detail = body.detail   // 透出后端信息
    } catch { /* 保留默认信息 */ }
    throw new ApiError(detail)
  }
  return resp.json() as Promise<T>
}
```

- **连接失败与 HTTP 错误分开**:前者是「服务没起」,后者尽量透出后端 `detail`(如「未配置 ZHIPU_API_KEY」)
- 之上包出五个类型化函数:`checkHealth` / `listDocuments` / `ingestDocuments`(FormData 多文件)/ `deleteDocument` / `query`

## 全局状态:`App.tsx`

```tsx
export default function App() {
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])

  // 健康轮询:每 15s 一次
  useEffect(() => {
    const ping = () =>
      checkHealth().then(() => setHealthy(true)).catch(() => setHealthy(false))
    ping()
    const timer = setInterval(ping, 15000)
    return () => clearInterval(timer)
  }, [])

  // 文档列表加载;上传/删除后由子组件回调刷新
  const refreshDocuments = useCallback(() => {
    listDocuments().then((r) => setDocuments(r.documents)).catch(() => setDocuments([]))
  }, [])

  return (
    <main className="app-main">
      <DocumentsPanel documents={documents} onChanged={refreshDocuments} />
      <ChatPanel />
    </main>
  )
}
```

状态设计:文档列表提升到 App 层,因为**上传(DocumentsPanel)与问答引用(ChatPanel)都会改变/依赖知识库状态**,由父组件统一刷新。

## 组件职责

| 组件 | 职责 | 关键交互 |
|---|---|---|
| `DocumentsPanel` | 文件上传(多选)、文档列表(含分块数)、删除 | 调 `ingestDocuments` 后逐项展示 `errors`,成功即回调 `onChanged` |
| `ChatPanel` | 问题输入、**模式切换(自研/框架)**、`top_k` 选择、消息流 | 调 `query(question, topK, mode)`,把 `answer` 与 `sources` 一起渲染 |
| `Message` | 单条回答 | **引用来源可展开**:来源文件名 + 片段原文 + 相似度;回答附**模式徽标** |
| `HealthBadge` | 顶部健康徽标 | 绿/灰由 App 的 15s 轮询驱动 |

「引用展开」是 RAG 界面的点睛之笔:用户能看到「这个答案依据的是哪个文件的哪些片段、相似度多少」,幻觉与否一目了然。

## 模式切换:自研 vs 框架

`ChatPanel` 工具栏里有一组分段开关,选定 `mode` 随请求发送(状态保留在组件内,切换只影响下一次提问):

```tsx
const [mode, setMode] = useState<RagMode>('custom')

<div className="mode-switch" role="group" aria-label="问答模式">
  <button className={mode === 'custom' ? 'active' : ''} onClick={() => setMode('custom')}>
    自研
  </button>
  <button className={mode === 'framework' ? 'active' : ''} onClick={() => setMode('framework')}>
    框架
  </button>
</div>
```

- 每条回答来自后端回传的 `mode`,在气泡上渲染成小徽标 —— 同一问题用两种模式各问一遍,回答差异一目了然
- 后端未安装 LangChain 时选「框架」,错误信息(含安装指引)照常透出在错误气泡里,前端无需感知依赖状态

## 生产构建

```bash
cd frontend && npm install && npm run build   # 产出 dist/,tsc 类型检查 + vite 打包
```

`dist/` 是纯静态文件,任意静态服务器或网关托管,只需把 `/api` 反代到后端即可。

下一步 → [第 8 步 · 测试与运行](/guide/10-testing)
