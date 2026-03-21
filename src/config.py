import os

from dotenv import load_dotenv

load_dotenv(".env.local")


class Config:
    # GCP
    project_id: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location: str = os.environ.get("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    # Firestore
    collection_name: str = "chunks"

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

    # LLM
    llm_model: str = "gemini-2.5-flash"

    # Clarification
    clarification: bool = True

    # Permission
    permission_filter: bool = True
    user_groups: list[str] = ["all"]

    # Evaluation
    results_dir: str = "results"


config = Config()
