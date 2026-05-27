"""
Application configuration using Pydantic Settings
"""
import os
from pydantic import field_validator
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
    
    # Ports (used for CORS and docs links)
    BACKEND_PORT: str = "8000"
    FRONTEND_PORT: str = "5173"
    
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
    
    # TODO: Go 实时比赛引擎服务配置（详见 services/match_engine_client.py）
    # Python FastAPI 保留管理功能，比赛推演由独立 Go/Gin 微服务处理
    MATCH_ENGINE_URL: str = "http://localhost:8080"  # Go 引擎地址
    MATCH_ENGINE_API_KEY: str = ""  # 服务间通信密钥（预留）
    MATCH_ENGINE_TRANSPORT: str = "http"  # http / process
    MATCH_ENGINE_MODE: str = "instant"  # realtime / accelerated / instant
    MATCH_ENGINE_TICK_INTERVAL_MS: int = 0
    MATCH_ENGINE_FALLBACK_RANDOM: bool = False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v, info):
        """支持从环境变量以逗号分隔字符串解析 CORS_ORIGINS，并自动加入前端地址"""
        origins = []
        if isinstance(v, str):
            origins = [x.strip() for x in v.split(",") if x.strip()]
        elif isinstance(v, list):
            origins = list(v)
        # 自动包含当前 FRONTEND_PORT 对应的前端地址
        frontend_port = info.data.get("FRONTEND_PORT", "5173")
        frontend_origin = f"http://localhost:{frontend_port}"
        if frontend_origin not in origins:
            origins.insert(0, frontend_origin)
        return origins


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
