"""
Lightning Super League - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.dependencies import engine, redis_client
from app.routers import (
    health,
    auth,
    users,
    teams,
    players,
    leagues,
    matches,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    yield
    # Shutdown
    print("👋 Shutting down...")
    await engine.dispose()
    await redis_client.close()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="闪电超级联赛 - 在线足球经理游戏 API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "健康检查", "description": "系统健康状态检查"},
        {"name": "认证", "description": "用户注册、登录、令牌管理"},
        {"name": "用户", "description": "用户信息管理"},
        {"name": "球队", "description": "球队管理"},
        {"name": "球员", "description": "球员管理"},
        {"name": "联赛", "description": "联赛信息、积分榜、赛程"},
        {"name": "比赛", "description": "比赛数据、直播、统计"},
    ],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(leagues.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else None,
        "api_prefix": "/api/v1",
    }


@app.get("/api/v1")
async def api_info():
    """API information endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "teams": "/api/v1/teams",
            "players": "/api/v1/players",
            "leagues": "/api/v1/leagues",
            "matches": "/api/v1/matches",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
