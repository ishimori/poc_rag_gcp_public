import { useEffect, useState } from 'react'
import { getConfig, getEvalResults, getChunks, type ConfigParams, type EvalResultSummary } from './api'

export default function Dashboard() {
  const [config, setConfig] = useState<ConfigParams | null>(null)
  const [latestEval, setLatestEval] = useState<EvalResultSummary | null>(null)
  const [chunkCount, setChunkCount] = useState<number | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setError('')
    Promise.all([
      getConfig().then(setConfig),
      getEvalResults().then((r) => setLatestEval(r[0] ?? null)),
      getChunks({ limit: 1 }).then((r) => setChunkCount(r.count > 0 ? null : 0)),
    ]).catch((e) => setError(e.message))

    // chunk count via larger request
    getChunks({ limit: 500 }).then((r) => setChunkCount(r.count)).catch(() => {})
  }, [])

  return (
    <div className="admin-page">
      <h1>Dashboard</h1>
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-cards">
        {/* Evaluation Score */}
        <div className="admin-card">
          <h3>Latest Evaluation</h3>
          {latestEval ? (
            <>
              <div className="admin-score">
                {(latestEval.overall.rate * 100).toFixed(1)}%
              </div>
              <div className="admin-score-detail">
                {latestEval.overall.passed}/{latestEval.overall.total} passed
              </div>
              <div className="admin-card-meta">{latestEval.date.slice(0, 19)}</div>
            </>
          ) : (
            <p className="admin-muted">No evaluation results</p>
          )}
        </div>

        {/* Chunk Count */}
        <div className="admin-card">
          <h3>Chunks</h3>
          <div className="admin-score">{chunkCount ?? '...'}</div>
          <div className="admin-score-detail">documents in Firestore</div>
        </div>

        {/* Current Config */}
        <div className="admin-card">
          <h3>Parameters</h3>
          {config ? (
            <table className="admin-config-table">
              <tbody>
                {Object.entries(config).map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="admin-muted">Loading...</p>
          )}
        </div>
      </div>

      {/* Score by type */}
      {latestEval && (
        <div className="admin-section">
          <h2>Score by Type</h2>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Passed</th>
                <th>Total</th>
                <th>Rate</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(latestEval.score_by_type).map(([type, s]) => (
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
    </div>
  )
}
