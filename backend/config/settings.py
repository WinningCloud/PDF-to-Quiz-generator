# backend/config/settings.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # ================= DATABASE =================
    DATABASE_URL: str

    # ================= REDIS =================
    REDIS_URL: str = "redis://localhost:6379"

    # ================= LLM / AI =================
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "llama-3.1-8b-instant"
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # ================= AUTH =================
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ================= APP =================
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ================= FILE STORAGE =================
    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    CHUNKS_DIR: str = "./data/chunks"
    QUIZZES_DIR: str = "./data/quizzes"
    VECTOR_INDEX_DIR: str = "./data/vector_index"

    # ================= CHUNKING =================
    CHUNK_OVERLAP_RATIO: float = 0.3
    MIN_CHUNK_SIZE: int = 200
    MAX_CHUNK_SIZE: int = 1000

    # ================= QUESTION GEN =================
    MAX_QUESTIONS_PER_CHUNK: int = 2
    QUESTION_TYPES: List[str] = ["mcq", "short_answer"]

    # ================= DEDUP =================
    SIMILARITY_THRESHOLD: float = 0.85

    # ================= TOPICS =================
    TARGET_TOPIC_COUNT: int = 10
    TOPIC_CLUSTERING_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"   # ✅ correct path (same folder level where app runs)
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
