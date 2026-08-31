/** 后端 API 类型定义。 */

export interface Source {
  source: string
  content: string
  similarity: number
}

export interface QueryResponse {
  answer: string
  sources: Source[]
}

export interface DocumentInfo {
  doc_id: string
  source: string
  chunks: number
}

export interface IngestionResult {
  doc_id: string
  source: string
  chunks: number
  errors: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  sources?: Source[]
  error?: boolean
}
