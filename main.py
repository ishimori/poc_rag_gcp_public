"""Cloud Functions for Firebase — RAG API エントリポイント"""

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

# プロジェクトルートを sys.path に追加（src/ のインポート用）
sys.path.insert(0, Path(__file__).parent.as_posix())

from firebase_functions import https_fn, options
from google.cloud import firestore

from src.config import config
from src.search.flow import rag_flow

NO_ANSWER_MARKER = "記載がありません"

_firestore_client = None


def _get_firestore_client() -> firestore.Client:
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.Client()
    return _firestore_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CORS = options.CorsOptions(
    cors_origins=["http://localhost:5180"],
    cors_methods=["GET", "POST", "PUT"],
)


def _json_response(data: dict | list, status: int = 200) -> https_fn.Response:
    return https_fn.Response(
        response=json.dumps(data, ensure_ascii=False),
        status=status,
        content_type="application/json",
    )


def _error(msg: str, status: int = 400) -> https_fn.Response:
    return _json_response({"error": msg}, status)


# ---------------------------------------------------------------------------
# Query logging
# ---------------------------------------------------------------------------


def _save_query_log(
    query: str,
    answer: str,
    model: str | None,
    elapsed_ms: int,
    sources: list[dict],
) -> None:
    """クエリログを Firestore query_logs コレクションに保存する"""
    try:
        db = _get_firestore_client()
        db.collection("query_logs").add(
            {
                "query": query,
                "answer": answer,
                "model": model or "",
                "elapsed_ms": elapsed_ms,
                "sources": [{"file": s.get("source_file", ""), "score": s.get("score", 0)} for s in sources],
                "source_count": len(sources),
                "no_answer": NO_ANSWER_MARKER in answer,
                "collection": config.collection_name,
                "techniques": {
                    "hybrid_search": config.hybrid_search,
                    "metadata_scoring": config.metadata_scoring,
                    "clarification": config.clarification,
                    "permission_filter": config.permission_filter,
                    "shadow_retrieval": config.shadow_retrieval,
                    "multi_query": config.multi_query,
                    "contextual_retrieval": config.contextual_retrieval,
                },
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        )
    except Exception as e:
        print(f"  [QueryLog] Failed to save log: {e}")


# ---------------------------------------------------------------------------
# chat — RAG チャット API
# ---------------------------------------------------------------------------


@https_fn.on_request(
    region="asia-northeast1",
    memory=options.MemoryOption.GB_1,
    timeout_sec=120,
    min_instances=0,
    cors=_CORS,
)
def chat(req: https_fn.Request) -> https_fn.Response:
    """RAG チャット API"""
    if req.method != "POST":
        return _error("Method not allowed", 405)

    body = req.get_json(force=True, silent=True)
    if not body or "query" not in body:
        return _error("query is required")

    query = body["query"]
    model = body.get("model")
    user_groups = body.get("user_groups", config.user_groups)

    start_time = time.monotonic()
    result = rag_flow(query, model_name=model, user_groups=user_groups)
    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    sources = [
        {
            "content": s.content,
            "score": s.score,
            "source_file": s.source_file,
            "chunk_index": s.chunk_index,
            "category": s.category,
            "security_level": s.security_level,
        }
        for s in result.reranked_sources
    ]

    response_data = {
        "answer": result.answer,
        "query": result.query,
        "sources": sources,
        "is_clarification": result.is_clarification,
    }

    _save_query_log(query, result.answer, model, elapsed_ms, sources)

    return _json_response(response_data)


# ---------------------------------------------------------------------------
# admin — 管理系 API（パスベースルーティング）
# ---------------------------------------------------------------------------


@https_fn.on_request(
    region="asia-northeast1",
    memory=options.MemoryOption.GB_1,
    timeout_sec=540,
    min_instances=0,
    cors=_CORS,
)
def admin(req: https_fn.Request) -> https_fn.Response:
    """管理系 API — パスベースルーティング"""
    path = req.path.rstrip("/")
    # Firebase Hosting rewrites /api/admin/** → admin function
    if path.startswith("/api/admin"):
        path = path[len("/api/admin") :]
    method = req.method

    if path == "/sources" and method == "GET":
        return _handle_sources(req)
    if path == "/ingest" and method == "POST":
        return _handle_ingest(req)
    if path == "/ingest/status" and method == "GET":
        return _handle_ingest_status(req)
    if path == "/ingest/cancel" and method == "POST":
        return _handle_ingest_cancel(req)
    if path == "/evaluate" and method == "POST":
        return _handle_evaluate(req)
    if path == "/evaluate/status" and method == "GET":
        return _handle_evaluate_status(req)
    if path == "/evaluate/cancel" and method == "POST":
        return _handle_evaluate_cancel(req)
    if path == "/evaluate/cases" and method == "GET":
        return _handle_evaluate_cases(req)
    if path == "/evaluate/results" and method == "GET":
        return _handle_evaluate_results(req)
    if path == "/config" and method == "GET":
        return _handle_config_get(req)
    if path == "/config" and method == "PUT":
        return _handle_config_put(req)
    if path == "/chunks" and method == "GET":
        return _handle_chunks(req)
    if path == "/logs" and method == "GET":
        return _handle_logs(req)
    if path == "/collections" and method == "GET":
        return _handle_collections(req)
    if path == "/collections/active" and method == "PUT":
        return _handle_collections_switch(req)
    if path == "/tasks" and method == "GET":
        return _handle_tasks(req)

    return _error(f"Not found: {method} {path}", 404)


# --- Sources ---


def _handle_sources(req: https_fn.Request) -> https_fn.Response:
    """GET /sources — 取り込み対象のソースファイル一覧"""
    sources_dir = "test-data/sources"
    if not os.path.isdir(sources_dir):
        return _json_response({"files": [], "count": 0})

    files = []
    for root, _dirs, fnames in os.walk(sources_dir):
        for fname in sorted(fnames):
            if fname.endswith(".md"):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, sources_dir).replace("\\", "/")
                size = os.path.getsize(full)
                files.append({"name": rel, "size": size})
    files.sort(key=lambda f: f["name"])

    return _json_response({"files": files, "count": len(files)})


