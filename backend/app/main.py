from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import auth, teams, players, matches
from app.core.config import settings

app = FastAPI(
    title="闪电超级联赛 API",
    description="高度拟真的在线足球经理游戏后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(teams.router, prefix="/api/teams", tags=["球队"])
app.include_router(players.router, prefix="/api/players", tags=["球员"])
app.include_router(matches.router, prefix="/api/matches", tags=["比赛"])

@app.get("/")
async def root():
    return JSONResponse(content={
        "message": "欢迎来到闪电超级联赛 API",
        "version": "1.0.0",
        "docs": "/docs"
    })

@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 