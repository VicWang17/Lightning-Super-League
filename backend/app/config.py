"""
Application configuration using Pydantic Settings
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


# 确保 .env 路径相对于本文件位置，不受运行目录影响
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # App
    APP_NAME: str = "Lightning Super League API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "mysql+asyncmy://user:pass@localhost:3306/lightning"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
