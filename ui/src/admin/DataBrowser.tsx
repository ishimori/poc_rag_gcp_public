import { useState } from 'react'
import { getChunks, type ChunkItem } from './api'

export default function DataBrowser() {
  const [chunks, setChunks] = useState<ChunkItem[]>([])
  const [count, setCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Filters
  const [category, setCategory] = useState('')
  const [securityLevel, setSecurityLevel] = useState('')
  const [limit, setLimit] = useState(100)

  // Detail
  const [selected, setSelected] = useState<ChunkItem | null>(null)

  async function handleFetch() {
    setLoading(true)
    setError('')
    setSelected(null)
    try {
      const res = await getChunks({
        category: category || undefined,
        security_level: securityLevel || undefined,
        limit,
      })
      setChunks(res.chunks)
      setCount(res.count)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-page">
      <h1>Data Browser</h1>
      {error && <div className="admin-error">{error}</div>}

      {/* Filters */}
      <div className="admin-section">
        <h2>Filters</h2>
        <div className="data-filters">
          <label className="admin-param">
            <span>Category</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All</option>
              <option value="parts_catalog">parts_catalog</option>
              <option value="it_helpdesk">it_helpdesk</option>
              <option value="hr">hr</option>
              <option value="finance">finance</option>
              <option value="general">general</option>
              <option value="management">management</option>
              <option value="wikipedia">wikipedia</option>
            </select>
          </label>
          <label className="admin-param">
            <span>Security Level</span>
            <select value={securityLevel} onChange={(e) => setSecurityLevel(e.target.value)}>
              <option value="">All</option>
              <option value="public">public</option>
              <option value="internal">internal</option>
              <option value="confidential">confidential</option>
            </select>
          </label>
          <label className="admin-param">
            <span>Limit</span>
            <input
              type="number"
              min={1}
              max={500}
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value) || 100)}
            />
          </label>
          <button className="admin-btn admin-btn-primary" onClick={handleFetch} disabled={loading}>
            {loading ? 'Loading...' : 'Fetch Data'}
          </button>
        </div>
      </div>

      {/* Results */}
      {count !== null && (
        <div className="admin-section">
          <h2>Chunks ({count})</h2>
          <div className="data-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>source_file</th>
                  <th>#</th>
                  <th>category</th>
                  <th>security</th>
                  <th>content</th>
                </tr>
              </thead>
              <tbody>
                {chunks.map((c) => (
                  <tr
                    key={c.id}
                    className={`data-row ${selected?.id === c.id ? 'admin-row-selected' : ''}`}
                    onClick={() => setSelected(selected?.id === c.id ? null : c)}
                  >
                    <td>{c.source_file}</td>
                    <td>{c.chunk_index}</td>
                    <td><span className={`data-tag tag-${c.category}`}>{c.category}</span></td>
                    <td><span className={`data-tag tag-${c.security_level}`}>{c.security_level}</span></td>
                    <td className="data-content-cell">{c.content}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail */}
      {selected && (
        <div className="admin-section">
          <h2>Detail — {selected.source_file}#{selected.chunk_index}</h2>
          <table className="admin-config-table" style={{ marginBottom: 12 }}>
            <tbody>
              <tr><td>ID</td><td>{selected.id}</td></tr>
              <tr><td>Category</td><td>{selected.category}</td></tr>
              <tr><td>Security Level</td><td>{selected.security_level}</td></tr>
              <tr><td>Allowed Groups</td><td>{selected.allowed_groups?.join(', ') ?? '-'}</td></tr>
            </tbody>
          </table>
          <div className="data-content-full">
            {selected.content}
          </div>
        </div>
      )}
    </div>
  )
}
