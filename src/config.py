import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # GCP
    project_id: str = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    location: str = os.environ.get("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    # Firestore
    collection_name: str = "chunks"

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 150

    # Embedding
    embedding_model: str = "text-embedding-005"
    embedding_dimension: int = 768

    # Search
    top_k: int = 10
    rerank_top_n: int = 5
    rerank_threshold: float = 0.01

    # LLM
    llm_model: str = "gemini-2.5-flash"

    # Evaluation
    results_dir: str = "results"


config = Config()
