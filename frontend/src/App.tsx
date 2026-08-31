import { useCallback, useEffect, useState } from 'react'
import type { DocumentInfo } from './types'
import { checkHealth, listDocuments } from './api'
import ChatPanel from './components/ChatPanel'
import DocumentsPanel from './components/DocumentsPanel'
import HealthBadge from './components/HealthBadge'

export default function App() {
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])

  const refreshDocuments = useCallback(() => {
    listDocuments()
      .then((r) => setDocuments(r.documents))
      .catch(() => setDocuments([]))
  }, [])

  useEffect(() => {
    const ping = () =>
      checkHealth()
        .then(() => setHealthy(true))
        .catch(() => setHealthy(false))
    ping()
    const timer = setInterval(ping, 15000)
    return () => clearInterval(timer)
  }, [])

  useEffect(refreshDocuments, [refreshDocuments])

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>RAGDemo</h1>
          <p className="subtitle">自研轻量 RAG · 文档问答</p>
        </div>
        <HealthBadge healthy={healthy} />
      </header>

      <main className="app-main">
        <DocumentsPanel documents={documents} onChanged={refreshDocuments} />
        <ChatPanel />
      </main>
    </div>
  )
}
