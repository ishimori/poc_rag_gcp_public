import { useEffect, useState } from 'react'
import { getEvalResults, type EvalResultSummary, type ConfigParams } from './api'

export default function History() {
  const [results, setResults] = useState<EvalResultSummary[]>([])
  const [selected, setSelected] = useState<EvalResultSummary | null>(null)
  const [error, setError] = useState('')

  const [beforeFile, setBeforeFile] = useState<string | null>(null)
  const [afterFile, setAfterFile] = useState<string | null>(null)

  useEffect(() => {
    getEvalResults()
      .then(setResults)
      .catch((e) => setError(e.message))
  }, [])

  const compareResults = beforeFile && afterFile
    ? { before: results.find((r) => r.file === beforeFile)!, after: results.find((r) => r.file === afterFile)! }
    : null

  return (
    <div className="admin-page">
      <h1>Evaluation History</h1>
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-guide">
        <strong>使い方:</strong> 2件にチェック ☑ を入れると、パラメータの変更点とスコアの増減が比較表示されます。Δ列の緑は改善、赤は悪化を示します。
      </div>

      {results.length === 0 ? (
        <p className="admin-muted">No evaluation results yet</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th style={{ textAlign: 'center', fontSize: '0.8em' }}>Before</th>
              <th style={{ textAlign: 'center', fontSize: '0.8em' }}>After</th>
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
                <td style={{ textAlign: 'center' }}>
                  <input
                    type="radio"
                    name="compare-before"
                    checked={beforeFile === r.file}
                    onChange={() => setBeforeFile(beforeFile === r.file ? null : r.file)}
                  />
                </td>
                <td style={{ textAlign: 'center' }}>
                  <input
                    type="radio"
                    name="compare-after"
                    checked={afterFile === r.file}
                    onChange={() => setAfterFile(afterFile === r.file ? null : r.file)}
                  />
                </td>
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

      {/* Compare */}
      {compareResults && (
        <div className="admin-section">
          <h2>Compare</h2>
          <CompareView before={compareResults.before} after={compareResults.after} />
        </div>
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


function DeltaPct({ a, b }: { a: number; b: number }) {
  const diff = Math.round((b - a) * 100)
  if (diff === 0) return <span style={{ color: '#888' }}>±0%</span>
  const sign = diff > 0 ? '+' : ''
  const color = diff > 0 ? '#1e7e34' : '#c5221f'
  return <span style={{ color, fontWeight: 600 }}>{sign}{diff}%</span>
}

function CompareView({ before, after }: { before: EvalResultSummary; after: EvalResultSummary }) {
  const a = after
  const b = before
  const PARAM_KEYS: { key: keyof ConfigParams; label: string }[] = [
    { key: 'chunk_size', label: 'Chunk Size' },
    { key: 'chunk_overlap', label: 'Chunk Overlap' },
    { key: 'top_k', label: 'Top K' },
    { key: 'rerank_top_n', label: 'Rerank Top N' },
    { key: 'rerank_threshold', label: 'Rerank Threshold' },
  ]

  const allTypes = Array.from(new Set([
    ...Object.keys(a.score_by_type),
    ...Object.keys(b.score_by_type),
  ])).sort()

  // --- Auto interpretation ---
  const changedParams = PARAM_KEYS.filter(({ key }) => a.config_params[key] !== b.config_params[key])
  const overallDiff = Math.round((after.overall.rate - before.overall.rate) * 100)
  const improved = allTypes.filter((t) => {
    const rb = before.score_by_type[t]?.rate ?? 0
    const ra = after.score_by_type[t]?.rate ?? 0
    return ra - rb >= 0.1
  })
  const degraded = allTypes.filter((t) => {
    const rb = before.score_by_type[t]?.rate ?? 0
    const ra = after.score_by_type[t]?.rate ?? 0
    return rb - ra >= 0.1
  })

  // newer = a (top of list = most recent)
  const changeDesc = changedParams.length === 0
    ? 'パラメータの変更なし'
    : changedParams.map(({ key, label }) => `${label}: ${before.config_params[key]} → ${after.config_params[key]}`).join('、')

  const testCountChanged = before.overall.total !== after.overall.total

  let verdict: { text: string; color: string }
  if (testCountChanged) {
    verdict = {
      text: `テストケース数が ${before.overall.total}件 → ${after.overall.total}件 に変更されています。スコアの単純比較はできません。各Typeごとの増減を確認してください。`,
      color: '#b45309',
    }
  } else if (overallDiff > 0) {
    verdict = { text: `この変更は効果的です（+${overallDiff}%）。この設定を維持しましょう。`, color: '#1e7e34' }
  } else if (overallDiff < 0) {
    verdict = { text: `この変更でスコアが${Math.abs(overallDiff)}%低下しました。元の設定に戻すことを検討してください。`, color: '#c5221f' }
  } else {
    verdict = { text: 'スコアに変化はありません。他のパラメータを試してみましょう。', color: '#555' }
  }

  return (
    <div>
      {/* Interpretation */}
      <div style={{ padding: '12px 16px', marginBottom: 16, borderRadius: 6, background: testCountChanged ? '#fef9e7' : overallDiff > 0 ? '#e6f4ea' : overallDiff < 0 ? '#fce8e6' : '#f1f3f4' }}>
        <div style={{ marginBottom: 6 }}>
          <strong>変更内容:</strong> {changeDesc}
        </div>
        <div style={{ marginBottom: 6, color: verdict.color, fontWeight: 600 }}>
          {verdict.text}
        </div>
        {improved.length > 0 && (
          <div style={{ color: '#1e7e34', fontSize: '0.9em' }}>
            改善: {improved.join(', ')}
          </div>
        )}
        {degraded.length > 0 && (
          <div style={{ color: '#c5221f', fontSize: '0.9em' }}>
            悪化: {degraded.join(', ')}
          </div>
        )}
      </div>

      {/* Parameter diff */}
      <h3 style={{ marginBottom: 4 }}>Parameters</h3>
      <table className="admin-table" style={{ marginBottom: 16 }}>
        <thead>
          <tr>
            <th>Parameter</th>
            <th style={{ textAlign: 'right' }}>Before ({before.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>After ({after.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>Diff</th>
          </tr>
        </thead>
        <tbody>
          {PARAM_KEYS.map(({ key, label }) => {
            const vb = before.config_params[key]
            const va = after.config_params[key]
            const changed = vb !== va
            return (
              <tr key={key} style={changed ? { background: '#fffde7' } : {}}>
                <td>{label}</td>
                <td style={{ textAlign: 'right' }}>{vb}</td>
                <td style={{ textAlign: 'right' }}>{va}</td>
                <td style={{ textAlign: 'right' }}>
                  {changed
                    ? <span style={{ color: '#1a56db', fontWeight: 600 }}>{typeof va === 'number' && typeof vb === 'number' ? (va > vb ? '↑' : '↓') : '≠'}</span>
                    : <span style={{ color: '#ccc' }}>—</span>}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* Score diff */}
      <h3 style={{ marginBottom: 4 }}>Scores</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Type</th>
            <th style={{ textAlign: 'right' }}>Before ({before.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>After ({after.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ fontWeight: 600 }}>
            <td>Overall</td>
            <td style={{ textAlign: 'right' }}>{(before.overall.rate * 100).toFixed(0)}% ({before.overall.passed}/{before.overall.total})</td>
            <td style={{ textAlign: 'right' }}>{(after.overall.rate * 100).toFixed(0)}% ({after.overall.passed}/{after.overall.total})</td>
            <td style={{ textAlign: 'right' }}><DeltaPct a={before.overall.rate} b={after.overall.rate} /></td>
          </tr>
          {allTypes.map((type) => {
            const sb = before.score_by_type[type] ?? { passed: 0, total: 0, rate: 0 }
            const sa = after.score_by_type[type] ?? { passed: 0, total: 0, rate: 0 }
            return (
              <tr key={type}>
                <td>{type}</td>
                <td style={{ textAlign: 'right' }}>{(sb.rate * 100).toFixed(0)}% ({sb.passed}/{sb.total})</td>
                <td style={{ textAlign: 'right' }}>{(sa.rate * 100).toFixed(0)}% ({sa.passed}/{sa.total})</td>
                <td style={{ textAlign: 'right' }}><DeltaPct a={sb.rate} b={sa.rate} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
