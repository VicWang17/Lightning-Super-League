"""
Lightning Super League - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.dependencies import engine, redis_client
from app.core.logging import setup_logging, get_logger
from app.core.middleware import LoggingMiddleware, ProcessTimeHeader
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.teams import router as teams_router
from app.routers.players import router as players_router
from app.routers.leagues import router as leagues_router
from app.routers.matches import router as matches_router
from app.routers.seasons import router as seasons_router
from app.routers.cups import router as cups_router

settings = get_settings()

# 配置日志
setup_logging(debug=settings.DEBUG)
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📚 API Documentation: http://localhost:8000/docs")
    yield
    # Shutdown
    logger.info("👋 Shutting down...")
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
        {"name": "赛季", "description": "赛季管理、赛程生成、比赛调度"},
        {"name": "杯赛", "description": "杯赛信息、小组赛、淘汰赛"},
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

# 请求日志中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(ProcessTimeHeader)


# Include routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(players_router, prefix="/api/v1")
app.include_router(leagues_router, prefix="/api/v1")
app.include_router(matches_router, prefix="/api/v1")
app.include_router(seasons_router, prefix="/api/v1")
app.include_router(cups_router, prefix="/api/v1")


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
