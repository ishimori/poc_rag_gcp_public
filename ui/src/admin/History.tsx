import { useEffect, useState } from 'react'
import { getEvalResults, type EvalResultSummary, type ConfigParams } from './api'

const PARAM_LABEL: Record<string, string> = {
  chunk_size: '分割サイズ',
  chunk_overlap: '重複幅',
  top_k: '検索件数',
  rerank_top_n: '絞り込み件数',
  rerank_threshold: '足切りスコア',
}

function describeChanges(current: EvalResultSummary, prev: EvalResultSummary | undefined): string {
  if (!prev) return '（初回実行）'
  const diffs: string[] = []
  if (prev.overall.total !== current.overall.total) {
    diffs.push(`テストケース ${prev.overall.total}→${current.overall.total}件`)
  }
  for (const key of Object.keys(PARAM_LABEL) as (keyof ConfigParams)[]) {
    if (current.config_params[key] !== prev.config_params[key]) {
      diffs.push(`${PARAM_LABEL[key]} ${prev.config_params[key]}→${current.config_params[key]}`)
    }
  }
  return diffs.length === 0 ? '—' : diffs.join('、')
}

const TYPE_LABELS: Record<string, string> = {
  exact_match:      '完全一致',
  similar_number:   '類似数値の区別',
  semantic:         '意味検索',
  step_sequence:    '手順再現',
  multi_chunk:      '複数チャンク統合',
  unanswerable:     '回答不能判定',
  ambiguous:        '曖昧質問対応',
  cross_category:   'カテゴリ横断',
  security:         'セキュリティ',
  noise_resistance: 'ノイズ耐性',
  table_extract:    '表データ抽出',
  temporal:         '時系列判定',
}

