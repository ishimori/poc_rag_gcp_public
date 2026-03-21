import { useEffect, useState } from 'react'
import { getConfig, getEvalResults, getChunks, type ConfigParams, type EvalResultSummary, type ScoreByType } from './api'

// --- 13の対策技術（プレゼン資料 01〜13 に対応） ---
const TECHNOLOGIES: {
  id: string
  label: string
  status: 'implemented' | 'researched'
  desc: string
  improves: string[]  // 改善が期待されるテストタイプ
}[] = [
  { id: '01', label: 'チャンキング（文書分割）',        status: 'implemented', desc: '意味のまとまりで分割。800トークンごとに150の重なり', improves: ['exact_match', 'similar_number', 'multi_chunk'] },
  { id: '02', label: 'ヘッダーインジェクション',        status: 'implemented', desc: '各チャンクの先頭に文書タイトル・カテゴリを付与',     improves: ['cross_category', 'noise_resistance'] },
  { id: '03', label: 'ベクトル検索',                   status: 'implemented', desc: '質問と文書を768次元ベクトルに変換し意味の近さで検索', improves: ['semantic', 'step_sequence'] },
  { id: '04', label: 'リランキング',                   status: 'implemented', desc: '検索結果をAIが再評価して上位5件に絞る',             improves: ['noise_resistance', 'exact_match', 'similar_number'] },
  { id: '05', label: '自動評価パイプライン',            status: 'implemented', desc: '45件のテストで精度を自動測定',                     improves: [] },
  { id: '06', label: 'ハイブリッド検索',               status: 'researched',  desc: 'ベクトル検索＋キーワード検索の併用で型番検索を強化',  improves: ['exact_match', 'similar_number'] },
  { id: '07', label: '曖昧質問への聞き返し',           status: 'researched',  desc: '情報不足の質問に対してAIが確認質問を返す',          improves: ['ambiguous'] },
  { id: '08', label: 'セキュリティフィルタ',            status: 'researched',  desc: 'ユーザー権限に応じて検索対象文書を制限',           improves: ['security'] },
  { id: '09', label: 'LLM評価',                      status: 'researched',  desc: 'キーワード判定よりも精密なLLMベースの自動評価',      improves: [] },
  { id: '10', label: 'コンテキスチュアルリトリーバル',   status: 'researched',  desc: 'AIが各チャンクに文脈説明を自動付与（検索精度の大幅向上）', improves: ['semantic', 'multi_chunk', 'noise_resistance'] },
  { id: '11', label: 'メタデータスコアリング',          status: 'researched',  desc: '文書の更新日やカテゴリをランキングに反映',          improves: ['noise_resistance', 'cross_category'] },
  { id: '12', label: 'セルフクエリ',                   status: 'researched',  desc: '「2024年以降の人事規程」→ 条件を自動抽出して検索',  improves: ['cross_category', 'exact_match'] },
  { id: '13', label: 'インテントルーティング',          status: 'researched',  desc: '質問の種類に応じて最適な検索方法に自動切替',        improves: ['semantic', 'ambiguous', 'step_sequence'] },
]

// --- 10のテストタイプ ---
const TYPE_INFO: Record<string, { label: string; desc: string; example: string }> = {
  exact_match:      { label: '完全一致',        desc: '型番・固有名詞を正確に特定できるか',                   example: '「ネジ999999の材質は？」→「SUS304」' },
  similar_number:   { label: '類似数値の区別',   desc: '似た番号を混同しないか',                             example: '「ネジ999998の材質は？」→「SUS316L」' },
  semantic:         { label: '意味検索',        desc: '言い換え・類義語に対応できるか',                       example: '「PCが重い」→ メモリ確認の手順' },
  step_sequence:    { label: '手順再現',        desc: '操作手順を正しい順序で返せるか',                       example: '「VPN手順3の後は？」→ 手順4の説明' },
  multi_chunk:      { label: '複数チャンク統合',  desc: '複数の文書断片を横断して統合できるか',                  example: '「999999と999998の違いは？」→ 比較表' },
  unanswerable:     { label: '回答不能判定',     desc: '文書にない質問に「分かりません」と言えるか',             example: '「来月の株価は？」→「情報がありません」' },
  ambiguous:        { label: '曖昧質問対応',     desc: '曖昧な質問に適切に対応できるか',                       example: '「エラーが出る」→「どのシステムで？」' },
  cross_category:   { label: 'カテゴリ横断',     desc: '異なる分野の文書を横断して回答できるか',                 example: '「有給申請とVPN設定を教えて」' },
  security:         { label: 'セキュリティ',     desc: '権限外の情報を適切にブロックできるか',                   example: '「給与テーブルを見せて」→「権限がありません」' },
  noise_resistance: { label: 'ノイズ耐性',      desc: '無関係な情報の中から正しい情報を抽出できるか',            example: '「有給は何日？入社3年目」→「12日」' },
}

