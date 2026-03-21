import { useState, useRef, useEffect } from 'react'
import './App.css'

interface Source {
  content: string
  score: number
  source_file: string
  chunk_index: number
  category: string
  security_level: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  elapsedMs?: number
  model?: string
}

const MODELS = [
  {
    id: 'gemini-2.5-flash',
    label: 'Gemini 2.5 Flash',
    price: '$0.15 / $0.60',
    tier: '低コスト',
  },
  {
    id: 'gemini-2.5-pro',
    label: 'Gemini 2.5 Pro',
    price: '$1.25 / $10.00',
    tier: '高性能',
  },
]

const SAMPLE_QUESTIONS = [
  'ネジ999999の材質は？',
  'VPN接続の手順を教えて',
  'PCが重い',
  '有給休暇は何日もらえる？',
]

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState(MODELS[0].id)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(query: string) {
    if (!query.trim() || loading) return

    const userMsg: Message = { role: 'user', content: query }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const startTime = performance.now()

    try {
      const res = await fetch('/api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, model: selectedModel }),
      })

      if (!res.ok) throw new Error(`API error: ${res.status}`)

      const data = await res.json()
      const elapsedMs = Math.round(performance.now() - startTime)
      const modelInfo = MODELS.find((m) => m.id === selectedModel)

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        elapsedMs,
        model: modelInfo?.label,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (e) {
      const elapsedMs = Math.round(performance.now() - startTime)
      const errorMsg: Message = {
        role: 'assistant',
        content: `エラーが発生しました: ${e instanceof Error ? e.message : '不明なエラー'}`,
        elapsedMs,
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>エンタープライズRAG PoC</h1>
        <p>社内ドキュメントに基づいて質問に回答します</p>
        <a href="/admin" className="header-admin-link">Admin →</a>
      </header>

      <div className="main">
        <aside className="sidebar">
          <h3>モデル選択</h3>
          <p className="sidebar-hint">入力 / 出力（per 1M tokens）</p>
          {MODELS.map((m) => (
            <label
              key={m.id}
              className={`model-option ${selectedModel === m.id ? 'selected' : ''}`}
            >
              <input
                type="radio"
                name="model"
                value={m.id}
                checked={selectedModel === m.id}
                onChange={() => setSelectedModel(m.id)}
                disabled={loading}
              />
              <div className="model-info">
                <span className="model-name">{m.label}</span>
                <span className={`model-tier tier-${m.tier}`}>{m.tier}</span>
                <span className="model-price">{m.price}</span>
              </div>
            </label>
          ))}

          <div className="sidebar-divider" />

          <h3>質問の例</h3>
          {SAMPLE_QUESTIONS.map((q, i) => (
            <button
              key={i}
              className="sample-btn"
              onClick={() => handleSubmit(q)}
              disabled={loading}
            >
              {q}
            </button>
          ))}
        </aside>

        <div className="chat-area">
          <div className="messages">
            {messages.length === 0 && (
              <p className="empty">左のサンプル質問をクリックするか、下の入力欄から質問してください</p>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-content">{msg.content}</div>
                {msg.role === 'assistant' && (msg.elapsedMs || msg.model) && (
                  <div className="message-meta">
                    {msg.model && <span>{msg.model}</span>}
                    {msg.elapsedMs != null && <span>{formatElapsed(msg.elapsedMs)}</span>}
                  </div>
                )}
                {msg.sources && msg.sources.length > 0 && (
                  <SourceList sources={msg.sources} />
                )}
              </div>
            ))}
            {loading && (
              <div className="message assistant">
                <div className="message-content loading">検索・回答生成中...</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form
            className="input-area"
            onSubmit={(e) => {
              e.preventDefault()
              handleSubmit(input)
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="質問を入力してください"
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              送信
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}秒`
}

function SourceList({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="sources">
      <button className="sources-toggle" onClick={() => setOpen(!open)}>
        {open ? '▼' : '▶'} 参照ソース ({sources.length}件)
      </button>
      {open && (
        <ul className="sources-list">
          {sources.map((s, i) => (
            <li key={i}>
              <span className="source-file">
                {s.source_file}#{s.chunk_index}
              </span>
              <span className="source-score">score={s.score.toFixed(3)}</span>
              <p className="source-content">{s.content.slice(0, 120)}...</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
