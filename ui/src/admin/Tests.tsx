import { useEffect, useState } from 'react'
import { getEvalCases, type EvalCase } from './api'

export default function Tests() {
  const [cases, setCases] = useState<EvalCase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Filters
  const [typeFilter, setTypeFilter] = useState('')
  const [requiresFilter, setRequiresFilter] = useState('')

  useEffect(() => {
    getEvalCases()
      .then((res) => setCases(res.cases))
      .catch((e) => setError(e instanceof Error ? e.message : 'Unknown error'))
      .finally(() => setLoading(false))
  }, [])

  const types = [...new Set(cases.map((c) => c.type))].sort()
  const requiresValues = [...new Set(cases.map((c) => c.requires).filter(Boolean))].sort()

  const filtered = cases.filter((c) => {
    if (typeFilter && c.type !== typeFilter) return false
    if (requiresFilter === '_none' && c.requires) return false
    if (requiresFilter && requiresFilter !== '_none' && c.requires !== requiresFilter) return false
    return true
  })

  if (loading) return <div className="admin-page"><p>Loading...</p></div>

  return (
    <div className="admin-page-wide">
      <h1>Test Cases</h1>
      <p className="admin-section-desc">
        精度評価（Evaluate）で使用するテストケースの一覧です。
        各ケースには質問・期待回答・判定キーワードが定義されており、RAGの回答品質を自動測定します。
        「requires」が設定されたケースは、該当機能が未実装の間はスキップされます。
      </p>
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-section">
        <div className="data-filters">
          <label className="admin-param">
            <span>タイプ</span>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="">すべて</option>
              {types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label className="admin-param">
            <span>前提機能</span>
            <select value={requiresFilter} onChange={(e) => setRequiresFilter(e.target.value)}>
              <option value="">すべて</option>
              <option value="_none">なし（常に実行）</option>
              {requiresValues.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </label>
          <span className="admin-muted">{filtered.length} / {cases.length} 件</span>
        </div>
      </div>

      <div className="admin-section">
        <div className="data-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>タイプ</th>
                <th>質問</th>
                <th>期待回答</th>
                <th>キーワード</th>
                <th>前提機能</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id}>
                  <td style={{ whiteSpace: 'nowrap', fontWeight: 600, fontSize: '0.8rem' }}>{c.id}</td>
                  <td>
                    <span className={`data-tag tag-${c.type}`}>{c.type}</span>
                  </td>
                  <td style={{ maxWidth: 300, fontSize: '0.82rem' }}>{c.query}</td>
                  <td style={{ maxWidth: 250, fontSize: '0.78rem', color: '#555' }}>{c.expected_answer}</td>
                  <td style={{ maxWidth: 200, fontSize: '0.75rem', color: '#888' }}>
                    {c.expected_keywords.join(', ')}
                  </td>
                  <td>
                    {c.requires
                      ? <span className="data-tag tag-hr">{c.requires}</span>
                      : <span style={{ color: '#ccc' }}>—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
