import { useRef, useState } from 'react'
import type { DocumentInfo, IngestionResult } from '../types'
import { deleteDocument, ingestDocuments } from '../api'

interface Props {
  documents: DocumentInfo[]
  onChanged: () => void
}

const ACCEPT = '.txt,.md,.markdown,.pdf,.docx'

function summarize(results: IngestionResult[]): string {
  const ok = results.filter((r) => r.errors.length === 0)
  const failed = results.filter((r) => r.errors.length > 0)
  const parts: string[] = []
  if (ok.length) parts.push(`成功 ${ok.length} 个（共 ${ok.reduce((n, r) => n + r.chunks, 0)} 个分块）`)
  if (failed.length) parts.push(`失败: ${failed.map((r) => `${r.source}（${r.errors[0]}）`).join('、')}`)
  return parts.join('；') || '未处理任何文件'
}

export default function DocumentsPanel({ documents, onChanged }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleUpload = async () => {
    const fileList = inputRef.current?.files
    const files = fileList ? Array.from(fileList) : []
    if (files.length === 0) return
    setUploading(true)
    setError(null)
    setNotice(null)
    try {
      const results = await ingestDocuments(files)
      setNotice(summarize(results))
      if (inputRef.current) inputRef.current.value = ''
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId: string, source: string) => {
    if (!window.confirm(`确定删除「${source}」及其全部向量？`)) return
    setError(null)
    try {
      await deleteDocument(docId)
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <section className="panel documents-panel">
      <h2>知识库文档</h2>

      <div className="upload-row">
        <input ref={inputRef} type="file" multiple accept={ACCEPT} disabled={uploading} />
        <button onClick={handleUpload} disabled={uploading}>
          {uploading ? '入库中…' : '上传并入库'}
        </button>
      </div>
      <p className="hint">支持 txt / md / pdf / docx，可多选</p>

      {notice && <p className="notice">{notice}</p>}
      {error && <p className="error-text">{error}</p>}

      {documents.length === 0 ? (
        <p className="empty">知识库为空，请先上传文档</p>
      ) : (
        <ul className="doc-list">
          {documents.map((d) => (
            <li key={d.doc_id}>
              <span className="doc-name" title={d.source}>{d.source}</span>
              <span className="doc-chunks">{d.chunks} 块</span>
              <button className="link-danger" onClick={() => handleDelete(d.doc_id, d.source)}>
                删除
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
