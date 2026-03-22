"""タスク状態管理 — Firestore経由でプロセス間の実行状態を共有する"""

from __future__ import annotations

from google.cloud import firestore

from src.config import config

_COLLECTION = "task_status"

_db: firestore.Client | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=config.project_id or None)
    return _db


def update_task_status(task_id: str, **fields) -> None:
    """タスク状態を更新する（merge=Trueで部分更新）"""
    doc_ref = _get_db().collection(_COLLECTION).document(task_id)
    fields["updated_at"] = firestore.SERVER_TIMESTAMP
    doc_ref.set(fields, merge=True)


def get_task_status(task_id: str) -> dict:
    """タスク状態を取得する。ドキュメント未存在なら running=False を返す"""
    doc = _get_db().collection(_COLLECTION).document(task_id).get()
    if not doc.exists:
        return {"running": False}
    data = doc.to_dict() or {}
    # SERVER_TIMESTAMP は読み取り時に datetime になるため、文字列に変換
    if "updated_at" in data and data["updated_at"] is not None:
        data["updated_at"] = data["updated_at"].isoformat()
    return data


def clear_task_status(task_id: str) -> None:
    """タスク完了時に状態をクリアする"""
    doc_ref = _get_db().collection(_COLLECTION).document(task_id)
    doc_ref.set(
        {
            "running": False,
            "cancel": False,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
    )


def list_tasks(prefix: str = "") -> list[dict]:
    """タスク一覧を取得する。prefixでフィルタ（例: "ingest_", "evaluate_"）"""
    db = _get_db()
    docs = db.collection(_COLLECTION).stream()
    results = []
    for doc in docs:
        if prefix and not doc.id.startswith(prefix):
            continue
        data = doc.to_dict() or {}
        data["task_id"] = doc.id
        if "updated_at" in data and data["updated_at"] is not None:
            data["updated_at"] = data["updated_at"].isoformat()
        results.append(data)
    return results


def check_cancel(task_id: str) -> bool:
    """中止リクエストが出ているか確認する"""
    doc = _get_db().collection(_COLLECTION).document(task_id).get()
    if not doc.exists:
        return False
    return bool((doc.to_dict() or {}).get("cancel", False))
