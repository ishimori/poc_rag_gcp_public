const BASE = '/api/admin'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}

// --- Config ---

export interface ConfigParams {
  chunk_size: number
  chunk_overlap: number
  header_injection: boolean
  top_k: number
  rerank_top_n: number
  rerank_threshold: number
}

export function getConfig(): Promise<ConfigParams> {
  return request('/config')
}

export function updateConfig(params: Partial<ConfigParams>): Promise<{ updated: Partial<ConfigParams>; errors?: string[] }> {
  return request('/config', { method: 'PUT', body: JSON.stringify(params) })
}

// --- Ingest ---

export interface IngestResult {
  cleared: number
  files: number
  total_chunks: number
  stored: number
  skipped: number
  details: { file: string; chunks: number; stored: number; skipped: number }[]
}

export function runIngest(clear = false): Promise<IngestResult> {
  return request('/ingest', { method: 'POST', body: JSON.stringify({ clear }) })
}

// --- Evaluate ---

export interface ScoreByType {
  [type: string]: { passed: number; total: number; rate: number }
}

export interface EvalReport {
  date: string
  config_params: ConfigParams
  score_by_type: ScoreByType
  overall: { passed: number; total: number; rate: number }
  failed_cases: {
    id: string
    query: string
    type: string
    category: string
    expected: string
    actual: string
    keyword_score: number
    keyword_matched: string[]
    keyword_missed: string[]
    passed: boolean
  }[]
}

export function runEvaluate(): Promise<{ report: EvalReport; saved_to: string }> {
  return request('/evaluate', { method: 'POST' })
}

export interface EvalResultSummary {
  file: string
  date: string
  config_params: ConfigParams
  overall: { passed: number; total: number; rate: number }
  score_by_type: ScoreByType
}

export function getEvalResults(): Promise<EvalResultSummary[]> {
  return request('/evaluate/results')
}

// --- Chunks ---

export interface ChunkItem {
  id: string
  content: string
  content_preview: string
  source_file: string
  chunk_index: number
  category: string
  security_level: string
  allowed_groups: string[]
}

// --- Logs ---

export interface QueryLog {
  id: string
  query: string
  answer: string
  model: string
  elapsed_ms: number
  sources: (string | { file: string; score: number })[]
  source_count: number
  no_answer: boolean
  timestamp: string | null
}

export function getLogs(params?: {
  no_answer?: boolean
  limit?: number
}): Promise<{ logs: QueryLog[]; count: number }> {
  const q = new URLSearchParams()
  if (params?.no_answer) q.set('no_answer', 'true')
  if (params?.limit) q.set('limit', String(params.limit))
  const qs = q.toString()
  return request(`/logs${qs ? `?${qs}` : ''}`, { method: 'GET' })
}

// --- Chunks ---

export function getChunks(params?: {
  category?: string
  security_level?: string
  limit?: number
  offset?: number
}): Promise<{ chunks: ChunkItem[]; count: number }> {
  const q = new URLSearchParams()
  if (params?.category) q.set('category', params.category)
  if (params?.security_level) q.set('security_level', params.security_level)
  if (params?.limit) q.set('limit', String(params.limit))
  if (params?.offset) q.set('offset', String(params.offset))
  const qs = q.toString()
  return request(`/chunks${qs ? `?${qs}` : ''}`, { method: 'GET' })
}
