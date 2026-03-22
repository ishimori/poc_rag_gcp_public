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
  isClarification?: boolean
}

// 検索時にON/OFF可能なRAG技術 — config APIと連携
// configKey: backend config.py の属性名。nullの場合は常時ON（切替不可）
const RAG_TECHNIQUES: { id: string; label: string; desc: string; configKey: string | null }[] = [
  { id: 'vector',      label: 'ベクトル検索',         desc: '意味の近さで候補を検索', configKey: null },
  { id: 'hybrid',      label: 'ハイブリッド検索',     desc: 'キーワード検索を併用し型番に強く', configKey: 'hybrid_search' },
  { id: 'reranking',   label: 'リランキング',         desc: 'AIが検索結果を再評価して絞り込み', configKey: null },
  { id: 'metadata',    label: 'メタデータスコアリング', desc: 'カテゴリやファイル名をランキングに反映', configKey: 'metadata_scoring' },
  { id: 'clarify',     label: '曖昧質問の聞き返し',   desc: '情報不足の質問にAIが確認質問', configKey: 'clarification' },
  { id: 'security',    label: '権限フィルタ',         desc: 'ユーザー権限で検索対象を制限', configKey: 'permission_filter' },
  { id: 'shadow',      label: '権限除外検出',         desc: '権限で弾かれた文書を検出し即拒否', configKey: 'shadow_retrieval' },
  { id: 'multiquery',  label: 'マルチクエリ展開',     desc: 'クエリを複数に言い換えて検索精度向上', configKey: 'multi_query' },
  { id: 'context',     label: '文脈説明の自動付与',   desc: 'チャンクにLLM生成の文脈説明を付与（再Ingest要）', configKey: 'contextual_retrieval' },
]

const USER_ROLES = [
  { id: 'general',   label: '一般社員',   groups: ['all'] },
  { id: 'hr_admin',  label: 'HR管理者',  groups: ['all', 'hr_admin'] },
  { id: 'executive', label: '役員',      groups: ['all', 'exec_board'] },
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
  const [selectedRole, setSelectedRole] = useState(USER_ROLES[0].id)
  const [techConfig, setTechConfig] = useState<Record<string, boolean>>({})
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // マウント時にconfigを取得
  useEffect(() => {
    fetch('/api/admin/config')
      .then((r) => r.json())
      .then((data) => {
        const boolKeys: Record<string, boolean> = {}
        for (const t of RAG_TECHNIQUES) {
          if (t.configKey && t.configKey in data) {
            boolKeys[t.configKey] = Boolean(data[t.configKey])
          }
        }
        setTechConfig(boolKeys)
      })
      .catch(() => {})
  }, [])

  async function handleTechToggle(configKey: string, value: boolean) {
    setTechConfig((prev) => ({ ...prev, [configKey]: value }))
    try {
      await fetch('/api/admin/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [configKey]: value }),
      })
    } catch {
      // 失敗時は元に戻す
      setTechConfig((prev) => ({ ...prev, [configKey]: !value }))
    }
  }

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
        body: JSON.stringify({
          query,
          model: selectedModel,
          user_groups: USER_ROLES.find((r) => r.id === selectedRole)!.groups,
        }),
      })

      if (!res.ok) throw new Error(`API error: ${res.status}`)

      const data = await res.json()
      const elapsedMs = Math.round(performance.now() - startTime)
      const modelInfo = MODELS.find((m) => m.id === selectedModel)

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.answer,
        sources: data.is_clarification ? undefined : data.sources,
        elapsedMs,
        model: modelInfo?.label,
        isClarification: data.is_clarification || false,
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
          <h3>検索エンジン</h3>
          <div className="engine-toggle">
            <label className={`engine-option ${(techConfig['use_vertex_ai_search'] ?? true) ? 'selected' : ''}`}>
              <input
                type="radio"
                name="engine"
                checked={techConfig['use_vertex_ai_search'] ?? true}
                onChange={() => handleTechToggle('use_vertex_ai_search', true)}
                disabled={loading}
              />
              <div className="engine-info">
                <span className="engine-name">Vertex AI Search</span>
                <span className="engine-desc">Google Cloud マネージド検索</span>
              </div>
            </label>
            <label className={`engine-option ${!(techConfig['use_vertex_ai_search'] ?? true) ? 'selected' : ''}`}>
              <input
                type="radio"
                name="engine"
                checked={!(techConfig['use_vertex_ai_search'] ?? true)}
                onChange={() => handleTechToggle('use_vertex_ai_search', false)}
                disabled={loading}
              />
              <div className="engine-info">
                <span className="engine-name">自前RAG</span>
                <span className="engine-desc">Firestore + 独自パイプライン</span>
              </div>
            </label>
          </div>

          <div className="sidebar-divider" />

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

          <h3>ロール選択</h3>
          <p className="sidebar-hint">検索時の権限レベルを切り替えます</p>
          <select
            className="role-select"
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            disabled={loading}
          >
            {USER_ROLES.map((r) => (
              <option key={r.id} value={r.id}>{r.label}</option>
            ))}
          </select>

          <div className="sidebar-divider" />

          <h3>検索技術</h3>
          <p className="sidebar-hint">質問時に使う技術を切り替えられます</p>
          <div className="tech-toggles">
            {RAG_TECHNIQUES.map((t) => {
              const isOn = t.configKey ? (techConfig[t.configKey] ?? false) : true
              const canToggle = t.configKey !== null
              return (
                <div
                  key={t.id}
                  className={`tech-toggle${canToggle ? '' : ' tech-always-on'}`}
                  title={t.desc}
                >
                  <input
                    type="checkbox"
                    checked={isOn}
                    disabled={!canToggle || loading}
                    onChange={(e) => canToggle && handleTechToggle(t.configKey!, e.target.checked)}
                  />
                  <div className="tech-toggle-info">
                    <span className="tech-toggle-name">{t.label}</span>
                    <span className="tech-toggle-desc">{t.desc}</span>
                  </div>
                </div>
              )
            })}
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
              <div key={i} className={`message ${msg.role}${msg.isClarification ? ' clarification' : ''}`}>
                {msg.isClarification && <div className="clarification-label">確認質問</div>}
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