# --- Ingest ---


def _handle_ingest_status(req: https_fn.Request) -> https_fn.Response:
    """GET /ingest/status — インジェスト進捗を返す"""
    from src.task_status import get_task_status

    task_id = f"ingest:{config.collection_name}"
    return _json_response(get_task_status(task_id))


def _handle_ingest_cancel(req: https_fn.Request) -> https_fn.Response:
    """POST /ingest/cancel — インジェストを中止する"""
    from src.task_status import get_task_status, update_task_status

    task_id = f"ingest:{config.collection_name}"
    status = get_task_status(task_id)
    if not status.get("running"):
        return _json_response({"cancelled": False, "reason": "not running"})
    update_task_status(task_id, cancel=True)
    return _json_response({"cancelled": True})


def _handle_ingest(req: https_fn.Request) -> https_fn.Response:
    """POST /ingest — インジェスト実行"""
    from src.ingest.chunker import chunk_document
    from src.ingest.embedder import embed_texts
    from src.ingest.store import clear_collection, store_chunks
    from src.task_status import (
        check_cancel,
        clear_task_status,
        update_task_status,
    )

    body = req.get_json(force=True, silent=True) or {}
    should_clear = body.get("clear", False)

    sources_dir = "test-data/sources"

    deleted = clear_collection() if should_clear else 0

    files: list[tuple[str, str]] = []
    for root, _dirs, fnames in os.walk(sources_dir):
        for fname in sorted(fnames):
            if fname.endswith(".md"):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, sources_dir).replace("\\", "/")
                files.append((rel, full))
    files.sort()

    # 進捗初期化
    ingest_task_id = f"ingest:{config.collection_name}"
    start_time = time.time()
    update_task_status(
        ingest_task_id,
        running=True,
        cancel=False,
        current=0,
        total=len(files),
        current_file="",
        elapsed=0.0,
        estimated_remaining=0.0,
        collection=config.collection_name,
    )

    total_chunks = 0
    total_stored = 0
    total_skipped = 0
    file_results = []
    cancelled = False

    try:
        for i, (file_name, file_path) in enumerate(files):
            if check_cancel(ingest_task_id):
                cancelled = True
                break

            update_task_status(ingest_task_id, current_file=file_name)

            with open(file_path, encoding="utf-8") as f:
                text = f.read()

            chunks = chunk_document(text, file_name)
            texts = [c.content for c in chunks]
            embeddings = embed_texts(texts)
            result = store_chunks(chunks, embeddings)

            total_chunks += len(chunks)
            total_stored += result["stored"]
            total_skipped += result["skipped"]
            file_results.append(
                {
                    "file": file_name,
                    "chunks": len(chunks),
                    "stored": result["stored"],
                    "skipped": result["skipped"],
                }
            )

            elapsed = time.time() - start_time
            done = i + 1
            avg = elapsed / done
            update_task_status(
                ingest_task_id,
                current=done,
                elapsed=round(elapsed, 1),
                estimated_remaining=round(avg * (len(files) - done), 1),
            )
    finally:
        clear_task_status(ingest_task_id)

    return _json_response(
        {
            "cancelled": cancelled,
            "cleared": deleted,
            "files": len(files),
            "total_chunks": total_chunks,
            "stored": total_stored,
            "skipped": total_skipped,
            "details": file_results,
        }
    )


