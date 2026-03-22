import { useCallback, useEffect, useState } from 'react'
import { getLogs, type QueryLog } from './api'

export default function Logs() {
  const [logs, setLogs] = useState<QueryLog[]>([])
  const [count, setCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Filters
  const [noAnswerOnly, setNoAnswerOnly] = useState(false)
  const [limit, setLimit] = useState(50)

  // Detail
  const [selected, setSelected] = useState<QueryLog | null>(null)

  const handleFetch = useCallback(async () => {
    setLoading(true)
    setError('')
    setSelected(null)
    try {
      const res = await getLogs({
        no_answer: noAnswerOnly || undefined,
        limit,
      })
      setLogs(res.logs)
      setCount(res.count)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [noAnswerOnly, limit])

  useEffect(() => {
    handleFetch()
  }, [handleFetch])

  function formatTimestamp(ts: string | null) {
    if (!ts) return '-'
    const d = new Date(ts)
    return d.toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' })
  }

  return (
    <div className="admin-page-wide">
      <h1>Query Logs</h1>
      {error && <div className="admin-error">{error}</div>}

      {/* Filters */}
      <div className="admin-section">
        <h2>Filters</h2>
        <div className="data-filters">
          <label className="admin-param admin-checkbox">
            <input
              type="checkbox"
              checked={noAnswerOnly}
              onChange={(e) => setNoAnswerOnly(e.target.checked)}
            />
            <span>No Answer only</span>
          </label>
          <label className="admin-param">
            <span>Limit</span>
            <input
              type="number"
              min={1}
              max={200}
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value) || 50)}
            />
          </label>
          <button className="admin-btn admin-btn-primary" onClick={handleFetch} disabled={loading}>
            {loading ? 'Loading...' : 'Fetch Logs'}
          </button>
        </div>
      </div>

      {/* Summary */}
      {count !== null && (
        <div className="admin-section">
          <div className="admin-cards">
            <div className="admin-card">
              <div className="admin-card-value">{count}</div>
              <div className="admin-card-label">Total Logs</div>
            </div>
            <div className="admin-card">
              <div className="admin-card-value">{logs.filter(l => l.no_answer).length}</div>
              <div className="admin-card-label">No Answer</div>
            </div>
            <div className="admin-card">
              <div className="admin-card-value">
                {count > 0 ? (logs.reduce((s, l) => s + l.elapsed_ms, 0) / count / 1000).toFixed(1) : 0}s
              </div>
              <div className="admin-card-label">Avg Response</div>
            </div>
          </div>
        </div>
      )}

      {/* Results + Detail side-by-side */}
      {count !== null && (
        <div className="logs-split" style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          {/* Left: Log list */}
          <div className="admin-section" style={{ flex: selected ? '0 0 50%' : '1 1 100%', minWidth: 0, transition: 'flex 0.2s' }}>
            <h2>Logs ({count})</h2>
            <div className="data-table-wrap" style={{ maxHeight: 'calc(100vh - 300px)', overflowY: 'auto' }}>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Query</th>
                    <th>Engine</th>
                    <th>Collection</th>
                    <th>Time</th>
                    <th>No Answer</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      className={`data-row ${selected?.id === log.id ? 'admin-row-selected' : ''}`}
                      onClick={() => setSelected(selected?.id === log.id ? null : log)}
                    >
                      <td style={{ whiteSpace: 'nowrap', fontSize: '0.8rem' }}>{formatTimestamp(log.timestamp)}</td>
                      <td className="data-preview" style={{ maxWidth: 300 }}>{log.query.length > 40 ? log.query.slice(0, 40) + '…' : log.query}</td>
                      <td style={{ fontSize: '0.75rem', fontWeight: 600, color: log.techniques?.use_vertex_ai_search ? '#1a73e8' : '#666' }}>{log.techniques?.use_vertex_ai_search ? 'Vertex' : '自前'}</td>
                      <td style={{ fontSize: '0.8rem', color: '#666' }}>{log.collection || '-'}</td>
                      <td style={{ textAlign: 'right' }}>{(log.elapsed_ms / 1000).toFixed(1)}s</td>
                      <td>{log.no_answer ? <span className="text-fail">Yes</span> : <span className="text-pass">No</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right: Detail panel */}
          {selected && (
            <div className="admin-section" style={{ flex: '0 0 48%', minWidth: 0, position: 'sticky', top: 16, maxHeight: 'calc(100vh - 100px)', overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h2 style={{ margin: 0 }}>Detail</h2>
                <button className="admin-btn-sm" onClick={() => setSelected(null)}>✕ 閉じる</button>
              </div>
              <table className="admin-config-table" style={{ marginBottom: 12 }}>
                <tbody>
                  <tr><td>ID</td><td>{selected.id}</td></tr>
                  <tr><td>Timestamp</td><td>{formatTimestamp(selected.timestamp)}</td></tr>
                  <tr><td>Collection</td><td>{selected.collection || '-'}</td></tr>
                  <tr><td>Model</td><td>{selected.model || '-'}</td></tr>
                  <tr><td>Elapsed</td><td>{(selected.elapsed_ms / 1000).toFixed(1)}s</td></tr>
                  <tr><td>No Answer</td><td>{selected.no_answer ? 'Yes' : 'No'}</td></tr>
                </tbody>
              </table>
              {selected.techniques && (
                <>
                  <h3 style={{ marginBottom: 4 }}>Techniques</h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 8px', marginBottom: 12 }}>
                    {Object.entries(selected.techniques).map(([key, on]) => (
                      <span key={key} style={{ fontSize: '0.8rem', opacity: on ? 1 : 0.4 }}>
                        {on ? '✓' : '✗'} {key}
                      </span>
                    ))}
                  </div>
                </>
              )}
              <h3 style={{ marginBottom: 4 }}>Sources ({selected.source_count})</h3>
              <table className="admin-table" style={{ marginBottom: 12 }}>
                <thead>
                  <tr><th>File</th><th>Score</th></tr>
                </thead>
                <tbody>
                  {selected.sources.map((s, i) => {
                    const file = typeof s === 'string' ? s : s.file
                    const score = typeof s === 'string' ? null : s.score
                    return (
                      <tr key={i}>
                        <td>{file}</td>
                        <td style={{ textAlign: 'right' }}>{score !== null ? score.toFixed(3) : '-'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <h3 style={{ marginBottom: 4 }}>Query</h3>
              <div className="data-content-full" style={{ marginBottom: 12 }}>
                {selected.query}
              </div>
              <h3 style={{ marginBottom: 4 }}>Answer</h3>
              <div className="data-content-full">
                {selected.answer}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
