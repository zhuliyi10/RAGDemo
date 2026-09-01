import type { ChatMessage } from '../types'

export default function Message({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return <div className="bubble user">{message.text}</div>
  }
  return (
    <div className={`bubble assistant ${message.error ? 'error' : ''}`}>
      {message.mode && !message.error && (
        <span className={`mode-badge ${message.mode}`}>
          {message.mode === 'custom' ? '自研' : '框架'}
        </span>
      )}
      <div className="answer">{message.text}</div>
      {message.sources && message.sources.length > 0 && (
        <details className="sources">
          <summary>引用来源（{message.sources.length}）</summary>
          <ol>
            {message.sources.map((s, i) => (
              <li key={i}>
                <div className="source-meta">
                  {s.source} · 相似度 {s.similarity}
                </div>
                <blockquote>{s.content}</blockquote>
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  )
}
