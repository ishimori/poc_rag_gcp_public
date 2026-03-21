import { useState, useRef, useEffect } from 'react'
import Markdown from 'react-markdown'
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

// 検索時にON/OFF可能なRAG技術（モックアップ: UIのみ、バックエンド未連携）
// ※ Ingest時に決まる技術（チャンキング、ヘッダー注入、文脈説明）はTuning画面で管理
const RAG_TECHNIQUES = [
  { id: 'vector',      label: 'ベクトル検索',         desc: '意味の近さで候補を検索', enabled: true },
  { id: 'reranking',   label: 'リランキング',         desc: 'AIが検索結果を再評価して絞り込み', enabled: true },
  { id: 'hybrid',      label: 'ハイブリッド検索',     desc: 'キーワード検索を併用し型番に強く', enabled: false },
  { id: 'metadata',    label: 'メタデータスコアリング', desc: '更新日やカテゴリをランキングに反映', enabled: false },
  { id: 'selfquery',   label: 'AIフィルタ自動生成',   desc: '条件を自動抽出して検索を絞り込み', enabled: false },
  { id: 'routing',     label: 'インテントルーティング', desc: '質問の種類に応じて検索方法を自動切替', enabled: false },
  { id: 'clarify',     label: '曖昧質問の聞き返し',   desc: '情報不足の質問にAIが確認質問', enabled: false },
  { id: 'security',    label: '権限フィルタ',         desc: 'ユーザー権限で検索対象を制限', enabled: false },
]

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

const DATA_CATEGORIES = [
  {
    label: '部品・製造',
    docs: ['部品カタログ', '部品仕様書×4', '品質基準', '新製品情報'],
    questions: [
      'ネジ999999と999998の違いは？',
      'SUS316Lのボルトの部品番号は？',
      'M8ボルトの締付トルクは？',
      'ネジ999999と一緒に必要な部品は？',
      '品質検査の等級Aの引張強さの基準は？',
      '不良品が見つかったら何をする？',
      '新製品のCorrGuardとは何？',
    ],
  },
  {
    label: 'IT・インフラ',
    docs: ['ヘルプデスクFAQ', 'VPNマニュアル', 'PC障害対応', 'ネットワーク規程', 'セキュリティポリシー'],
    questions: [
      'VPNが繋がらない原因を全て教えて',
      'リモートワークに必要な準備を全部教えて',
      '社内Wi-FiのSSIDは？ゲスト用との違いは？',
      'PCが重い',
      'パスワードの条件は？',
      '機密情報をメールで送っていいか？',
      '社外秘の書類を捨てたい',
    ],
  },
  {
    label: '人事・総務・経理',
    docs: ['休暇規程', '給与規程', '経費精算マニュアル', '入社ガイド', '組織図'],
    questions: [
      '入社初日にやることを全部教えて',
      '経費精算の手順を教えて',
      '5万円の経費は誰が最終承認する？',
      'タクシー代を会社に請求したい',
      '有給休暇は何日もらえる？入社3年目です',
      '情報システム部の部長は誰？',
    ],
  },
]

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState(MODELS[0].id)
  // 検索技術トグル（モックアップ: UI表示のみ、切り替え機能は未実装）
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

          <h3>検索技術</h3>
          <p className="sidebar-hint">質問時に使う技術を切り替えられます（実装予定）</p>
          <div className="tech-toggles">
            {RAG_TECHNIQUES.map((t) => (
              <div
                key={t.id}
                className="tech-toggle tech-not-impl"
                title={t.desc}
              >
                <input
                  type="checkbox"
                  checked={t.enabled}
                  disabled
                />
                <div className="tech-toggle-info">
                  <span className="tech-toggle-name">{t.label}</span>
                  <span className="tech-toggle-desc">{t.desc}</span>
                </div>
              </div>
            ))}
          </div>

          {messages.length > 0 && (
            <>
              <div className="sidebar-divider" />
              <button
                className="new-chat-btn"
                onClick={() => setMessages([])}
                disabled={loading}
              >
                新しい質問
              </button>
            </>
          )}
        </aside>

        <div className="chat-area">
          <div className="messages">
            {messages.length === 0 && (
              <div className="welcome">
                <h3 className="welcome-title">収録データと質問例</h3>
                <p className="welcome-hint">19件の社内ドキュメントを収録しています。質問ボタンをクリックして試せます。</p>
                <div className="category-grid">
                  {DATA_CATEGORIES.map((cat) => (
                    <div key={cat.label} className="category-card">
                      <h4 className="category-label">{cat.label}</h4>
                      <ul className="category-docs">
                        {cat.docs.map((doc, i) => (
                          <li key={i}>{doc}</li>
                        ))}
                      </ul>
                      <div className="category-questions">
                        <span className="category-q-label">質問してみよう</span>
                        {cat.questions.map((q, i) => (
                          <button
                            key={i}
                            className="sample-btn"
                            onClick={() => handleSubmit(q)}
                            disabled={loading}
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-content"><Markdown>{msg.content}</Markdown></div>
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