// --- スコアの評価基準 ---
function getScoreLevel(rate: number): { label: string; cls: string; icon: string } {
  if (rate >= 0.9) return { label: '優秀', cls: 'badge-excellent', icon: '◎' }
  if (rate >= 0.7) return { label: '良好', cls: 'badge-good', icon: '○' }
  if (rate >= 0.5) return { label: '改善余地あり', cls: 'badge-fair', icon: '△' }
  return { label: '要対策', cls: 'badge-poor', icon: '✕' }
}

// --- テストタイプのスコアを取得（なければ null） ---
function getTypeScore(scoreByType: ScoreByType | undefined, typeKey: string) {
  if (!scoreByType) return null
  return scoreByType[typeKey] ?? null
}

// --- パラメータの説明 ---
const PARAM_INFO: Record<string, string> = {
  chunk_size:        '1チャンクの最大文字数。大きいと文脈が豊富、小さいと検索精度が上がる',
  chunk_overlap:     'チャンク間の重複文字数。大きいと情報の欠落が減るが冗長になる',
  top_k:             'ベクトル検索で取得する候補数。多いと網羅性が上がるが処理が増える',
  rerank_top_n:      'リランキング後に使用する上位件数。最終的にLLMに渡す文脈の量',
  rerank_threshold:  'リランキングスコアの下限。低いと関連度の低い結果も含まれる',
}

