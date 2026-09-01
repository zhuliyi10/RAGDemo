import { useEffect, useRef, useState } from 'react'
import type { ChatMessage, RagMode } from '../types'
import { query } from '../api'
import Message from './Message'

const MODE_LABEL: Record<RagMode, string> = { custom: '自研', framework: '框架' }

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [topK, setTopK] = useState(4)
  const [mode, setMode] = useState<RagMode>('custom')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: question }, { role: 'assistant', text: '…' }])
    setLoading(true)
    try {
      const r = await query(question, topK, mode)
      setMessages((m) => {
        const next = [...m]
        next[next.length - 1] = { role: 'assistant', text: r.answer, sources: r.sources, mode: r.mode ?? mode }
        return next
      })
    } catch (e) {
      setMessages((m) => {
        const next = [...m]
        next[next.length - 1] = {
          role: 'assistant',
          text: e instanceof Error ? e.message : String(e),
          error: true,
        }
        return next
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <section className="panel chat-panel">
      <div className="chat-toolbar">
        <h2>文档问答</h2>
        <div className="chat-controls">
          <div className="mode-switch" role="group" aria-label="问答模式">
            {(Object.keys(MODE_LABEL) as RagMode[]).map((m) => (
              <button
                key={m}
                type="button"
                className={mode === m ? 'active' : ''}
                disabled={loading}
                title={m === 'custom' ? '自研 pipeline（手写检索与生成编排）' : 'LangChain 框架模式（需安装框架依赖）'}
                onClick={() => setMode(m)}
              >
                {MODE_LABEL[m]}
              </button>
            ))}
          </div>
          <label className="topk">
            检索片段数
            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Math.max(1, Math.min(20, Number(e.target.value) || 4)))}
            />
          </label>
        </div>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>先在左侧上传文档，然后在这里提问。</p>
            <p className="hint">回答仅依据已入库的文档内容，并附引用来源。</p>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        {loading && <div className="typing">生成中…</div>}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          value={input}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          rows={2}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button onClick={() => void handleSend()} disabled={loading || !input.trim()}>
          发送
        </button>
      </div>
    </section>
  )
}
