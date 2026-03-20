import { useEffect, useState } from 'react'
import {
  getConfig, updateConfig, runIngest, runEvaluate,
  type ConfigParams, type EvalReport, type IngestResult,
} from './api'

type Status = 'idle' | 'loading' | 'success' | 'error'

export default function Tuning() {
  const [config, setConfig] = useState<ConfigParams | null>(null)
  const [draft, setDraft] = useState<Partial<ConfigParams>>({})
  const [configStatus, setConfigStatus] = useState<Status>('idle')

  const [ingestStatus, setIngestStatus] = useState<Status>('idle')
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null)
  const [ingestClear, setIngestClear] = useState(true)

  const [evalStatus, setEvalStatus] = useState<Status>('idle')
  const [evalReport, setEvalReport] = useState<EvalReport | null>(null)

  const [retuneStatus, setRetuneStatus] = useState<Status>('idle')

  const [error, setError] = useState('')

  useEffect(() => {
    getConfig().then((c) => {
      setConfig(c)
      setDraft(c)
    }).catch((e) => setError(e.message))
  }, [])

  function handleDraftChange(key: keyof ConfigParams, value: string) {
    setDraft((prev) => ({ ...prev, [key]: key === 'rerank_threshold' ? parseFloat(value) : parseInt(value) }))
  }

  async function handleSaveConfig() {
    setConfigStatus('loading')
    try {
      const res = await updateConfig(draft)
      setConfig({ ...config!, ...res.updated })
      setConfigStatus('success')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setConfigStatus('error')
    }
  }

  async function handleIngest() {
    setIngestStatus('loading')
    setIngestResult(null)
    try {
      const res = await runIngest(ingestClear)
      setIngestResult(res)
      setIngestStatus('success')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setIngestStatus('error')
    }
  }

  async function handleEvaluate() {
    setEvalStatus('loading')
    setEvalReport(null)
    try {
      const res = await runEvaluate()
      setEvalReport(res.report)
      setEvalStatus('success')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setEvalStatus('error')
    }
  }

  async function handleRetune() {
    setRetuneStatus('loading')
    setError('')
    try {
      // 1. Save config
      await updateConfig(draft)
      // 2. Ingest
      setIngestStatus('loading')
      const ingestRes = await runIngest(true)
      setIngestResult(ingestRes)
      setIngestStatus('success')
      // 3. Evaluate
      setEvalStatus('loading')
      const evalRes = await runEvaluate()
      setEvalReport(evalRes.report)
      setEvalStatus('success')
      setRetuneStatus('success')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setRetuneStatus('error')
    }
  }

  const isRunning = ingestStatus === 'loading' || evalStatus === 'loading' || retuneStatus === 'loading'

  if (!config) return <div className="admin-page"><p>Loading...</p></div>

  const PARAM_FIELDS: { key: keyof ConfigParams; label: string; step?: string }[] = [
    { key: 'chunk_size', label: 'Chunk Size' },
    { key: 'chunk_overlap', label: 'Chunk Overlap' },
    { key: 'top_k', label: 'Top K' },
    { key: 'rerank_top_n', label: 'Rerank Top N' },
    { key: 'rerank_threshold', label: 'Rerank Threshold', step: '0.01' },
  ]

  return (
    <div className="admin-page">
      <h1>Evaluation & Tuning</h1>
      {error && <div className="admin-error">{error}</div>}

      {/* Parameters */}
      <div className="admin-section">
        <h2>Parameters</h2>
        <div className="admin-param-grid">
          {PARAM_FIELDS.map(({ key, label, step }) => (
            <label key={key} className="admin-param">
              <span>{label}</span>
              <input
                type="number"
                step={step || '1'}
                value={draft[key] ?? ''}
                onChange={(e) => handleDraftChange(key, e.target.value)}
                disabled={isRunning}
              />
            </label>
          ))}
        </div>
        <button
          className="admin-btn"
          onClick={handleSaveConfig}
          disabled={isRunning}
        >
          {configStatus === 'loading' ? 'Saving...' : 'Save Parameters'}
        </button>
      </div>

      {/* Actions */}
      <div className="admin-section">
        <h2>Actions</h2>
        <div className="admin-actions">
          <div className="admin-action-group">
            <label className="admin-checkbox">
              <input
                type="checkbox"
                checked={ingestClear}
                onChange={(e) => setIngestClear(e.target.checked)}
                disabled={isRunning}
              />
              Clear before ingest
            </label>
            <button className="admin-btn" onClick={handleIngest} disabled={isRunning}>
              {ingestStatus === 'loading' ? 'Ingesting...' : 'Run Ingest'}
            </button>
          </div>

          <button className="admin-btn" onClick={handleEvaluate} disabled={isRunning}>
            {evalStatus === 'loading' ? 'Evaluating...' : 'Run Evaluate'}
          </button>

          <button className="admin-btn admin-btn-primary" onClick={handleRetune} disabled={isRunning}>
            {retuneStatus === 'loading' ? 'Re-tuning...' : 'Re-tune (Save → Ingest → Evaluate)'}
          </button>
        </div>
      </div>

      {/* Ingest Result */}
      {ingestResult && (
        <div className="admin-section">
          <h2>Ingest Result</h2>
          <table className="admin-table">
            <thead>
              <tr><th>File</th><th>Chunks</th><th>Stored</th><th>Skipped</th></tr>
            </thead>
            <tbody>
              {ingestResult.details.map((d) => (
                <tr key={d.file}>
                  <td>{d.file}</td><td>{d.chunks}</td><td>{d.stored}</td><td>{d.skipped}</td>
                </tr>
              ))}
              <tr className="admin-table-total">
                <td>Total</td>
                <td>{ingestResult.total_chunks}</td>
                <td>{ingestResult.stored}</td>
                <td>{ingestResult.skipped}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Evaluation Result */}
      {evalReport && (
        <div className="admin-section">
          <h2>Evaluation Result</h2>
          <div className="admin-eval-summary">
            <span className="admin-score">
              {(evalReport.overall.rate * 100).toFixed(1)}%
            </span>
            <span>({evalReport.overall.passed}/{evalReport.overall.total} passed)</span>
          </div>

          <table className="admin-table">
            <thead>
              <tr><th>Type</th><th>Passed</th><th>Total</th><th>Rate</th></tr>
            </thead>
            <tbody>
              {Object.entries(evalReport.score_by_type).map(([type, s]) => (
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

          {evalReport.failed_cases.length > 0 && (
            <details className="admin-failed">
              <summary>Failed Cases ({evalReport.failed_cases.length})</summary>
              {evalReport.failed_cases.map((fc) => (
                <div key={fc.id} className="admin-failed-case">
                  <div className="admin-failed-id">[{fc.id}] {fc.type}</div>
                  <div><strong>Q:</strong> {fc.query}</div>
                  <div><strong>Expected:</strong> {fc.expected}</div>
                  <div><strong>Got:</strong> {fc.actual.slice(0, 200)}{fc.actual.length > 200 ? '...' : ''}</div>
                  {fc.keyword_missed.length > 0 && (
                    <div className="admin-missed">Missed: {fc.keyword_missed.join(', ')}</div>
                  )}
                </div>
              ))}
            </details>
          )}
        </div>
      )}
    </div>
  )
}
