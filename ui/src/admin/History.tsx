import { useEffect, useState } from 'react'
import { getEvalResults, type EvalResultSummary } from './api'

export default function History() {
  const [results, setResults] = useState<EvalResultSummary[]>([])
  const [selected, setSelected] = useState<EvalResultSummary | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getEvalResults()
      .then(setResults)
      .catch((e) => setError(e.message))
  }, [])

  return (
    <div className="admin-page">
      <h1>Evaluation History</h1>
      {error && <div className="admin-error">{error}</div>}

      {results.length === 0 ? (
        <p className="admin-muted">No evaluation results yet</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Score</th>
              <th>Passed</th>
              <th>chunk_size</th>
              <th>overlap</th>
              <th>top_k</th>
              <th>rerank_top_n</th>
              <th>threshold</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.file} className={selected?.file === r.file ? 'admin-row-selected' : ''}>
                <td>{r.date.slice(0, 19)}</td>
                <td className={r.overall.rate >= 0.5 ? 'text-pass' : 'text-fail'}>
                  {(r.overall.rate * 100).toFixed(1)}%
                </td>
                <td>{r.overall.passed}/{r.overall.total}</td>
                <td>{r.config_params.chunk_size}</td>
                <td>{r.config_params.chunk_overlap}</td>
                <td>{r.config_params.top_k}</td>
                <td>{r.config_params.rerank_top_n}</td>
                <td>{r.config_params.rerank_threshold}</td>
                <td>
                  <button
                    className="admin-btn-sm"
                    onClick={() => setSelected(selected?.file === r.file ? null : r)}
                  >
                    {selected?.file === r.file ? 'Close' : 'Detail'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <div className="admin-section">
          <h2>Score by Type — {selected.date.slice(0, 19)}</h2>
          <table className="admin-table">
            <thead>
              <tr><th>Type</th><th>Passed</th><th>Total</th><th>Rate</th></tr>
            </thead>
            <tbody>
              {Object.entries(selected.score_by_type).map(([type, s]) => (
                <tr key={type}>
                  <td>{type}</td>
                  <td>{s.passed}</td>
                  <td>{s.total}</td>
                  <td className={s.rate >= 0.5 ? 'text-pass' : 'text-fail'}>
                    {(s.rate * 100).toFixed(0)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Score comparison across runs */}
      {results.length >= 2 && (
        <div className="admin-section">
          <h2>Score Trend</h2>
          <div className="admin-trend">
            {[...results].reverse().map((r) => {
              const pct = r.overall.rate * 100
              return (
                <div key={r.file} className="admin-trend-bar">
                  <div
                    className="admin-trend-fill"
                    style={{ height: `${pct}%` }}
                    title={`${pct.toFixed(1)}% (${r.date.slice(0, 10)})`}
                  />
                  <span className="admin-trend-label">{pct.toFixed(0)}%</span>
                  <span className="admin-trend-date">{r.date.slice(5, 10)}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