# --- Evaluate ---


def _handle_evaluate(req: https_fn.Request) -> https_fn.Response:
    """POST /evaluate — 評価実行"""
    from src.evaluate.reporter import generate_report, save_report
    from src.evaluate.runner import run_evaluation
    from src.evaluate.scorer import EvalCase
    from src.task_status import (
        check_cancel,
        clear_task_status,
        update_task_status,
    )

    eval_dataset = "test-data/golden/eval_dataset.jsonl"

    with open(eval_dataset, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    cases = []
    for line in lines:
        data = json.loads(line)
        cases.append(
            EvalCase(
                id=data["id"],
                query=data["query"],
                expected_answer=data["expected_answer"],
                expected_keywords=data["expected_keywords"],
                type=data["type"],
                category=data["category"],
                requires=data.get("requires", ""),
            )
        )

    # 進捗初期化
    eval_task_id = f"evaluate:{config.collection_name}"
    start_time = time.time()
    active_count = 0
    eval_results_list: list[dict] = []
    update_task_status(
        eval_task_id,
        running=True,
        cancel=False,
        current=0,
        total=len(cases),
        current_id="",
        elapsed=0.0,
        estimated_remaining=0.0,
        results=[],
        collection=config.collection_name,
    )

    def _should_cancel() -> bool:
        return check_cancel(eval_task_id)

    def _on_progress(current: int, total: int, result) -> None:
        nonlocal active_count
        elapsed = time.time() - start_time
        if not result.skipped:
            active_count += 1

        est_remaining = 0.0
        if active_count >= 2:
            avg_per_active = elapsed / active_count
            est_remaining = avg_per_active * (total - current)

        status = "SKIP" if result.skipped else ("PASS" if result.passed else "FAIL")
        eval_results_list.append(
            {
                "id": result.id,
                "status": status,
                "llm_label": result.llm_label or "",
            }
        )
        update_task_status(
            eval_task_id,
            current=current,
            total=total,
            current_id=result.id,
            elapsed=round(elapsed, 1),
            estimated_remaining=round(est_remaining, 1),
            results=eval_results_list,
        )

    try:
        results = run_evaluation(cases, on_progress=_on_progress, should_cancel=_should_cancel)
    finally:
        clear_task_status(eval_task_id)

    report = generate_report(results)
    file_path = save_report(report)

    return _json_response(
        {
            "report": asdict(report),
            "saved_to": file_path,
        }
    )


def _handle_evaluate_status(req: https_fn.Request) -> https_fn.Response:
    """GET /evaluate/status — 評価進捗を返す"""
    from src.task_status import get_task_status

    eval_task_id = f"evaluate:{config.collection_name}"
    return _json_response(get_task_status(eval_task_id))


def _handle_evaluate_cancel(req: https_fn.Request) -> https_fn.Response:
    """POST /evaluate/cancel — 評価を中止する"""
    from src.task_status import get_task_status, update_task_status

    eval_task_id = f"evaluate:{config.collection_name}"
    status = get_task_status(eval_task_id)
    if not status.get("running"):
        return _json_response({"cancelled": False, "reason": "not running"})
    update_task_status(eval_task_id, cancel=True)
    return _json_response({"cancelled": True})


def _handle_evaluate_cases(req: https_fn.Request) -> https_fn.Response:
    """GET /evaluate/cases — テストケース一覧"""
    eval_dataset = "test-data/golden/eval_dataset.jsonl"

    with open(eval_dataset, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    cases = []
    for line in lines:
        data = json.loads(line)
        cases.append(
            {
                "id": data["id"],
                "type": data["type"],
                "category": data["category"],
                "query": data["query"],
                "expected_answer": data["expected_answer"],
                "expected_keywords": data["expected_keywords"],
                "requires": data.get("requires", ""),
            }
        )

    return _json_response({"cases": cases, "count": len(cases)})


def _handle_evaluate_results(req: https_fn.Request) -> https_fn.Response:
    """GET /evaluate/results — 評価結果一覧取得（Firestore優先、フォールバックでローカルファイル）"""
    # Firestoreから取得を試みる
    try:
        db = _get_firestore_client()
        docs = list(
            db.collection("eval_results").order_by("date", direction=firestore.Query.DESCENDING).limit(50).get()
        )
        if docs:
            results = []
            for doc in docs:
                data = doc.to_dict() or {}
                results.append(
                    {
                        "file": doc.id,
                        "date": data.get("date", ""),
                        "config_params": data.get("config_params", {}),
                        "overall": data.get("overall", {}),
                        "score_by_type": data.get("score_by_type", {}),
                    }
                )
            return _json_response(results)
    except Exception as e:
        print(f"  [EvalResults] Firestore read failed: {e}")

    # フォールバック: ローカルファイルから読み込み
    from src.config import config

    results_dir = config.results_dir
    if not os.path.isdir(results_dir):
        return _json_response([])

    files = sorted(
        (f for f in os.listdir(results_dir) if f.startswith("eval_") and f.endswith(".json")),
        reverse=True,
    )

    results = []
    for fname in files:
        fpath = os.path.join(results_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        results.append(
            {
                "file": fname,
                "date": data.get("date", ""),
                "config_params": data.get("config_params", {}),
                "overall": data.get("overall", {}),
                "score_by_type": data.get("score_by_type", {}),
            }
        )

    return _json_response(results)


# --- Config ---

_TUNABLE_PARAMS: dict[str, type] = {
    "chunk_size": int,
    "chunk_overlap": int,
    "header_injection": bool,
    "top_k": int,
    "rerank_top_n": int,
    "rerank_threshold": float,
    # 検索技術トグル
    "hybrid_search": bool,
    "metadata_scoring": bool,
    "clarification": bool,
    "permission_filter": bool,
    "shadow_retrieval": bool,
    "multi_query": bool,
    "answerability_threshold": float,
    "contextual_retrieval": bool,
}


def _handle_config_get(req: https_fn.Request) -> https_fn.Response:
    """GET /config — 現在のパラメータ取得"""
    from src.config import config

    return _json_response({k: getattr(config, k) for k in _TUNABLE_PARAMS})


def _handle_config_put(req: https_fn.Request) -> https_fn.Response:
    """PUT /config — パラメータ更新（ランタイムのみ、再デプロイで戻る）"""
    from src.config import config

    body = req.get_json(force=True, silent=True)
    if not body:
        return _error("JSON body required")

    updated = {}
    errors = []
    for key, value in body.items():
        if key not in _TUNABLE_PARAMS:
            errors.append(f"Unknown parameter: {key}")
            continue
        try:
            expected_type = _TUNABLE_PARAMS[key]
            if expected_type is bool:
                typed_value = value if isinstance(value, bool) else str(value).lower() not in ("false", "0", "no")
            else:
                typed_value = expected_type(value)
            setattr(config, key, typed_value)
            updated[key] = typed_value
        except (ValueError, TypeError) as e:
            errors.append(f"Invalid value for {key}: {e}")

    result: dict = {"updated": updated}
    if errors:
        result["errors"] = errors

    return _json_response(result)


# --- Chunks ---


def _handle_chunks(req: https_fn.Request) -> https_fn.Response:
    """GET /chunks — チャンク一覧取得（embedding除外）"""
    from src.config import config

    db = _get_firestore_client()
    collection = db.collection(config.collection_name)

    # フィルタ構築
    query = collection
    category = req.args.get("category")
    if category:
        query = query.where("category", "==", category)
    security_level = req.args.get("security_level")
    if security_level:
        query = query.where("security_level", "==", security_level)

    query = query.order_by("source_file").order_by("chunk_index")

    limit = min(int(req.args.get("limit", "200")), 500)
    offset = int(req.args.get("offset", "0"))

    docs = list(query.limit(limit + offset).get())
    docs = docs[offset:]

    chunks = []
    for doc in docs[:limit]:
        data = doc.to_dict() or {}
        data.pop("embedding", None)
        data["id"] = doc.id
        content = data.get("content", "")
        data["content_preview"] = content[:50] + ("..." if len(content) > 50 else "")
        chunks.append(data)

    return _json_response(
        {
            "chunks": chunks,
            "count": len(chunks),
        }
    )


# --- Logs ---


def _handle_logs(req: https_fn.Request) -> https_fn.Response:
    """GET /logs — クエリログ一覧取得"""
    db = _get_firestore_client()
    query = db.collection("query_logs").order_by("timestamp", direction=firestore.Query.DESCENDING)

    # フィルタ
    no_answer = req.args.get("no_answer")
    if no_answer == "true":
        query = query.where("no_answer", "==", True)

    limit = min(int(req.args.get("limit", "50")), 200)
    docs = list(query.limit(limit).get())

    logs = []
    for doc in docs:
        data = doc.to_dict() or {}
        ts = data.get("timestamp")
        logs.append(
            {
                "id": doc.id,
                "query": data.get("query", ""),
                "answer": data.get("answer", ""),
                "model": data.get("model", ""),
                "elapsed_ms": data.get("elapsed_ms", 0),
                "sources": data.get("sources", []),
                "source_count": data.get("source_count", 0),
                "no_answer": data.get("no_answer", False),
                "timestamp": ts.isoformat() if ts else None,
            }
        )

    return _json_response(
        {
            "logs": logs,
            "count": len(logs),
        }
    )


# --- Collections ---


def _handle_collections(req: https_fn.Request) -> https_fn.Response:
    """GET /collections — chunks_* コレクション一覧を返す"""
    db = _get_firestore_client()
    collections = []
    for coll_ref in db.collections():
        name = coll_ref.id
        if not name.startswith("chunks"):
            continue
        # ドキュメント数を取得（count_documents は Firestore の集約クエリ）
        try:
            count = sum(1 for _ in coll_ref.select([]).limit(10000).stream())
        except Exception:
            count = 0
        collections.append(
            {
                "name": name,
                "count": count,
                "active": name == config.collection_name,
            }
        )
    collections.sort(key=lambda c: c["name"])
    return _json_response({"collections": collections, "current": config.collection_name})


def _handle_collections_switch(req: https_fn.Request) -> https_fn.Response:
    """PUT /collections/switch — 検索対象コレクションを切り替える"""
    body = req.get_json(force=True, silent=True) or {}
    name = body.get("name", "")
    if not name:
        return _error("name is required", 400)
    config.collection_name = name
    return _json_response({"switched_to": name})


# --- Tasks ---


def _handle_tasks(req: https_fn.Request) -> https_fn.Response:
    """GET /tasks — 実行中のタスク一覧を返す（ingest_*, evaluate_*）"""
    from src.task_status import list_tasks

    prefix = req.args.get("prefix", "")
    tasks = list_tasks(prefix)
    return _json_response({"tasks": tasks})