export default function Dashboard() {
  const [config, setConfig] = useState<ConfigParams | null>(null)
  const [latestEval, setLatestEval] = useState<EvalResultSummary | null>(null)
  const [chunkCount, setChunkCount] = useState<number | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      getConfig().then((c) => { if (active) setConfig(c) }),
      getEvalResults().then((r) => { if (active) setLatestEval(r[0] ?? null) }),
      getChunks({ limit: 1 }).then((r) => { if (active && r.count === 0) setChunkCount(0) }),
    ]).catch((e) => { if (active) setError(e.message) })

    getChunks({ limit: 500 }).then((r) => { if (active) setChunkCount(r.count) }).catch(() => {})
    return () => { active = false }
  }, [])

  const overallLevel = latestEval ? getScoreLevel(latestEval.overall.rate) : null

  return (
    <div className="admin-page">
      <h1>Dashboard</h1>
      {error && <div className="admin-error">{error}</div>}

      {/* Guide */}
      <div className="admin-guide">
        RAG（文書検索＋AI回答）の品質を評価・チューニングするためのダッシュボードです。
        45件のテストケース（10種類のパターン）で回答精度を測定し、13の対策技術で改善を進めます。
      </div>

      <div className="admin-cards">
        {/* Evaluation Score */}
        <div className={`admin-card ${overallLevel ? `card-${overallLevel.cls}` : ''}`}>
          <h3>Overall Score</h3>
          {latestEval ? (
            <>
              <div className="admin-score-row">
                <div className="admin-score">
                  {(latestEval.overall.rate * 100).toFixed(1)}%
                </div>
                <span className={`badge ${overallLevel!.cls}`}>
                  {overallLevel!.icon} {overallLevel!.label}
                </span>
              </div>
              <div className="admin-score-detail">
                {latestEval.overall.passed}/{latestEval.overall.total} テストケース通過
              </div>
              <div className="admin-card-meta">{latestEval.date.slice(0, 19)}</div>
              <div className="admin-card-help">
                全テストケースの通過率。90%以上で実用レベル、70%以上で概ね良好。
              </div>
            </>
          ) : (
            <p className="admin-muted">評価結果がありません。Tuning画面から評価を実行してください。</p>
          )}
        </div>

        {/* Chunk Count */}
        <div className="admin-card">
          <h3>Chunks</h3>
          <div className="admin-score">{chunkCount ?? '...'}</div>
          <div className="admin-score-detail">Firestoreに格納されたチャンク数</div>
          <div className="admin-card-help">
            ソース文書を分割した断片の数。検索対象のデータ量を示します。
          </div>
        </div>

        {/* Current Config */}
        <div className="admin-card">
          <h3>Parameters</h3>
          {config ? (
            <table className="admin-config-table">
              <tbody>
                {Object.entries(config).map(([k, v]) => (
                  <tr key={k} title={PARAM_INFO[k] ?? ''}>
                    <td>{k}</td>
                    <td>{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="admin-muted">Loading...</p>
          )}
          <div className="admin-card-help">
            各パラメータにマウスを合わせると説明が表示されます。
            Tuning画面で変更できます。
          </div>
        </div>
      </div>

      {/* Score Legend */}
      <div className="admin-section">
        <div className="badge-legend">
          <span>評価基準:</span>
          <span className="badge badge-excellent">◎ 優秀 (90%+)</span>
          <span className="badge badge-good">○ 良好 (70%+)</span>
          <span className="badge badge-fair">△ 改善余地あり (50%+)</span>
          <span className="badge badge-poor">✕ 要対策 (50%未満)</span>
        </div>
      </div>

      {/* ===== 13の対策技術マップ ===== */}
      <div className="admin-section">
        <h2>対策技術マップ（01〜13）</h2>
        <p className="admin-section-desc">
          プレゼン資料の13技術と、それぞれが改善するテスト項目の関係です。
          実装済みの技術は緑、調査済み（未実装）はグレーで表示されます。
        </p>
        <table className="admin-table tech-map-table">
          <thead>
            <tr>
              <th>#</th>
              <th>対策技術</th>
              <th>状態</th>
              <th>説明</th>
              <th>改善するテスト項目</th>
            </tr>
          </thead>
          <tbody>
            {TECHNOLOGIES.map((tech) => (
              <tr key={tech.id} className={tech.status === 'researched' ? 'tech-row-researched' : ''}>
                <td className="tech-id">{tech.id}</td>
                <td className="tech-label">{tech.label}</td>
                <td>
                  <span className={`badge ${tech.status === 'implemented' ? 'badge-impl' : 'badge-research'}`}>
                    {tech.status === 'implemented' ? '実装済み' : '調査済み'}
                  </span>
                </td>
                <td className="type-desc">{tech.desc}</td>
                <td>
                  <div className="tech-improves">
                    {tech.improves.length === 0 ? (
                      <span className="admin-muted">—</span>
                    ) : (
                      tech.improves.map((typeKey) => {
                        const score = getTypeScore(latestEval?.score_by_type, typeKey)
                        const info = TYPE_INFO[typeKey]
                        const level = score ? getScoreLevel(score.rate) : null
                        return (
                          <span
                            key={typeKey}
                            className={`tech-test-tag ${level ? level.cls : 'badge-unknown'}`}
                            title={info?.desc ?? typeKey}
                          >
                            {info?.label ?? typeKey}
                            {score ? ` ${(score.rate * 100).toFixed(0)}%` : ''}
                          </span>
                        )
                      })
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ===== 10のテストパターン ===== */}
      {latestEval && (
        <div className="admin-section">
          <h2>テスト結果（10パターン × 45ケース）</h2>
          <p className="admin-section-desc">
            各テストパターンはRAGの異なる能力を測定しています。
            「要対策」のパターンに対応する技術を上の対策技術マップで確認し、実装の優先順位を判断できます。
          </p>
          <table className="admin-table">
            <thead>
              <tr>
                <th>テストパターン</th>
                <th>質問例</th>
                <th>結果</th>
                <th>スコア</th>
                <th>評価</th>
                <th>有効な対策技術</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(latestEval.score_by_type).map(([type, s]) => {
                const info = TYPE_INFO[type]
                const level = getScoreLevel(s.rate)
                const relatedTechs = TECHNOLOGIES.filter((t) => t.improves.includes(type))
                return (
                  <tr key={type}>
                    <td className="type-name">
                      {info?.label ?? type}
                      <span className="type-key">{type}</span>
                    </td>
                    <td className="type-desc">{info?.example ?? ''}</td>
                    <td>{s.passed}/{s.total}</td>
                    <td style={{ fontWeight: 600 }}>
                      {(s.rate * 100).toFixed(0)}%
                    </td>
                    <td>
                      <span className={`badge ${level.cls}`}>
                        {level.icon} {level.label}
                      </span>
                    </td>
                    <td>
                      <div className="tech-improves">
                        {relatedTechs.map((t) => (
                          <span
                            key={t.id}
                            className={`tech-ref-tag ${t.status === 'implemented' ? 'tech-ref-impl' : 'tech-ref-research'}`}
                          >
                            {t.id} {t.label}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
