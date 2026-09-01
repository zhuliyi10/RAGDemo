/** 后端 API 封装：统一错误处理与 JSON 解析。 */
import type { DocumentInfo, IngestionResult, QueryResponse, RagMode } from './types'

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
