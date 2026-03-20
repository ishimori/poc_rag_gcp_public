from __future__ import annotations

import vertexai
from vertexai.language_models import TextEmbeddingModel

from src.config import config

_model: TextEmbeddingModel | None = None


def _get_model() -> TextEmbeddingModel:
    global _model
    if _model is None:
        vertexai.init(project=config.project_id or None, location=config.location)
        _model = TextEmbeddingModel.from_pretrained(config.embedding_model)
    return _model


def embed_text(text: str) -> list[float]:
    """テキストをベクトルに変換する"""
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """複数テキストを一括でベクトルに変換する（バッチ処理）"""
    model = _get_model()
    all_embeddings: list[list[float]] = []

    # Vertex AI は1リクエスト最大250件
    batch_size = 250
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = model.get_embeddings(batch)
        for emb in embeddings:
            all_embeddings.append(emb.values)

    return all_embeddings
