import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "vyapaar_ai.db").replace("\\", "/")

class Settings(BaseSettings):
    PROJECT_NAME: str = "Vyapaar AI"
    PROJECT_VERSION: str = "2.4.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "vyapaar-ai-in-super-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database: Absolute path SQLite or PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{DEFAULT_DB_FILE}"
    )
    
    # Document storage directory
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "storage", "scheme_documents"))
    
    # AI Configuration (Optional Gemini key, with intelligent local fallback)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)

    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()
