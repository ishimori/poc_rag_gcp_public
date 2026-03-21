# DD-013-3: フローチャート

## 1. CLI実行フロー

```
scripts/evaluate.py [--limit N]
    │
    ├── cases = load from eval_dataset.jsonl
    ├── if --limit: cases = cases[:limit]
    │
    ▼
run_evaluation(cases)
    │
    ├── start_time = time.time()
    │
    ▼ ──── for i, case in enumerate(cases, 1) ────
    │
    │   run_case(case)
    │       │
    │       ├── requires判定 → 機能OFF → return SKIP
    │       │
    │       ├── rag_flow(query)
    │       │
    │       ├── score_by_keywords()
    │       │
    │       └── score_by_llm()
    │
    │   elapsed = time.time() - start_time
    │   remaining = avg_per_active * (total - i)   ← skipped除外の平均
    │
    │   print("[i/total] STATUS id ... [elapsed, ~remaining]")
    │
    ▼ ──── end for ────
    │
    ▼
generate_report(results) → print_report → save_report
```

---

## 2. Admin UI 単独Evaluateフロー

```
┌──────────────────┐    ┌──────────────────────────────┐
│    Tuning.tsx     │    │        main.py (admin)        │
│    (Browser)      │    │   functions-framework thread  │
└──────────────────┘    └──────────────────────────────┘
        │                              │
        │  POST /evaluate              │
        │ ─────────────────────────── ▶│
        │                              │
        │                              │  _eval_progress = {running: True, ...}
        │                              │
        │  ┌── setInterval 2s ──┐      │ ──── for each case ────
        │  │                    │      │  │
        │  │  GET /evaluate/    │      │  │ run_case(case)
        │  │      status        │      │  │
        │  │ ─────────────────▶ │      │  │ _eval_progress を更新
        │  │                    │◀──── │  │   {current: i, total: N,
        │  │  {current, total,  │      │  │    current_id, elapsed,
        │  │   running: true,   │      │  │    estimated_remaining,
        │  │   current_id, ...} │      │  │    results: [...]}
        │  │                    │      │  │
        │  │ → プログレスバー更新│      │  │
        │  │                    │      │ ──── end for ────
        │  └────────────────────┘      │
        │                              │  _eval_progress["running"] = False
        │                              │
        │  GET /evaluate/status        │
        │ ─────────────────────────── ▶│
        │  {running: false}            │
        │ ◀─────────────────────────── │
        │                              │
        │  → clearInterval             │
        │                              │
        │  ◀── POST /evaluate 完了 ─── │  report JSON を返す
        │                              │
        │  → evalReport 表示           │
        ▼                              ▼
```

**ポイント**:
- POSTは評価完了まで応答を返さない（既存動作を維持）
- ポーリングは**別スレッド**で処理される（functions-frameworkのスレッドプール）
- POSTレスポンス受信 → `evalStatus = 'success'` → ポーリング自動停止
- ポーリングが先に `running: false` を検出しても、**POSTのレスポンスで最終結果を受け取る**ので二重処理なし

---

## 3. Re-tune時のEvaluateフロー

```
┌──────────────────┐
│    Tuning.tsx     │
└──────────────────┘
        │
        │ handleRetune()
        │
        ├── 1. await updateConfig(draft)
        │
        ├── 2. setIngestStatus('loading')
        │      await runIngest(true)
        │      setIngestStatus('success')
        │
        ├── 3. setEvalStatus('loading')     ← ここでポーリング開始
        │      await runEvaluate()           ← POST /evaluate（Phase 2対応済み）
        │      setEvalStatus('success')      ← ここでポーリング停止
        │
        └── setRetuneStatus('success')
```

**ポイント**:
- Re-tuneはTuning.tsx内で3ステップを逐次実行する既存フロー
- `evalStatus === 'loading'` のトリガーでポーリングが自動開始されるため、Re-tune時も特別な対応は不要
- `handleEvaluate()` と `handleRetune()` の両方で同じポーリングロジックが動く

---

## 4. ポーリングのライフサイクル（useEffect）

```
evalStatus が 'loading' に変化
    │
    ▼
useEffect 発火
    │
    ├── intervalId = setInterval(async () => {
    │       const status = await getEvalStatus()
    │       setEvalProgress(status)
    │   }, 2000)
    │
    ▼ ──── 2秒ごとに繰り返し ────
    │
    │   getEvalStatus() → {running: true, current: 12, total: 64, ...}
    │   → setEvalProgress → UI再描画（プログレスバー更新）
    │
    ▼ ──── evalStatus が 'success' or 'error' に変化 ────
    │
    useEffect cleanup
    │
    ├── clearInterval(intervalId)
    └── setEvalProgress(null)
```

---

## 5. データフロー一覧

### _eval_progress 辞書（main.py グローバル）

```
{
  "running": true,           ← bool: 評価実行中か
  "current": 12,             ← int: 完了したケース数
  "total": 64,               ← int: 全ケース数（skipped含む）
  "current_id": "exact-005", ← str: 最新の完了ケースID
  "elapsed": 135.2,          ← float: 経過秒数
  "estimated_remaining": 612.8, ← float: 推定残り秒数
  "results": [               ← list: 完了ケースの要約
    {"id": "exact-001", "status": "PASS", "llm_label": "correct"},
    {"id": "exact-002", "status": "FAIL", "llm_label": "incorrect"},
    {"id": "ambiguous-001", "status": "SKIP", "llm_label": ""},
    ...
  ]
}
```

### コールバック連携

```
main.py                         runner.py
────────                        ──────────
_eval_progress (global dict)
        │
        ▼
_on_progress(i, total, result)  ←── run_evaluation(cases, on_progress=callback)
        │                                   │
        │ _eval_progress を更新              │ 各ケース完了時に callback を呼ぶ
        ▼                                   ▼
GET /evaluate/status で返却      CLI用の print は runner.py 内で直接出力
```

---

## 6. 変更対象ファイル一覧

| ファイル | Phase | 変更内容 |
|---------|-------|---------|
| `src/evaluate/runner.py` | 1, 2 | `_format_time()` 追加、`on_progress` コールバック引数追加、CLI進捗print変更 |
| `scripts/evaluate.py` | — | 変更なし（`run_evaluation(cases)` の呼び出しはそのまま動く） |
| `main.py` | 2 | `_eval_progress` グローバル辞書、`_on_progress` コールバック、`_handle_evaluate_status()` 追加、ルーティング追加 |
| `ui/src/admin/api.ts` | 2 | `EvalProgress` interface、`getEvalStatus()` 追加 |
| `ui/src/admin/Tuning.tsx` | 2 | `evalProgress` state、ポーリング `useEffect`、プログレスバーUI追加 |