function TypeName({ type }: { type: string }) {
  const label = TYPE_LABELS[type]
  if (!label) return <>{type}</>
  return <><span className="type-name">{label}</span><span className="type-key">{type}</span></>
}

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
      <h1>評価履歴</h1>
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-guide">
        <strong>この画面について:</strong> RAGは「文書を分割 → 検索 → AIが絞り込み → 回答」という流れで動きます。各ステップのパラメータを変えて評価を実行すると、ここに結果が記録されます。
        <br />
        <strong>使い方:</strong> 各行の Before / After にチェックを入れると、2件の評価結果を比較できます。
      </div>

      {results.length === 0 ? (
        <p className="admin-muted">評価結果がまだありません。Tuning画面から Evaluate を実行してください。</p>
      ) : (
        <>
        <p className="admin-section-desc">
          Tuning画面でパラメータを変更して評価を実行するたびに、ここに結果が蓄積されます。前回からの変更内容とスコアの変動が一目でわかります。
        </p>
        <table className="admin-table">
          <thead>
            <tr>
              <th style={{ textAlign: 'center', fontSize: '0.8em' }}>Before</th>
              <th style={{ textAlign: 'center', fontSize: '0.8em' }}>After</th>
              <th>実行日時</th>
              <th>スコア</th>
              <th>正答数</th>
              <th>前回からの変更</th>
              <th>スコア変動</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => {
              const prev = i < results.length - 1 ? results[i + 1] : undefined
              const scoreDiff = prev ? Math.round((r.overall.rate - prev.overall.rate) * 100) : undefined
              return (
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
                  <td style={{ whiteSpace: 'nowrap' }}>{r.date.slice(5, 16)}</td>
                  <td className={r.overall.rate >= 0.5 ? 'text-pass' : 'text-fail'}>
                    {(r.overall.rate * 100).toFixed(1)}%
                  </td>
                  <td>{r.overall.passed}/{r.overall.total}</td>
                  <td style={{ fontSize: '0.82rem', color: '#555' }}>
                    {describeChanges(r, prev)}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {scoreDiff === undefined ? (
                      <span style={{ color: '#999', fontSize: '0.82rem' }}>—</span>
                    ) : scoreDiff === 0 ? (
                      <span style={{ color: '#888' }}>±0%</span>
                    ) : (
                      <span style={{ color: scoreDiff > 0 ? '#1e7e34' : '#c5221f', fontWeight: 600 }}>
                        {scoreDiff > 0 ? '+' : ''}{scoreDiff}%
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      className="admin-btn-sm"
                      onClick={() => setSelected(selected?.file === r.file ? null : r)}
                    >
                      {selected?.file === r.file ? 'Close' : 'Detail'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        </>
      )}

      {/* Compare */}
      {compareResults && (
        <div className="admin-section">
          <h2>比較結果</h2>
          <p className="admin-section-desc">Before → After でパラメータとスコアがどう変わったかを表示します。</p>
          <CompareView before={compareResults.before} after={compareResults.after} />
        </div>
      )}

      {selected && (
        <div className="admin-section">
          <h2>タイプ別スコア — {selected.date.slice(0, 19)}</h2>
          <p className="admin-section-desc">テストケースの質問タイプごとの正答率です。苦手なタイプを特定し、改善の方針を立てるのに使います。</p>
          <table className="admin-table">
            <thead>
              <tr><th>タイプ</th><th>正答数</th><th>全体</th><th>正答率</th></tr>
            </thead>
            <tbody>
              {Object.entries(selected.score_by_type).map(([type, s]) => (
                <tr key={type}>
                  <td><TypeName type={type} /></td>
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
          <h2>スコア推移</h2>
          <p className="admin-section-desc">評価のたびにスコアがどう変化しているかを時系列で表示します。右端が最新です。</p>
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
    { key: 'chunk_size', label: '分割サイズ' },
    { key: 'chunk_overlap', label: '重複幅' },
    { key: 'top_k', label: '検索件数' },
    { key: 'rerank_top_n', label: '絞り込み件数' },
    { key: 'rerank_threshold', label: '足切りスコア' },
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
            改善: {improved.map((t) => TYPE_LABELS[t] ?? t).join('、')}
          </div>
        )}
        {degraded.length > 0 && (
          <div style={{ color: '#c5221f', fontSize: '0.9em' }}>
            悪化: {degraded.map((t) => TYPE_LABELS[t] ?? t).join('、')}
          </div>
        )}
      </div>

      {/* Parameter diff */}
      <h3 style={{ marginBottom: 4 }}>パラメータ比較</h3>
      <p className="admin-section-desc" style={{ marginTop: 0 }}>変更されたパラメータは黄色でハイライトされます。</p>
      <table className="admin-table" style={{ marginBottom: 16 }}>
        <thead>
          <tr>
            <th>パラメータ</th>
            <th style={{ textAlign: 'right' }}>Before ({before.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>After ({after.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>変化</th>
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
      <h3 style={{ marginBottom: 4 }}>スコア比較</h3>
      <p className="admin-section-desc" style={{ marginTop: 0 }}>タイプごとのスコア変化です。Δ列の<span style={{ color: '#1e7e34', fontWeight: 600 }}>緑</span>は改善、<span style={{ color: '#c5221f', fontWeight: 600 }}>赤</span>は悪化を示します。</p>
      <table className="admin-table">
        <thead>
          <tr>
            <th>タイプ</th>
            <th style={{ textAlign: 'right' }}>Before ({before.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>After ({after.date.slice(5, 16)})</th>
            <th style={{ textAlign: 'right' }}>Δ</th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ fontWeight: 600 }}>
            <td>全体</td>
            <td style={{ textAlign: 'right' }}>{(before.overall.rate * 100).toFixed(0)}% ({before.overall.passed}/{before.overall.total})</td>
            <td style={{ textAlign: 'right' }}>{(after.overall.rate * 100).toFixed(0)}% ({after.overall.passed}/{after.overall.total})</td>
            <td style={{ textAlign: 'right' }}><DeltaPct a={before.overall.rate} b={after.overall.rate} /></td>
          </tr>
          {allTypes.map((type) => {
            const sb = before.score_by_type[type] ?? { passed: 0, total: 0, rate: 0 }
            const sa = after.score_by_type[type] ?? { passed: 0, total: 0, rate: 0 }
            return (
              <tr key={type}>
                <td><TypeName type={type} /></td>
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
