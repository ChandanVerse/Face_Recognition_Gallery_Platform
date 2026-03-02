"""
Application settings and configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database - MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "aiGallery")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Pinecone
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "face-embeddings-webapp")

    # Local Storage
    STORAGE_BASE_PATH: str = os.getenv("STORAGE_BASE_PATH", "storage")
    STORAGE_BASE_URL: str = os.getenv("STORAGE_BASE_URL", "http://localhost:8000/storage")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your_super_secret_jwt_key_here_change_in_production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))

    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # Face Recognition
    FACE_DETECTION_THRESHOLD: float = float(os.getenv("FACE_DETECTION_THRESHOLD", "0.7"))
    MAX_FACES_PER_IMAGE: int = int(os.getenv("MAX_FACES_PER_IMAGE", "50"))

    # Face Matching
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.7"))  # Minimum similarity for face matches (transformed scores in [0, 1] range)
                                        # Raw Pinecone cosine scores [-1, 1] are transformed: (score + 1.0) / 2.0
                                        # Example: 0.7 threshold = 0.4 raw cosine similarity
    FACE_MATCH_TOP_K: int = int(os.getenv("FACE_MATCH_TOP_K", "10000"))  # Maximum number of candidates to consider
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()