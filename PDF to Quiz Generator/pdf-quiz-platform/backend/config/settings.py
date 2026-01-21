# /backend/config/settings.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # OpenAI / LLM
    OPENAI_API_KEY: str = "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"
    OPENAI_MODEL: str = "llama-3.1-8b-instant"
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    CHUNKS_DIR: str = "./data/chunks"
    QUIZZES_DIR: str = "./data/quizzes"
    VECTOR_INDEX_DIR: str = "./data/vector_index"
    
    # Chunking Parameters
    CHUNK_OVERLAP_RATIO: float = 0.3
    MIN_CHUNK_SIZE: int = 200
    MAX_CHUNK_SIZE: int = 1000
    
    # Question Generation
    MAX_QUESTIONS_PER_CHUNK: int = 3
    QUESTION_TYPES: List[str] = ["mcq", "short_answer"]
    
    # Deduplication
    SIMILARITY_THRESHOLD: float = 0.85
    
    # Topic Normalization
    TARGET_TOPIC_COUNT: int = 10
    TOPIC_CLUSTERING_THRESHOLD: float = 0.7
    
    class Config:
        env_file = "../../.env"  # Adjusted to match your actual file location
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
