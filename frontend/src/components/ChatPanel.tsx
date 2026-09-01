import { useEffect, useRef, useState } from 'react'
import type { ChatMessage, RagMode } from '../types'
import { queryStream } from '../api'
import Message from './Message'

const MODE_LABEL: Record<RagMode, string> = { custom: '自研', framework: '框架' }

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [topK, setTopK] = useState(4)
  const [mode, setMode] = useState<RagMode>('custom')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  // 是否「贴底跟随」：仅当用户本就停留在底部附近时才自动滚动，
  // 避免流式期间的高频滚动抢占用户手动拖拽/上翻的滚动位置。
  const stickToBottomRef = useRef(true)

  const handleScroll = () => {
    const el = listRef.current
    if (!el) return
    stickToBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  }

  useEffect(() => {
    // behavior 用 auto：流式期间每个增量都触发滚动，smooth 动画会被反复重启，
    // 既打断用户拖拽滚动条，也造成滚动卡顿感
    if (stickToBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'auto' })
    }
  }, [messages, loading])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return
    setInput('')
    stickToBottomRef.current = true // 发新消息时重新跟随最新回答
    // 占位消息：'…' 表示尚未收到任何增量
    setMessages((m) => [...m, { role: 'user', text: question }, { role: 'assistant', text: '…', mode }])
    setLoading(true)
    const patchLast = (patch: (prev: ChatMessage) => ChatMessage) => {
      setMessages((m) => {
        const next = [...m]
        next[next.length - 1] = patch(next[next.length - 1])
        return next
      })
    }
    try {
      await queryStream(question, topK, mode, {
        onSources: (sources) => patchLast((prev) => ({ ...prev, sources })),
        onDelta: (delta) =>
          patchLast((prev) => ({
            ...prev,
            text: (prev.text === '…' ? '' : prev.text) + delta,
          })),
      })
    } catch (e) {
      patchLast((prev) => ({
        ...prev,
        text: e instanceof Error ? e.message : String(e),
        error: true,
      }))
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

      <div className="messages" ref={listRef} onScroll={handleScroll}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>先在左侧上传文档，然后在这里提问。</p>
            <p className="hint">回答仅依据已入库的文档内容，并附引用来源。</p>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        {loading && messages[messages.length - 1]?.text === '…' && <div className="typing">生成中…</div>}
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
