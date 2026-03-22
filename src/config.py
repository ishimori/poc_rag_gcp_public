import os

from dotenv import load_dotenv

load_dotenv(".env.local")


class Config:
    # GCP
    project_id: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location: str = os.environ.get("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    # Firestore
    collection_name: str = os.environ.get("COLLECTION_NAME", "chunks")

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 150
    header_injection: bool = True

    # Contextual Retrieval
    contextual_retrieval: bool = True  # ONの場合header_injectionより優先

    # Embedding
    embedding_model: str = "text-embedding-005"
    embedding_dimension: int = 768

    # Search
    top_k: int = 10
    rerank_top_n: int = 5
    rerank_threshold: float = 0.01

    # Metadata Scoring
    metadata_scoring: bool = True
    metadata_category_bonus: float = 0.03
    metadata_filename_bonus: float = 0.02

    # Hybrid Search
    hybrid_search: bool = True
    rrf_k: int = 60

    # Multi-Query Expansion
    multi_query: bool = False  # ONでクエリを複数展開して検索
    multi_query_count: int = 3  # 展開するクエリ数（original + N）

    # LLM
    llm_model: str = "gemini-3-flash-preview"
    llm_location: str = os.environ.get("LLM_LOCATION", "global")  # Gemini 3系はglobalのみ

    # Clarification
    clarification: bool = True

    # Permission
    permission_filter: bool = True
    shadow_retrieval: bool = True  # 権限除外検出（フィルタなし検索で差分判定）
    user_groups: list[str] = ["all"]

    # Vertex AI Search
    use_vertex_ai_search: bool = False
    vertex_search_engine_id: str = os.environ.get("VERTEX_SEARCH_ENGINE_ID", "")
    vertex_search_data_store_id: str = os.environ.get("VERTEX_SEARCH_DATA_STORE_ID", "")

    # Answerability Gate
    answerability_threshold: float = 0.0  # 0=無効。リランキング後のtop1スコアがこれ未満なら拒否

    # Evaluation
    results_dir: str = "results"


config = Config()
