import { useEffect, useRef, useState } from 'react'
import {
  getConfig, updateConfig, runIngest, runEvaluate, getSources, getEvalStatus, cancelEvaluate,
  type ConfigParams, type EvalProgress, type EvalReport, type IngestResult, type SourceFile,
} from './api'

type Status = 'idle' | 'loading' | 'success' | 'error'

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function Tuning() {
  const [config, setConfig] = useState<ConfigParams | null>(null)
  const [draft, setDraft] = useState<Partial<ConfigParams>>({})
  const [configStatus, setConfigStatus] = useState<Status>('idle')

  const [ingestStatus, setIngestStatus] = useState<Status>('idle')
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null)
  const [ingestClear, setIngestClear] = useState(true)

  const [evalStatus, setEvalStatus] = useState<Status>('idle')
  const [evalReport, setEvalReport] = useState<EvalReport | null>(null)
  const [evalProgress, setEvalProgress] = useState<EvalProgress | null>(null)
  // 画面再オープン時に既存ジョブを検出した場合、POSTレスポンスは受け取れない
  const [evalDetached, setEvalDetached] = useState(false)

  const [retuneStatus, setRetuneStatus] = useState<Status>('idle')

  const [sourceFiles, setSourceFiles] = useState<SourceFile[]>([])

  const [error, setError] = useState('')

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    getConfig().then((c) => {
      setConfig(c)
      setDraft(c)
    }).catch((e) => setError(e.message))
    getSources().then((res) => setSourceFiles(res.files)).catch(() => {})

    // マウント時に実行中ジョブを検出
    getEvalStatus().then((status) => {
      if (status.running) {
        setEvalStatus('loading')
        setEvalProgress(status)
        setEvalDetached(true)
      }
    }).catch(() => {})
  }, [])

  // Evaluate進捗ポーリング
  useEffect(() => {
    if (evalStatus === 'loading') {
      pollRef.current = setInterval(async () => {
        try {
          const status = await getEvalStatus()
          setEvalProgress(status)
          // detachedモード: ポーリングで完了を検出
          if (evalDetached && !status.running) {
            setEvalStatus('success')
            setEvalDetached(false)
          }
        } catch {
          // ポーリング失敗は無視（バックエンドが忙しい場合がある）
        }
      }, 2000)
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
      if (evalStatus !== 'loading') {
        setEvalProgress(null)
      }
    }
  }, [evalStatus, evalDetached])

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
    setEvalDetached(false)
    try {
      const res = await runEvaluate()
      setEvalReport(res.report)
      setEvalStatus('success')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setEvalStatus('error')
    }
  }

  async function handleCancel() {
    try {
      await cancelEvaluate()
    } catch {
      // キャンセル失敗は無視
    }
  }

  async function handleRetune() {
    setRetuneStatus('loading')
    setError('')
    setEvalDetached(false)
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

  const isProd = import.meta.env.PROD
  const isRunning = ingestStatus === 'loading' || evalStatus === 'loading' || retuneStatus === 'loading'

  if (!config) return <div className="admin-page"><p>Loading...</p></div>

  const PARAM_FIELDS: { key: keyof ConfigParams; label: string; hint: string; step?: string }[] = [
    { key: 'chunk_size', label: '分割サイズ', hint: '文書を何文字ごとに区切るか。大きいと文脈が豊富、小さいと検索精度が上がる' },
    { key: 'chunk_overlap', label: '重複幅', hint: '分割の境界で前後の文を重ねる文字数。情報の切れ目を防ぐ' },
    { key: 'top_k', label: '検索件数', hint: '質問に対して何件の候補を検索するか' },
    { key: 'rerank_top_n', label: '絞り込み件数', hint: '検索結果をAIが再評価した後、上位何件を回答に使うか' },
    { key: 'rerank_threshold', label: '足切りスコア', hint: 'AIの再評価でこのスコア未満の候補は除外する（0〜1）', step: '0.01' },
  ]

  const progressPct = evalProgress && evalProgress.total > 0
    ? Math.round((evalProgress.current / evalProgress.total) * 100)
    : 0

  return (
    <div className="admin-page">
      <h1>Evaluation & Tuning</h1>
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-guide">
        <strong>操作フロー:</strong> ① パラメータ変更 → ② Re-tune実行（Save → Ingest → Evaluate を一括実行）→ ③ Historyで前回と比較
      </div>

      {isProd && (
        <div className="admin-error" style={{ background: '#fff3cd', color: '#856404', borderColor: '#ffc107' }}>
          ⚠ Ingest・Evaluate・Re-tune はローカル環境でのみ実行できます。パラメータ変更のみ可能です。
          <br />
          <code style={{ fontSize: '0.85em' }}>bash scripts/dev.sh</code> でローカルサーバーを起動してください。
        </div>
      )}

      {/* Technique Toggles */}
      <div className="admin-section">
        <h2>Technique Toggles</h2>
        <p className="admin-section-desc">
          技術をOFFにして Re-tune すると、その技術の効果（スコア差分）を測定できます。
          <strong>チャンキング・ヘッダーの変更は再インジェストが必要です。</strong>
        </p>
        <div className="admin-toggle-grid">
          <label className="admin-toggle">
            <input
              type="checkbox"
              checked={draft.header_injection ?? true}
              onChange={(e) => setDraft((prev) => ({ ...prev, header_injection: e.target.checked }))}
              disabled={isRunning}
            />
            <div>
              <span className="admin-toggle-label">02 ヘッダーインジェクション</span>
              <span className="admin-param-hint">各チャンクの先頭に文書タイトルを付与</span>
              {!(draft.header_injection ?? true) && <span className="admin-toggle-warn">⚠ 再インジェスト必要</span>}
            </div>
          </label>
          <label className="admin-toggle">
            <input
              type="checkbox"
              checked={(draft.rerank_top_n ?? 5) < (draft.top_k ?? 10)}
              onChange={(e) => {
                if (e.target.checked) {
                  setDraft((prev) => ({ ...prev, rerank_top_n: 5 }))
                } else {
                  setDraft((prev) => ({ ...prev, rerank_top_n: prev.top_k ?? 10 }))
                }
              }}
              disabled={isRunning}
            />
            <div>
              <span className="admin-toggle-label">04 リランキング</span>
              <span className="admin-param-hint">検索結果をAIが再評価して上位に絞る</span>
              {(draft.rerank_top_n ?? 5) >= (draft.top_k ?? 10) && <span className="admin-toggle-warn">OFF（top_n=top_k で無効化）</span>}
            </div>
          </label>
        </div>
      </div>

      {/* Parameters */}
      <div className="admin-section">
        <h2>Parameters</h2>
        <div className="admin-param-grid">
          {PARAM_FIELDS.map(({ key, label, hint, step }) => (
            <label key={key} className="admin-param">
              <span>{label}</span>
              <input
                type="number"
                step={step || '1'}
                value={draft[key] as number ?? ''}
                onChange={(e) => handleDraftChange(key, e.target.value)}
                disabled={isRunning}
              />
              <span className="admin-param-hint">{hint}</span>
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
          <div className="admin-action-card">
            <div className="admin-action-header">
              <button className="admin-btn" onClick={handleIngest} disabled={isRunning || isProd}>
                {ingestStatus === 'loading' ? '取り込み中...' : 'データ取り込み（Ingest）'}
              </button>
            </div>
            <p className="admin-action-desc">ソース文書を分割・ベクトル化してDBに格納する</p>
            <label className="admin-checkbox">
              <input
                type="checkbox"
                checked={ingestClear}
                onChange={(e) => setIngestClear(e.target.checked)}
                disabled={isRunning}
              />
              {ingestClear
                ? 'DBを空にしてから全文書を再取り込み（パラメータ変更時はこちら）'
                : '新規・変更分だけ追加（既存データはそのまま）'}
            </label>
            {sourceFiles.length > 0 && (
              <details className="admin-source-files">
                <summary>取り込み対象ファイル（{sourceFiles.length}件）</summary>
                <ul>
                  {sourceFiles.map((f) => (
                    <li key={f.name}>
                      {f.name}
                      <span className="admin-file-size">{(f.size / 1024).toFixed(1)} KB</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>

          <div className="admin-action-card">
            <div className="admin-action-header">
              <button className="admin-btn" onClick={handleEvaluate} disabled={isRunning || isProd}>
                {evalStatus === 'loading' ? '評価中...' : '精度評価（Evaluate）'}
              </button>
            </div>
            <p className="admin-action-desc">テストケースで質問→回答し、正答率を測定する</p>
            {evalStatus === 'loading' && evalProgress && evalProgress.total > 0 && (
              <div className="admin-eval-progress">
                <div className="admin-eval-progress-info">
                  <span>{evalProgress.current} / {evalProgress.total} 件完了</span>
                  <button className="admin-btn-sm admin-btn-cancel" onClick={handleCancel}>中止</button>
                </div>
                <div className="admin-progress-bar">
                  <div
                    className="admin-progress-bar-fill"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                <div className="admin-eval-progress-detail">
                  <span>{formatTime(evalProgress.elapsed)} 経過</span>
                  {evalProgress.estimated_remaining > 0 && (
                    <span>残り約 {formatTime(evalProgress.estimated_remaining)}</span>
                  )}
                </div>
                {evalProgress.current_id && (
                  <div className="admin-eval-progress-current">
                    最新: {evalProgress.current_id}
                    {evalProgress.results.length > 0 && (() => {
                      const last = evalProgress.results[evalProgress.results.length - 1]
                      return ` → ${last.status}${last.llm_label ? ` (${last.llm_label})` : ''}`
                    })()}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="admin-action-card">
            <div className="admin-action-header">
              <button className="admin-btn admin-btn-primary" onClick={handleRetune} disabled={isRunning || isProd}>
                {retuneStatus === 'loading' ? 'Re-tune中...' : '一括実行（パラメータ保存 → 取り込み → 評価）'}
              </button>
            </div>
            <p className="admin-action-desc">上の3ステップをまとめて実行する</p>
          </div>
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
