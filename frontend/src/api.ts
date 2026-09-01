/** 后端 API 封装：统一错误处理与 JSON 解析。 */
import type { DocumentInfo, IngestionResult, QueryResponse, RagMode, Source } from './types'

const BASE = '/api'

class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError('无法连接后端服务，请确认服务已启动')
  }
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`
    try {
      const body = await resp.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* 忽略解析失败，保留默认信息 */
    }
    throw new ApiError(detail)
  }
  return resp.json() as Promise<T>
}

export function checkHealth(): Promise<{ status: string }> {
  return request('/health')
}

export function listDocuments(): Promise<{ documents: DocumentInfo[] }> {
  return request('/documents')
}

export function ingestDocuments(files: File[]): Promise<IngestionResult[]> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return request('/ingest', { method: 'POST', body: form })
}

export function deleteDocument(docId: string): Promise<{ status: string }> {
  return request(`/documents/${encodeURIComponent(docId)}`, { method: 'DELETE' })
}

export function query(
  question: string,
  topK?: number,
  mode: RagMode = 'custom',
): Promise<QueryResponse> {
  return request('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK, mode }),
  })
}

interface StreamHandlers {
  /** 收到检索来源（在首个回答增量之前触发一次） */
  onSources?: (sources: Source[]) => void
  /** 收到回答文本增量（流式过程中反复触发） */
  onDelta: (text: string) => void
}

/** 流式问答（SSE）：解析 data: 单行 JSON 事件帧，按类型分发给 handlers。 */
export async function queryStream(
  question: string,
  topK: number | undefined,
  mode: RagMode,
  handlers: StreamHandlers,
): Promise<void> {
  let resp: Response
  try {
    resp = await fetch(`${BASE}/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: topK, mode }),
    })
  } catch {
    throw new ApiError('无法连接后端服务，请确认服务已启动')
  }
  if (!resp.ok || !resp.body) {
    let detail = `请求失败 (${resp.status})`
    try {
      const body = await resp.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* 忽略解析失败，保留默认信息 */
    }
    throw new ApiError(detail)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const dispatch = (frame: string) => {
    const line = frame.trim()
    if (!line.startsWith('data:')) return
    let evt: { type: string; text?: string; sources?: Source[]; detail?: string; mode?: RagMode }
    try {
      evt = JSON.parse(line.slice(5).trim())
    } catch {
      return // 忽略非 JSON 帧
    }
    if (evt.type === 'sources' && evt.sources) handlers.onSources?.(evt.sources)
    else if (evt.type === 'delta' && typeof evt.text === 'string') handlers.onDelta(evt.text)
    else if (evt.type === 'error') throw new ApiError(evt.detail ?? '流式问答失败')
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? '' // 最后一段可能不完整，留到下一轮
    frames.forEach(dispatch)
  }
  if (buffer.trim()) dispatch(buffer)
}
