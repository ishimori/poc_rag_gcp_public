import { useEffect, useRef, useState } from 'react'
import {
  getCollections, setActiveCollection, getTasks, cancelIngest, cancelEvaluate,
  type Collection, type TaskStatus,
} from './api'

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function progressPct(task: TaskStatus): number {
  if (!task.total || task.total === 0) return 0
  return Math.round(((task.current ?? 0) / task.total) * 100)
}

function taskLabel(task: TaskStatus): string {
  if (task.running) return '実行中'
  if (task.current && task.total && task.current >= task.total) return '完了'
  return '待機中'
}

function taskColor(task: TaskStatus): string {
  if (task.running) return '#4a90d9'
  if (task.current && task.total && task.current >= task.total) return '#52c41a'
  return '#e8e8e8'
}

export default function Tuning() {
  const [collections, setCollections] = useState<Collection[]>([])
  const [activeCollection, setActiveCollectionState] = useState('')
  const [ingestTasks, setIngestTasks] = useState<TaskStatus[]>([])
  const [evalTasks, setEvalTasks] = useState<TaskStatus[]>([])
  const [error, setError] = useState('')

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 初期読み込み
  useEffect(() => {
    let active = true
    getCollections()
      .then((res) => { if (active) { setCollections(res.collections); setActiveCollectionState(res.current) } })
      .catch((e) => { if (active) setError(e instanceof Error ? e.message : 'Failed to load collections') })
    getTasks()
      .then((res) => {
        if (active) {
          setIngestTasks(res.tasks.filter((t) => t.task_id.startsWith('ingest:') && t.running))
          setEvalTasks(res.tasks.filter((t) => t.task_id.startsWith('evaluate:') && t.running))
        }
      })
      .catch(() => {})
    return () => { active = false }
  }, [])

  // タスクポーリング（2秒間隔）
  useEffect(() => {
    pollRef.current = setInterval(() => {
      getTasks()
        .then((res) => {
          setIngestTasks(res.tasks.filter((t) => t.task_id.startsWith('ingest:') && t.running))
          setEvalTasks(res.tasks.filter((t) => t.task_id.startsWith('evaluate:') && t.running))
        })
        .catch(() => {})
    }, 2000)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  async function handleSwitchCollection(name: string) {
    try {
      await setActiveCollection(name)
      setActiveCollectionState(name)
      const res = await getCollections()
      setCollections(res.collections)
      setActiveCollectionState(res.current)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to switch collection')
    }
  }

  async function handleCancelTask(taskId: string) {
    try {
      if (taskId.startsWith('ingest:')) {
        await cancelIngest()
      } else if (taskId.startsWith('evaluate:')) {
        await cancelEvaluate()
      }
    } catch {
      // キャンセル失敗は無視
    }
  }

  function renderTaskRow(task: TaskStatus) {
    const pct = progressPct(task)
    const color = taskColor(task)
    const label = taskLabel(task)
    const collectionName = task.collection || task.task_id.split(':')[1] || ''
    const isRunning = task.running

    return (
      <div key={task.task_id} className="admin-job-row">
        <div className="admin-job-name">
          <strong>{collectionName}</strong>
          {task.chunk_size && (
            <span className="admin-job-params">{task.chunk_size} / overlap {task.chunk_overlap ?? '?'}</span>
          )}
        </div>
        <div className="admin-job-progress">
          <div className="admin-progress-bar">
            <div
              className="admin-progress-bar-fill"
              style={{ width: `${pct}%`, background: color }}
            />
          </div>
          <div className="admin-job-detail">
            {isRunning && task.current_file && (
              <span className="admin-job-file">処理中: {task.current_file}</span>
            )}
            {isRunning && task.current_id && (
              <span className="admin-job-file">最新: {task.current_id}
                {task.results && task.results.length > 0 && (() => {
                  const last = task.results[task.results.length - 1]
                  return ` → ${last.status}${last.llm_label ? ` (${last.llm_label})` : ''}`
                })()}
              </span>
            )}
            <span>
              {task.current ?? 0} / {task.total ?? 0}
              {task.elapsed != null && ` | ${formatTime(task.elapsed)} 経過`}
              {isRunning && task.estimated_remaining != null && task.estimated_remaining > 0 && ` | 残り約 ${formatTime(task.estimated_remaining)}`}
            </span>
          </div>
        </div>
        <div className="admin-job-status">
          <span className={`admin-status-badge admin-status-${isRunning ? 'running' : label === '完了' ? 'done' : 'waiting'}`}>
            {label}
          </span>
        </div>
        <div className="admin-job-action">
          <button
            className="admin-btn-sm admin-btn-cancel"
            onClick={() => handleCancelTask(task.task_id)}
            disabled={!isRunning}
          >
            中止
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-page">
      <h1>Operations Monitor</h1>
      {error && <div className="admin-error">{error}</div>}

      <div className="admin-guide">
        <strong>CLI専用に移行した機能:</strong> パラメータ編集・Technique Toggles → <code>src/config.py</code>、
        Re-tune → <code>python scripts/run_chunk_experiments.py</code>。
        この画面では実行の進捗監視とコレクション切替のみ行います。
      </div>

      {/* Collection Selector */}
      <div className="admin-section">
        <h2>検索対象コレクション</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <select
            className="admin-collection-select"
            value={activeCollection}
            onChange={(e) => handleSwitchCollection(e.target.value)}
          >
            {collections.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.count} chunks)
              </option>
            ))}
          </select>
          <span style={{ fontSize: '0.82rem', color: '#666' }}>
            チャット・評価の検索対象が切り替わります
          </span>
        </div>
      </div>

      {/* Ingest Monitor */}
      <div className="admin-section">
        <h2>Ingest（データ取り込み）</h2>
        {ingestTasks.length === 0 ? (
          <p style={{ color: '#999', fontSize: '0.85rem' }}>実行中・完了済みのIngestジョブはありません</p>
        ) : (
          <div className="admin-job-list">
            {ingestTasks.map(renderTaskRow)}
          </div>
        )}
      </div>

      {/* Evaluate Monitor */}
      <div className="admin-section">
        <h2>Evaluate（精度評価）</h2>
        {evalTasks.length === 0 ? (
          <p style={{ color: '#999', fontSize: '0.85rem' }}>実行中・完了済みのEvaluateジョブはありません</p>
        ) : (
          <div className="admin-job-list">
            {evalTasks.map(renderTaskRow)}
          </div>
        )}
      </div>

      {/* Score Comparison */}
      {collections.length > 0 && (
        <div className="admin-section">
          <h2>コレクション一覧</h2>
          <table className="admin-table">
            <thead>
              <tr>
                <th>コレクション</th>
                <th>チャンク数</th>
                <th>状態</th>
              </tr>
            </thead>
            <tbody>
              {collections.map((c) => (
                <tr key={c.name} className={c.name === activeCollection ? 'admin-row-active' : ''}>
                  <td>
                    {c.name}
                    {c.name === activeCollection && <span className="admin-active-badge">active</span>}
                  </td>
                  <td>{c.count}</td>
                  <td>{c.count > 0 ? 'Ready' : 'Empty'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
